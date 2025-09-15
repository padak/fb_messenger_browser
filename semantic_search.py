#!/usr/bin/env python3
"""
Semantic search functionality using Ollama for Czech language support.
"""

import json
import os
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import hashlib
from datetime import datetime

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("⚠️ Ollama not installed. Run: pip install ollama")

try:
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    print("⚠️ scikit-learn not installed. Run: pip install scikit-learn")

try:
    from tqdm import tqdm
except ImportError:
    # Simple fallback if tqdm not available
    def tqdm(iterable, desc=None, total=None):
        return iterable


class SemanticSearchEngine:
    """Handles semantic search using Ollama embeddings."""

    def __init__(self, model_name: str = "nomic-embed-text", cache_dir: str = "server_data/embeddings"):
        """
        Initialize the semantic search engine.

        Args:
            model_name: Ollama model to use for embeddings
            cache_dir: Directory to cache embeddings
        """
        self.model_name = model_name
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Progress tracking
        self.generation_progress = {}  # conversation_id -> {status, progress, message}

        # Check if Ollama is available
        if not OLLAMA_AVAILABLE:
            raise ImportError("Ollama is required for semantic search. Install with: pip install ollama")

        # Check if model is available
        self._check_ollama_model()

    def _check_ollama_model(self):
        """Check if the required Ollama model is installed."""
        try:
            # Try to get model info
            ollama.show(self.model_name)
            print(f"✅ Ollama model '{self.model_name}' is ready")
        except Exception as e:
            print(f"⚠️ Ollama model '{self.model_name}' not found.")
            print(f"Please install it with: ollama pull {self.model_name}")
            print("\nRecommended models for Czech:")
            print("  - nomic-embed-text (good multilingual support)")
            print("  - mxbai-embed-large (larger, better quality)")
            raise RuntimeError(f"Ollama model '{self.model_name}' not available") from e

    def _get_cache_path(self, conversation_id: str) -> Path:
        """Get the cache file path for a conversation."""
        return self.cache_dir / f"conv_{conversation_id}_embeddings.npz"

    def _get_text_hash(self, text: str) -> str:
        """Get a hash of the text for cache invalidation."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()[:8]

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text using Ollama.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(768)  # Typical embedding size

        try:
            response = ollama.embeddings(
                model=self.model_name,
                prompt=text
            )
            return np.array(response['embedding'])
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector on error
            return np.zeros(768)

    def embed_messages(self, messages: List[Dict], conversation_id: str, force_rebuild: bool = False) -> Dict:
        """
        Generate embeddings for all messages in a conversation.

        Args:
            messages: List of message dictionaries
            conversation_id: Unique ID for the conversation
            force_rebuild: Force regeneration even if cache exists

        Returns:
            Dictionary with message IDs as keys and embeddings as values
        """
        cache_path = self._get_cache_path(conversation_id)

        # Try to load from cache
        if not force_rebuild and cache_path.exists():
            try:
                print(f"📂 Loading cached embeddings for conversation {conversation_id}")
                data = np.load(cache_path, allow_pickle=True)

                # Check if cache is still valid (same number of messages)
                if 'message_count' in data and data['message_count'] == len(messages):
                    embeddings = {}
                    for key in data.files:
                        if key.startswith('msg_'):
                            embeddings[key] = data[key]
                    print(f"✅ Loaded {len(embeddings)} cached embeddings")

                    # Mark as ready since we loaded from cache
                    self.generation_progress[conversation_id] = {
                        'status': 'ready',
                        'progress': 100,
                        'message': f'Loaded {len(embeddings)} cached embeddings'
                    }

                    return embeddings
            except Exception as e:
                print(f"⚠️ Failed to load cache: {e}")

        # Generate new embeddings
        print(f"🔄 Generating embeddings for {len(messages)} messages...")

        # Set initial progress
        self.generation_progress[conversation_id] = {
            'status': 'generating',
            'progress': 0,
            'message': f'Starting to process {len(messages)} messages...'
        }

        embeddings = {}
        messages_with_content = [msg for msg in messages if msg.get('content', '').strip()]
        total_messages = len(messages_with_content)

        for i, msg in enumerate(messages_with_content):
            # Create unique message ID
            msg_id = f"msg_{msg.get('timestamp_ms', i)}"

            # Get message content
            content = msg.get('content', '')

            # Generate embedding
            embedding = self.embed_text(content)
            embeddings[msg_id] = embedding

            # Update progress
            progress = ((i + 1) / total_messages) * 100
            self.generation_progress[conversation_id] = {
                'status': 'generating',
                'progress': progress,
                'message': f'Processing message {i + 1} of {total_messages}...'
            }

            # Show progress for large conversations
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{total_messages} messages...")

        # Save to cache
        try:
            print(f"💾 Saving embeddings to cache...")
            save_data = {
                'message_count': len(messages),
                'generated_at': datetime.now().isoformat(),
                'model': self.model_name
            }
            # Add all embeddings
            for msg_id, embedding in embeddings.items():
                save_data[msg_id] = embedding

            np.savez_compressed(cache_path, **save_data)
            print(f"✅ Cached {len(embeddings)} embeddings")
        except Exception as e:
            print(f"⚠️ Failed to save cache: {e}")

        # Mark as ready
        self.generation_progress[conversation_id] = {
            'status': 'ready',
            'progress': 100,
            'message': f'Successfully generated embeddings for {len(embeddings)} messages'
        }

        return embeddings

    def search(self, query: str, messages: List[Dict], embeddings: Dict,
               top_k: int = 10, threshold: float = 0.3) -> List[Tuple[Dict, float]]:
        """
        Perform semantic search on messages.

        Args:
            query: Search query in natural language
            messages: List of message dictionaries
            embeddings: Pre-computed embeddings dictionary
            top_k: Number of top results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of (message, similarity_score) tuples
        """
        if not query or not query.strip():
            return []

        # Generate query embedding
        print(f"🔍 Searching for: '{query}'")
        query_embedding = self.embed_text(query)

        # Calculate similarities
        results = []

        for msg in messages:
            msg_id = f"msg_{msg.get('timestamp_ms', 0)}"

            if msg_id not in embeddings:
                continue

            # Calculate cosine similarity
            msg_embedding = embeddings[msg_id]
            similarity = cosine_similarity(
                query_embedding.reshape(1, -1),
                msg_embedding.reshape(1, -1)
            )[0][0]

            # Only include results above threshold
            if similarity >= threshold:
                results.append((msg, float(similarity)))

        # Sort by similarity (highest first)
        results.sort(key=lambda x: x[1], reverse=True)

        # Return top k results
        return results[:top_k]

    def search_across_conversations(self, query: str, conversations: List[Dict],
                                   top_k: int = 20) -> List[Dict]:
        """
        Search across multiple conversations.

        Args:
            query: Search query
            conversations: List of conversation data with embeddings
            top_k: Total number of results to return

        Returns:
            List of results with conversation context
        """
        all_results = []

        for conv in conversations:
            conv_results = self.search(
                query,
                conv['messages'],
                conv['embeddings'],
                top_k=5  # Get top 5 from each conversation
            )

            # Add conversation context
            for msg, score in conv_results:
                result = {
                    'message': msg,
                    'score': score,
                    'conversation': conv['participants'],
                    'conversation_id': conv['id']
                }
                all_results.append(result)

        # Sort all results by score
        all_results.sort(key=lambda x: x['score'], reverse=True)

        return all_results[:top_k]


# Utility functions for integration with messenger_server.py

def check_ollama_installation() -> bool:
    """Check if Ollama is installed and running."""
    if not OLLAMA_AVAILABLE:
        return False

    try:
        # Try to list models
        models = ollama.list()
        return True
    except Exception:
        print("⚠️ Ollama is not running. Please start it with: ollama serve")
        return False


def get_recommended_models() -> List[str]:
    """Get list of recommended models for Czech language."""
    return [
        "nomic-embed-text",      # Good multilingual, 768 dims
        "mxbai-embed-large",      # Better quality, 1024 dims
        "all-minilm",             # Smaller, faster, 384 dims
    ]


def install_model(model_name: str) -> bool:
    """
    Install an Ollama model if not present.

    Args:
        model_name: Name of the model to install

    Returns:
        True if successful
    """
    try:
        print(f"📥 Pulling Ollama model '{model_name}'...")
        ollama.pull(model_name)
        print(f"✅ Model '{model_name}' installed successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to install model: {e}")
        return False