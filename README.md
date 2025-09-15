# Facebook Messenger Export Viewer

A beautiful web-based viewer for your Facebook Messenger data export with full search, filtering, and navigation capabilities.

## Features

- 📱 **Complete Conversation Browser**: Browse all your Facebook Messenger conversations in one place
- 🔍 **Advanced Search**: Search within conversations with result count and navigation
- 🧠 **Semantic Search** (NEW): AI-powered search that understands meaning in Czech and English
- 🤖 **AI Conversation Analysis** (NEW): Generate summaries and insights using local LLM
- 📅 **Date Navigation**: Jump to any date with a date picker or quick buttons (Last Month, 3 Months, etc.)
- 🖼️ **Media Support**: View photos and videos inline
- 😀 **Emoji Reactions**: See all reactions on messages
- 📊 **Statistics**: View message counts, photos, videos, and hourly activity patterns
- 🎨 **Beautiful UI**: Modern, responsive design with color-coded messages
- 🚀 **Fast Performance**: Efficient loading and rendering of thousands of messages
- 🔒 **100% Private**: All processing happens locally on your machine

## Prerequisites

- Python 3.6 or higher
- Facebook data export in JSON format (see [How to Download](#how-to-download-facebook-data) below)
- (Optional) Ollama for semantic search and AI analysis - [Installation Guide](OLLAMA_SETUP.md)

## How to Download Facebook Data

### Quick Steps

1. Go to Facebook Settings → Settings & Privacy → Settings
2. Click "Download Your Information" (in Privacy section)
3. Select **JSON format** (not HTML)
4. Choose date range and select **Messages**
5. Request download and wait for email notification
6. Download the ZIP file when ready

### Detailed Instructions

1. **Access Download Tool**
   - Open Facebook on your computer
   - Click your profile icon → Settings & Privacy → Settings
   - In the left sidebar, find and click "Download Your Information"

2. **Configure Export Settings**
   - Click "Request a Download"
   - **Format**: Change from HTML to **JSON** (important!)
   - **Date Range**: Select your desired timeframe
   - **Your Information**: Check only "Messages" (or include other data if needed)
   - **Media Quality**: Choose based on your needs (higher quality = larger file)

3. **Download Process**
   - Click "Create File"
   - Wait for Facebook to prepare your data (can take hours to days)
   - You'll receive an email and Facebook notification when ready
   - Download the ZIP file (available for 4 days)

### Important Notes

- **JSON vs HTML**: Choose JSON format for this viewer to work properly
- **End-to-End Encrypted Messages** (2024): If using encrypted chats, you may need to download them separately via messenger.com → Privacy & Safety → End-to-end encrypted chats → Download secure storage data
- **Large Exports**: For many years of messages, the file can be several GB
- **Privacy**: The export contains sensitive personal data - handle with care

For more details, see [Facebook's official guide](https://www.facebook.com/help/212802592074644).

## Installation

1. Clone or download this repository:
```bash
git clone https://github.com/padak/fb_messenger_browser.git
cd fb_messenger_browser
```

2. Set up Python virtual environment and install dependencies:
```bash
# Create virtual environment
python -m venv .venv

# Activate it (macOS/Linux)
source .venv/bin/activate
# Activate it (Windows)
# .venv\Scripts\activate

# Install dependencies (make sure .venv is activated!)
pip install -r requirements.txt
```

3. Place your Facebook export in the `fb_export` folder:
```bash
fb_export/
└── your_facebook_activity/
    └── messages/
        ├── inbox/
        ├── archived_threads/
        ├── filtered_threads/
        └── ...
```

4. (Optional) Set up Ollama for semantic search and AI analysis:
```bash
# Install Ollama
brew install ollama  # macOS

# Start Ollama service
ollama serve

# Pull embedding model for semantic search
ollama pull nomic-embed-text

# Pull LLM model for conversation analysis (2GB)
ollama pull llama3.2:3b
```
See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for detailed instructions.

## Usage

### Quick Start

1. Start the server (make sure virtual environment is activated):
```bash
# Activate virtual environment first!
source .venv/bin/activate

# Then start the server
python messenger_server.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

3. Browse and select any conversation to view!

### Features Guide

#### Main Conversation List
- **Search**: Use the search bar to filter conversations by participant names
- **Categories**: Conversations are organized by folder (Inbox, Archived, etc.)
- **Statistics**: See message count and date range for each conversation
- **Photo Badge**: Green badge shows number of photos in conversation

#### Conversation View
- **Search Messages**: Search with highlighting and "Result X of Y" navigation
- **Semantic Search**: Toggle between text and AI-powered semantic search
  - Understands meaning, not just keywords
  - Works across Czech and English
  - Find related topics even with different words
- **AI Conversation Analysis**: Generate insights with ready-made prompts
  - **Overview & Topics**: Summarize conversation, extract main topics, create timeline
  - **Time-based Analysis**: Review specific months or years
  - **Memory Search**: Find all plans, decisions, or ask custom questions
  - Works with Czech and English conversations
  - All processing happens locally using Ollama
- **Date Picker**: Jump to any date in the conversation
- **Quick Dates**: Jump to Last Month, 3 Months, 6 Months, or 1 Year ago
- **Filters**: Filter by All, Photos, Videos, or Links
- **Activity Chart**: See hourly message distribution
- **Progress Tracking**: See real-time progress for embedding generation on large conversations
- **Back Button**: Return to conversation list

### Advanced Options

#### Rebuild Conversation Index
If you add new data or want to refresh the conversation list:
```
http://localhost:8000/rebuild
```


## Configuration

Create a `.env` file to customize settings (optional):
```bash
# Enable/disable semantic search
SEMANTIC_SEARCH_ENABLED=true

# Ollama model for embeddings
OLLAMA_MODEL=nomic-embed-text

# Server port
PORT=8000

# Show progress modal for conversations with this many messages
MIN_MESSAGES_FOR_PROGRESS=200

# Cache directory for embeddings
EMBEDDINGS_CACHE_DIR=server_data/embeddings
```

## File Structure

```
fb_mess/
├── messenger_server.py          # Main server with UI
├── semantic_search.py           # Semantic search engine with Ollama
├── requirements.txt             # Python dependencies
├── .env                        # Configuration (optional)
├── OLLAMA_SETUP.md             # Ollama installation guide
├── test_semantic_search.py     # Test suite for semantic search
├── fb_export/                   # Your Facebook export goes here (gitignored)
│   └── your_facebook_activity/
├── server_data/                 # Generated files (gitignored)
│   ├── conversation_index.json  # Conversation index
│   ├── embeddings/             # Cached embeddings for semantic search
│   └── *.html                   # Generated HTML files
├── .venv/                      # Python virtual environment (gitignored)
└── README.md                   # This file
```

## Technical Details

### Architecture
- **Backend**: Python HTTP server with dynamic HTML generation
- **Frontend**: Pure JavaScript (no frameworks required)
- **Data Processing**: Automatic Czech character encoding fixes
- **Semantic Search**: Ollama-powered embeddings with multilingual support
- **Caching**:
  - Conversation index cached in JSON for fast loading
  - Embeddings cached per conversation to avoid regeneration
- **Async Processing**: Background embedding generation for large conversations

### Encoding Fixes
The viewer automatically fixes common encoding issues in Facebook exports, particularly for Czech characters (č, š, ž, etc.) that may appear as mojibake (Ã¡, Ä\x8d, etc.).

### Performance
- Handles conversations with thousands of messages efficiently
- Lazy loading of images
- Optimized search with real-time highlighting
- Fast conversation switching
- Background embedding generation doesn't block UI
- Progress tracking for large conversations (200+ messages)
- Cached embeddings for instant semantic search after first generation

## Troubleshooting

### Port Already in Use
If you get an "Address already in use" error:
```bash
# Kill any process using port 8000
lsof -ti:8000 | xargs kill -9

# Then restart the server
# Activate virtual environment first!
source .venv/bin/activate

python messenger_server.py
```

### Missing Conversations
If some conversations don't appear:
1. Check that your data is in the correct folder structure
2. Visit http://localhost:8000/rebuild to rebuild the index

### Character Encoding Issues
The viewer automatically fixes most encoding issues. If you still see strange characters, ensure your export is complete and not corrupted.

### Semantic Search Not Working
If semantic search toggle doesn't appear:
1. Check Ollama is installed: `ollama --version`
2. Ensure Ollama is running: `ollama serve`
3. Pull the model: `ollama pull nomic-embed-text`
4. Restart the messenger server
5. Check console for "✅ Semantic search is available" message

### AI Analysis Not Working
If the AI Conversation Analysis section doesn't appear or summaries fail:
1. Ensure Ollama is running: `ollama serve`
2. Pull the LLM model: `ollama pull llama3.2:3b`
3. Check console for "✅ Ollama LLM model 'llama3.2:3b' is ready" message
4. The model download is ~2GB, ensure you have enough disk space
5. Summaries work best with conversations that have substantial content

### Slow Embedding Generation
First-time embedding generation can take 5-10 minutes for large conversations:
- Progress is shown for conversations with 200+ messages
- Embeddings are cached - subsequent searches are instant
- You can adjust `MIN_MESSAGES_FOR_PROGRESS` in `.env`

## Privacy Note

This tool runs entirely locally on your computer. Your messages never leave your machine and no data is sent to any external servers. Even the AI-powered semantic search uses local Ollama models - your data remains 100% private.

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

Built with ❤️ for anyone who wants to explore their Facebook Messenger history in a beautiful and functional way.