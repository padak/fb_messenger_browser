#!/usr/bin/env python3
"""
Test script for semantic search functionality.
"""

import json
import numpy as np
from semantic_search import SemanticSearchEngine, check_ollama_installation
from datetime import datetime


def test_ollama_connection():
    """Test if Ollama is installed and running."""
    print("=" * 60)
    print("🔍 Testing Ollama Connection")
    print("=" * 60)

    if not check_ollama_installation():
        print("❌ Ollama is not available!")
        print("\nPlease follow these steps:")
        print("1. Install Ollama: brew install ollama")
        print("2. Start Ollama: ollama serve")
        print("3. Pull model: ollama pull nomic-embed-text")
        return False

    print("✅ Ollama is running!")
    return True


def test_embeddings():
    """Test embedding generation with Czech and English text."""
    print("\n" + "=" * 60)
    print("🧪 Testing Embeddings")
    print("=" * 60)

    try:
        engine = SemanticSearchEngine()

        # Test texts
        test_texts = [
            ("English", "I'm planning a vacation to Prague"),
            ("Czech", "Plánuji dovolenou v Praze"),
            ("Mixed", "Tomorrow středa meeting at 3pm"),
        ]

        embeddings = []
        for lang, text in test_texts:
            print(f"\n{lang}: '{text}'")
            embedding = engine.embed_text(text)
            print(f"  Embedding shape: {embedding.shape}")
            print(f"  Non-zero values: {np.count_nonzero(embedding)}")
            embeddings.append(embedding)

        # Test similarity between English and Czech (should be high)
        from sklearn.metrics.pairwise import cosine_similarity
        similarity = cosine_similarity(
            embeddings[0].reshape(1, -1),
            embeddings[1].reshape(1, -1)
        )[0][0]

        print(f"\n📊 Similarity between English and Czech versions: {similarity:.2%}")
        if similarity > 0.7:
            print("✅ Good! The model understands both languages mean the same thing.")
        else:
            print("⚠️ Low similarity - model might not be multilingual.")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_semantic_search():
    """Test semantic search with sample messages."""
    print("\n" + "=" * 60)
    print("🔎 Testing Semantic Search")
    print("=" * 60)

    try:
        engine = SemanticSearchEngine()

        # Create sample messages
        messages = [
            {"timestamp_ms": 1000, "content": "Ahoj, jak se máš?", "sender": "Petr"},
            {"timestamp_ms": 2000, "content": "Dobře, díky za optání!", "sender": "Lucie"},
            {"timestamp_ms": 3000, "content": "Půjdeme zítra na kávu?", "sender": "Petr"},
            {"timestamp_ms": 4000, "content": "I'm learning Czech language", "sender": "Petr"},
            {"timestamp_ms": 5000, "content": "Učím se český jazyk", "sender": "Lucie"},
            {"timestamp_ms": 6000, "content": "Let's meet for coffee tomorrow", "sender": "Petr"},
            {"timestamp_ms": 7000, "content": "Jsem unavený, potřebuji spát", "sender": "Lucie"},
            {"timestamp_ms": 8000, "content": "I'm tired, need to sleep", "sender": "Petr"},
        ]

        print(f"📝 Processing {len(messages)} sample messages...")

        # Generate embeddings
        embeddings = {}
        for msg in messages:
            msg_id = f"msg_{msg['timestamp_ms']}"
            embeddings[msg_id] = engine.embed_text(msg['content'])

        # Test queries
        queries = [
            "greeting hello",
            "pozdrav ahoj",
            "coffee meeting",
            "káva setkání",
            "tired sleep",
            "unavený spát",
        ]

        print("\n🔍 Testing semantic search queries:")
        for query in queries:
            print(f"\nQuery: '{query}'")
            results = engine.search(query, messages, embeddings, top_k=3)

            if results:
                print("  Top matches:")
                for msg, score in results:
                    print(f"    [{score:.2%}] {msg['sender']}: {msg['content']}")
            else:
                print("  No matches found")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Facebook Messenger Semantic Search Test Suite")
    print("=" * 60)

    # Run tests
    tests_passed = 0
    tests_total = 3

    if test_ollama_connection():
        tests_passed += 1

        if test_embeddings():
            tests_passed += 1

        if test_semantic_search():
            tests_passed += 1
    else:
        print("\n⚠️ Skipping remaining tests - Ollama not available")

    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tests_passed}/{tests_total} passed")
    print("=" * 60)

    if tests_passed == tests_total:
        print("✅ All tests passed! Semantic search is ready to use.")
        print("\nNext steps:")
        print("1. Restart messenger_server.py")
        print("2. Visit http://localhost:8000")
        print("3. Semantic search will be available in conversations")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        print("\nSee OLLAMA_SETUP.md for installation instructions.")


if __name__ == "__main__":
    main()