# Facebook Messenger Export Viewer

A beautiful web-based viewer for your Facebook Messenger data export with full search, filtering, and navigation capabilities.

## Features

- 📱 **Complete Conversation Browser**: Browse all your Facebook Messenger conversations in one place
- 🔍 **Advanced Search**: Search within conversations with result count and navigation
- 📅 **Date Navigation**: Jump to any date with a date picker or quick buttons (Last Month, 3 Months, etc.)
- 🖼️ **Media Support**: View photos and videos inline
- 😀 **Emoji Reactions**: See all reactions on messages
- 📊 **Statistics**: View message counts, photos, videos, and hourly activity patterns
- 🎨 **Beautiful UI**: Modern, responsive design with color-coded messages
- 🚀 **Fast Performance**: Efficient loading and rendering of thousands of messages

## Prerequisites

- Python 3.6 or higher
- Facebook data export (downloaded from Facebook settings)

## Installation

1. Clone or download this repository:
```bash
git clone https://github.com/yourusername/fb_mess.git
cd fb_mess
```

2. Place your Facebook export in the `fb_export` folder:
```bash
fb_export/
└── your_facebook_activity/
    └── messages/
        ├── inbox/
        ├── archived_threads/
        ├── filtered_threads/
        └── ...
```

## Usage

### Quick Start

1. Start the server:
```bash
python3 messenger_server.py
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
- **Date Picker**: Jump to any date in the conversation
- **Quick Dates**: Jump to Last Month, 3 Months, 6 Months, or 1 Year ago
- **Filters**: Filter by All, Photos, Videos, or Links
- **Activity Chart**: See hourly message distribution
- **Back Button**: Return to conversation list

### Advanced Options

#### Rebuild Conversation Index
If you add new data or want to refresh the conversation list:
```
http://localhost:8000/rebuild
```

#### Use Specific Conversation (Legacy)
To process a single conversation directly:
```bash
python3 parse_messages_final.py
```
This will generate `messenger_export_final.html` for the hardcoded conversation path.

## File Structure

```
fb_mess/
├── messenger_server.py          # Main server with UI
├── parse_messages_final.py      # Single conversation processor
├── parse_messages_interactive.py # Interactive CLI version
├── fb_export/                   # Your Facebook export goes here (gitignored)
│   └── your_facebook_activity/
├── server_data/                 # Generated files (gitignored)
│   ├── conversation_index.json  # Conversation index
│   └── *.html                   # Generated HTML files
└── README.md                   # This file
```

## Technical Details

### Architecture
- **Backend**: Python HTTP server with dynamic HTML generation
- **Frontend**: Pure JavaScript (no frameworks required)
- **Data Processing**: Automatic Czech character encoding fixes
- **Caching**: Conversation index cached in JSON for fast loading

### Encoding Fixes
The viewer automatically fixes common encoding issues in Facebook exports, particularly for Czech characters (č, š, ž, etc.) that may appear as mojibake (Ã¡, Ä\x8d, etc.).

### Performance
- Handles conversations with thousands of messages efficiently
- Lazy loading of images
- Optimized search with real-time highlighting
- Fast conversation switching

## Troubleshooting

### Port Already in Use
If you get an "Address already in use" error:
```bash
# Kill any process using port 8000
lsof -ti:8000 | xargs kill -9

# Then restart the server
python3 messenger_server.py
```

### Missing Conversations
If some conversations don't appear:
1. Check that your data is in the correct folder structure
2. Visit http://localhost:8000/rebuild to rebuild the index

### Character Encoding Issues
The viewer automatically fixes most encoding issues. If you still see strange characters, ensure your export is complete and not corrupted.

## Privacy Note

This tool runs entirely locally on your computer. Your messages never leave your machine and no data is sent to any external servers.

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

Built with ❤️ for anyone who wants to explore their Facebook Messenger history in a beautiful and functional way.