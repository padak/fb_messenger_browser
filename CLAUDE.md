# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a Facebook Messenger Export Viewer - a web-based tool for browsing and searching Facebook Messenger conversation exports with full Czech character encoding fixes.

## Commands

### Running the Application
```bash
# Start the main server (recommended)
python3 messenger_server.py
# Opens at http://localhost:8000

# Alternative: Process single conversation (legacy)
python3 parse_messages_final.py
# Generates messenger_export_final.html

# Interactive CLI version
python3 parse_messages_interactive.py
# Select conversation number from list
```

### Common Operations
```bash
# Rebuild conversation index (if adding new data)
curl http://localhost:8000/rebuild

# Kill server if port 8000 is in use
lsof -ti:8000 | xargs kill -9
```

## Architecture

### Data Flow
1. **Facebook Export** → placed in `fb_export/your_facebook_activity/messages/`
2. **Index Generation** → `build_conversation_index()` scans all folders and creates `server_data/conversation_index.json`
3. **Dynamic Loading** → Server loads conversations on-demand when user clicks
4. **HTML Generation** → Python generates complete HTML with embedded JavaScript

### Key Components

**messenger_server.py** - Main application
- `MessengerHTTPHandler`: Routes requests (/, /conversation?id=X, /rebuild)
- `build_conversation_index()`: Scans all message folders and builds index
- `load_and_process_conversation()`: Processes JSON messages for a specific conversation
- `generate_conversation_html()`: Creates full HTML page with messages

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

- **Conversation paths**: Hardcoded in `parse_messages_final.py` to `fb_export/your_facebook_activity/messages/e2ee_cutover/luciesperkova_10153589231783469`
- **Port**: Server runs on port 8000 (hardcoded)
- **Index caching**: `server_data/conversation_index.json` must be deleted or use `/rebuild` to refresh
- **Message ordering**: Facebook exports messages in reverse chronological order; code sorts them
- **Media files**: Server serves photos/videos from original export paths