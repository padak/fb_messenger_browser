#!/usr/bin/env python3
"""
Configuration module for Messenger Server
Centralizes all configuration and environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Server Configuration
PORT = int(os.getenv('PORT', 8000))
HOST = os.getenv('HOST', '127.0.0.1')
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Path Configuration
BASE_DIR = Path(__file__).parent
FB_EXPORT_PATH = Path(os.getenv('FB_EXPORT_PATH', 'fb_export/your_facebook_activity/messages'))
SERVER_DATA_PATH = Path(os.getenv('SERVER_DATA_PATH', 'server_data'))
EMBEDDINGS_CACHE_DIR = Path(os.getenv('EMBEDDINGS_CACHE_DIR', SERVER_DATA_PATH / 'embeddings'))

# Ensure directories exist
SERVER_DATA_PATH.mkdir(exist_ok=True)
EMBEDDINGS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Conversation Index
CONVERSATION_INDEX_FILE = SERVER_DATA_PATH / 'conversation_index.json'
CONVERSATION_FOLDERS = ['inbox', 'filtered_threads', 'archived_threads', 'message_requests', 'e2ee_cutover']

# Semantic Search Configuration
SEMANTIC_SEARCH_ENABLED = os.getenv('SEMANTIC_SEARCH_ENABLED', 'true').lower() == 'true'
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'nomic-embed-text')
OLLAMA_LLM_MODEL = os.getenv('OLLAMA_LLM_MODEL', 'llama3.2:3b')
OLLAMA_TIMEOUT = int(os.getenv('OLLAMA_TIMEOUT', 120))

# Search Configuration
MAX_SEARCH_RESULTS = int(os.getenv('MAX_SEARCH_RESULTS', 20))
MIN_MESSAGES_FOR_PROGRESS = int(os.getenv('MIN_MESSAGES_FOR_PROGRESS', 200))
SEARCH_HIGHLIGHT_COLOR = os.getenv('SEARCH_HIGHLIGHT_COLOR', '#ffeb3b')
SEARCH_CURRENT_COLOR = os.getenv('SEARCH_CURRENT_COLOR', '#ff9800')

# UI Configuration
SCROLL_TO_TOP_THRESHOLD = int(os.getenv('SCROLL_TO_TOP_THRESHOLD', 500))
MAX_MESSAGE_PREVIEW = int(os.getenv('MAX_MESSAGE_PREVIEW', 200))
MAX_PHOTO_SIZE = int(os.getenv('MAX_PHOTO_SIZE', 250))
MAX_VIDEO_WIDTH = int(os.getenv('MAX_VIDEO_WIDTH', 400))

# Performance Configuration
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 8192))
MAX_CONVERSATIONS_PER_CATEGORY = int(os.getenv('MAX_CONVERSATIONS_PER_CATEGORY', 500))
EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', 32))
CACHE_TTL = int(os.getenv('CACHE_TTL', 3600))  # seconds

# Security Configuration
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 100 * 1024 * 1024))  # 100MB
RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 100))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))  # seconds

# Color Palette (for consistency)
COLORS = {
    'bg_primary': '#ffffff',
    'bg_secondary': '#fafafa',
    'bg_hover': '#f5f5f5',
    'text_primary': '#0a0a0a',
    'text_secondary': '#6b7280',
    'text_tertiary': '#9ca3af',
    'border_color': '#e5e7eb',
    'accent_blue': '#3b82f6',
    'accent_green': '#10b981',
    'accent_purple': '#8b5cf6',
    'sidebar_bg': '#f8f9fa',
    'tooltip_bg': 'rgba(0,0,0,0.8)',
    'tooltip_text': '#ffffff',
    'badge_green_bg': '#10b981',
    'badge_green_text': '#ffffff',
}

# Avatar Colors (consistent palette)
AVATAR_COLORS = [
    {'bg': '#fef3c7', 'text': '#92400e'},  # Amber
    {'bg': '#dbeafe', 'text': '#1e40af'},  # Blue
    {'bg': '#dcfce7', 'text': '#166534'},  # Green
    {'bg': '#fce7f3', 'text': '#9f1239'},  # Pink
    {'bg': '#e9d5ff', 'text': '#6b21a8'},  # Purple
    {'bg': '#fed7aa', 'text': '#9a3412'},  # Orange
    {'bg': '#fecaca', 'text': '#991b1b'},  # Red
    {'bg': '#d1fae5', 'text': '#065f46'},  # Teal
]

# Message Sender Colors (for conversation view)
MESSAGE_COLORS = [
    {'bg': '#e3f2fd', 'text': '#000'},  # Blue
    {'bg': '#fce4ec', 'text': '#000'},  # Pink
    {'bg': '#e8f5e9', 'text': '#000'},  # Green
    {'bg': '#fff3e0', 'text': '#000'},  # Orange
]

def get_config():
    """Return all configuration as a dictionary"""
    return {
        'PORT': PORT,
        'HOST': HOST,
        'DEBUG': DEBUG,
        'FB_EXPORT_PATH': str(FB_EXPORT_PATH),
        'SERVER_DATA_PATH': str(SERVER_DATA_PATH),
        'EMBEDDINGS_CACHE_DIR': str(EMBEDDINGS_CACHE_DIR),
        'SEMANTIC_SEARCH_ENABLED': SEMANTIC_SEARCH_ENABLED,
        'OLLAMA_MODEL': OLLAMA_MODEL,
        'MIN_MESSAGES_FOR_PROGRESS': MIN_MESSAGES_FOR_PROGRESS,
        'MAX_SEARCH_RESULTS': MAX_SEARCH_RESULTS,
        'COLORS': COLORS,
    }

def validate_config():
    """Validate configuration and environment"""
    errors = []

    # Check if FB export exists
    if not FB_EXPORT_PATH.exists():
        errors.append(f"Facebook export path not found: {FB_EXPORT_PATH}")

    # Check port range
    if not 1 <= PORT <= 65535:
        errors.append(f"Invalid port number: {PORT}")

    # Check Ollama if semantic search enabled
    if SEMANTIC_SEARCH_ENABLED:
        try:
            import ollama
            # Test connection
            ollama.list()
        except Exception as e:
            errors.append(f"Ollama not available: {e}")

    return errors

if __name__ == '__main__':
    # Test configuration
    config = get_config()
    print("Current Configuration:")
    for key, value in config.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Validate
    errors = validate_config()
    if errors:
        print("\nConfiguration Errors:")
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("\n✅ Configuration valid")