# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a Facebook Messenger Export Viewer - a web-based tool for browsing and searching Facebook Messenger conversation exports with full Czech character encoding fixes.

## Commands

### Setting Up the Environment
```bash
# IMPORTANT: Always use virtual environment for dependencies
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# For semantic search and AI analysis (optional)
brew install ollama  # macOS
ollama serve  # Run in separate terminal
ollama pull nomic-embed-text  # For semantic search
ollama pull llama3.2:3b  # For conversation summarization (2GB)
```

### Running the Application
```bash
# Activate virtual environment first!
source .venv/bin/activate

# Start the main server
python messenger_server.py
# Opens at http://localhost:8000

# Test semantic search
python test_semantic_search.py
```

### Common Operations
```bash
# Rebuild conversation index (if adding new data)
curl http://localhost:8000/rebuild

# Kill server if port 8000 is in use
lsof -ti:8000 | xargs kill -9
```

## Configuration

Environment variables can be set in `.env` file:
- `SEMANTIC_SEARCH_ENABLED` - Enable/disable semantic search (default: true)
- `OLLAMA_MODEL` - Model for embeddings (default: nomic-embed-text)
- `PORT` - Server port (default: 8000)
- `MIN_MESSAGES_FOR_PROGRESS` - Show progress for large conversations (default: 200)
- `EMBEDDINGS_CACHE_DIR` - Cache directory (default: server_data/embeddings)

## Architecture

### Data Flow
1. **Facebook Export** → placed in `fb_export/your_facebook_activity/messages/`
2. **Index Generation** → `build_conversation_index()` scans all folders and creates `server_data/conversation_index.json`
3. **Dynamic Loading** → Server loads conversations on-demand when user clicks
4. **Embedding Generation** → Background thread generates embeddings for semantic search
5. **HTML Generation** → Python generates complete HTML with embedded JavaScript

### Key Components

**messenger_server.py** - Main application
- `MessengerHTTPHandler`: Routes requests (/, /conversation?id=X, /rebuild, /semantic-search, /embedding-status, /summarize)
- `build_conversation_index()`: Scans all message folders and builds index
- `load_and_process_conversation()`: Processes JSON messages for a specific conversation
- `generate_conversation_html()`: Creates full HTML page with messages and AI analysis UI
- `generate_embeddings_async()`: Background thread for embedding generation
- `check_embeddings_exist()`: Check if embeddings are cached
- `/summarize` endpoint: Handles AI summarization requests with various prompt types

**semantic_search.py** - Semantic search and AI analysis engine
- `SemanticSearchEngine`: Main class for semantic search and summarization
  - `llm_model`: Ollama LLM model for summarization (default: llama3.2:3b)
- `embed_text()`: Generate embedding for single text using Ollama
- `embed_messages()`: Generate/load embeddings for all messages
- `search()`: Perform semantic search with cosine similarity
- `summarize_messages()`: Generate AI summaries with multiple prompt types:
  - `overview`: General conversation summary
  - `topics`: Main topics extraction
  - `timeline`: Chronological events
  - `memory`: Find plans and decisions
  - `custom`: User-defined prompts
- `_format_messages_for_llm()`: Prepare messages for LLM context
- `_build_prompt()`: Create prompts based on type and date filter
- Progress tracking via `generation_progress` dictionary

**Character Encoding Fix**
- `fix_czech_chars()`: Fixes mojibake by re-encoding latin-1 to UTF-8
- Applied to all text fields during processing
- Critical for Czech/Eastern European characters

### Data Structure

Facebook export expected structure:
```
fb_export/your_facebook_activity/messages/
├── inbox/
├── e2ee_cutover/
├── archived_threads/
├── filtered_threads/
└── message_requests/
    └── [conversation_folder]/
        └── message_1.json
```

Generated index format in `server_data/conversation_index.json`:
```json
{
  "id": 0,
  "participants": ["Name1", "Name2"],
  "message_count": 1234,
  "photo_count": 56,
  "first_date": "2020-01-01",
  "last_date": "2024-01-01",
  "path": "fb_export/your_facebook_activity/messages/inbox/...",
  "category": "inbox"
}
```

### HTML Generation Strategy
- Server generates complete HTML with all messages embedded
- No AJAX/dynamic loading after initial page load
- JavaScript handles client-side search/filtering only
- Photos/videos referenced by relative paths served by Python server

### Search Implementation
- Client-side text search with TreeWalker API
- Highlights all matches and provides navigation (Result X of Y)
- Search state managed in JavaScript with `searchResults` array

## Important Considerations

- **Virtual Environment**: ALWAYS use `.venv` for Python dependencies to avoid system conflicts
- **Port**: Server runs on port 8000 (configurable via `.env`)
- **Index caching**: `server_data/conversation_index.json` must be deleted or use `/rebuild` to refresh
- **Embedding caching**: Stored in `server_data/embeddings/` per conversation
- **Message ordering**: Facebook exports messages in reverse chronological order; code sorts them
- **Media files**: Server serves photos/videos from original export paths
- **Background threads**: Embedding generation runs in daemon threads
- **Progress tracking**: Only shown for conversations with 200+ messages (configurable)

## Key Learnings

1. **Always use virtual environments** - Dependencies should be installed in `.venv`, not globally
2. **Async processing for UX** - Long operations should run in background with progress feedback
3. **Smart defaults** - Show progress only when needed (large conversations)
4. **Configuration via .env** - Keep settings separate from code
5. **Caching is crucial** - Embeddings take time to generate but can be cached indefinitely
6. **Privacy first** - All processing local, even AI features use local Ollama models