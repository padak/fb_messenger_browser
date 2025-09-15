#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import html
import re
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
PORT = int(os.getenv('PORT', 8000))
MIN_MESSAGES_FOR_PROGRESS = int(os.getenv('MIN_MESSAGES_FOR_PROGRESS', 200))

# Global flag for semantic search availability
SEMANTIC_SEARCH_AVAILABLE = False
semantic_engine = None

# Check if semantic search is enabled in environment
if os.getenv('SEMANTIC_SEARCH_ENABLED', 'true').lower() == 'true':
    try:
        from semantic_search import SemanticSearchEngine, check_ollama_installation
        if check_ollama_installation():
            print("✅ Semantic search is available (Ollama detected)")
            SEMANTIC_SEARCH_AVAILABLE = True
            ollama_model = os.getenv('OLLAMA_MODEL', 'nomic-embed-text')
            cache_dir = os.getenv('EMBEDDINGS_CACHE_DIR', 'server_data/embeddings')
            semantic_engine = SemanticSearchEngine(model_name=ollama_model, cache_dir=cache_dir)
        else:
            print("⚠️ Semantic search disabled (Ollama not running)")
            print("   To enable: 1) Install Ollama  2) Run 'ollama serve'  3) Pull model with 'ollama pull nomic-embed-text'")
    except ImportError as e:
        print(f"⚠️ Semantic search disabled (missing dependencies: {e})")
        print("   To enable: pip install -r requirements.txt")
    except Exception as e:
        print(f"⚠️ Semantic search disabled (error: {e})")
else:
    print("ℹ️ Semantic search disabled via environment variable")

# Import parsing functions from our existing module
def fix_czech_chars(text):
    """Fix Czech character encoding issues"""
    if not text:
        return text
    try:
        if isinstance(text, str):
            if 'Ã' in text or 'Ä' in text or 'Å' in text:
                try:
                    fixed = text.encode('latin-1').decode('utf-8')
                    text = fixed
                except:
                    pass
    except:
        pass
    return text

def format_timestamp(timestamp_ms):
    """Format timestamp to readable date and time"""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)
    return {
        'date': dt.strftime('%A, %B %d, %Y'),
        'time': dt.strftime('%-I:%M %p'),
        'full': dt.strftime('%b %d, %Y, %-I:%M %p'),
        'iso': dt.isoformat(),
        'iso_date': dt.strftime('%Y-%m-%d'),
        'hour': dt.hour
    }

def get_conversation_info(conv_path):
    """Get basic info about a conversation"""
    json_path = Path(conv_path) / 'message_1.json'

    if not json_path.exists():
        return None

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        participants = []
        for p in data.get('participants', []):
            name = fix_czech_chars(p.get('name', 'Unknown'))
            participants.append(name)

        message_count = len(data.get('messages', []))

        # Get date range
        messages = data.get('messages', [])
        if messages:
            first_msg = messages[-1]
            last_msg = messages[0]
            first_date = datetime.fromtimestamp(first_msg.get('timestamp_ms', 0) / 1000).strftime('%Y-%m-%d')
            last_date = datetime.fromtimestamp(last_msg.get('timestamp_ms', 0) / 1000).strftime('%Y-%m-%d')
        else:
            first_date = 'N/A'
            last_date = 'N/A'

        # Count photos
        photo_count = sum(1 for msg in messages if msg.get('photos'))

        return {
            'participants': participants,
            'message_count': message_count,
            'photo_count': photo_count,
            'first_date': first_date,
            'last_date': last_date,
            'path': str(conv_path)
        }
    except Exception as e:
        print(f"Error processing {conv_path}: {e}")
        return None

def build_conversation_index():
    """Build an index of all conversations"""
    print("🔍 Building conversation index...")
    base_path = Path('fb_export/your_facebook_activity/messages')
    conversations = []

    folders_to_check = ['inbox', 'filtered_threads', 'archived_threads', 'message_requests', 'e2ee_cutover']

    for folder in folders_to_check:
        folder_path = base_path / folder
        if not folder_path.exists():
            continue

        print(f"  Scanning {folder}...")
        for conv_folder in folder_path.iterdir():
            if conv_folder.is_dir():
                info = get_conversation_info(conv_folder)
                if info:
                    info['category'] = folder
                    info['id'] = len(conversations)
                    conversations.append(info)

    # Save index
    with open('server_data/conversation_index.json', 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)

    print(f"✅ Indexed {len(conversations)} conversations")
    return conversations

def load_conversation_index():
    """Load or build conversation index"""
    index_path = Path('server_data/conversation_index.json')

    if not index_path.exists():
        return build_conversation_index()

    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_index_html(conversations):
    """Generate HTML for conversation list"""

    # Group by category
    categories = {}
    for conv in conversations:
        cat = conv['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(conv)

    # Sort each category by message count
    for cat in categories:
        categories[cat].sort(key=lambda x: x['message_count'], reverse=True)

    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Messenger Conversations</title>
    <style>
        :root {
            --bg-primary: #ffffff;
            --bg-secondary: #fafafa;
            --bg-hover: #f5f5f5;
            --text-primary: #0a0a0a;
            --text-secondary: #6b7280;
            --text-tertiary: #9ca3af;
            --border-color: #e5e7eb;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-purple: #8b5cf6;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.07);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
            --radius-sm: 6px;
            --radius-md: 8px;
            --radius-lg: 12px;
            --transition: all 0.2s ease;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-secondary);
            min-height: 100vh;
            padding: 0;
            color: var(--text-primary);
            line-height: 1.6;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 24px;
        }

        .header {
            background: var(--bg-primary);
            border-bottom: 1px solid var(--border-color);
            padding: 48px 0;
            margin-bottom: 32px;
        }

        .header h1 {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .header-subtitle {
            color: var(--text-secondary);
            font-size: 16px;
            margin-bottom: 24px;
        }

        .stats {
            display: flex;
            gap: 48px;
            margin-top: 24px;
        }

        .stat {
            text-align: left;
        }

        .stat-number {
            font-size: 28px;
            font-weight: 700;
            color: var(--text-primary);
            letter-spacing: -0.5px;
        }

        .stat-label {
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        .search-box {
            margin: 32px 0;
        }

        .search-input {
            width: 100%;
            max-width: 600px;
            padding: 12px 20px 12px 48px;
            font-size: 15px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            background: var(--bg-primary);
            transition: var(--transition);
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="%236b7280" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.35-4.35"></path></svg>');
            background-repeat: no-repeat;
            background-position: 16px center;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }

        .search-input::placeholder {
            color: var(--text-tertiary);
        }

        .category {
            background: var(--bg-primary);
            border-radius: var(--radius-lg);
            margin-bottom: 24px;
            border: 1px solid var(--border-color);
            overflow: hidden;
            transition: var(--transition);
        }

        .category-header {
            background: var(--bg-primary);
            color: var(--text-primary);
            padding: 16px 24px;
            font-size: 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .conversations {
            max-height: 500px;
            overflow-y: auto;
        }

        .conversations::-webkit-scrollbar {
            width: 8px;
        }

        .conversations::-webkit-scrollbar-track {
            background: var(--bg-secondary);
        }

        .conversations::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        .conversations::-webkit-scrollbar-thumb:hover {
            background: var(--text-tertiary);
        }

        .conversation {
            display: flex;
            align-items: center;
            padding: 16px 24px;
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            transition: var(--transition);
        }

        .conversation:last-child {
            border-bottom: none;
        }

        .conversation:hover {
            background: var(--bg-hover);
        }

        .conversation-avatar {
            width: 44px;
            height: 44px;
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            color: var(--text-secondary);
            background: var(--bg-secondary);
            margin-right: 16px;
            flex-shrink: 0;
            font-size: 16px;
            border: 1px solid var(--border-color);
        }

        .conversation-info {
            flex: 1;
            min-width: 0;
        }

        .conversation-name {
            font-weight: 600;
            font-size: 15px;
            margin-bottom: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--text-primary);
        }

        .conversation-meta {
            display: flex;
            gap: 16px;
            font-size: 13px;
            color: var(--text-secondary);
        }

        .conversation-stats {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .message-count {
            background: var(--bg-secondary);
            color: var(--text-primary);
            padding: 6px 12px;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 13px;
            border: 1px solid var(--border-color);
        }

        .date-range {
            font-size: 12px;
            color: var(--text-tertiary);
        }

        .loading {
            text-align: center;
            padding: 60px;
            color: var(--text-secondary);
            font-size: 16px;
        }

        .photo-badge {
            background: var(--accent-green);
            color: #0a0a0a;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            font-size: 12px;
            font-weight: 600;
        }

        /* Remove avatar gradients - use subtle backgrounds */
        .avatar-0 { background: #fef3c7; color: #92400e; }
        .avatar-1 { background: #dbeafe; color: #1e40af; }
        .avatar-2 { background: #dcfce7; color: #166534; }
        .avatar-3 { background: #fce7f3; color: #9f1239; }
        .avatar-4 { background: #e9d5ff; color: #6b21a8; }
        .avatar-5 { background: #fed7aa; color: #9a3412; }
        .avatar-6 { background: #fecaca; color: #991b1b; }
        .avatar-7 { background: #d1fae5; color: #065f46; }
    </style>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>Facebook Messenger Archive</h1>
            <p class="header-subtitle">Browse and search your complete message history</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">''' + str(len(conversations)) + '''</div>
                    <div class="stat-label">Conversations</div>
                </div>
                <div class="stat">
                    <div class="stat-number">''' + f"{sum(c['message_count'] for c in conversations):,}" + '''</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat">
                    <div class="stat-number">''' + f"{sum(c.get('photo_count', 0) for c in conversations):,}" + '''</div>
                    <div class="stat-label">Total Photos</div>
                </div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="search-box">
            <input type="text" class="search-input" id="search" placeholder="Search conversations...">
        </div>

        <div id="conversation-list">'''

    # Generate categories
    category_order = ['inbox', 'e2ee_cutover', 'archived_threads', 'message_requests', 'filtered_threads']

    for cat in category_order:
        if cat not in categories:
            continue

        cat_display = cat.replace('_', ' ').title()
        html_content += f'''
        <div class="category">
            <div class="category-header">{cat_display} • {len(categories[cat])} conversations</div>
            <div class="conversations">'''

        for conv in categories[cat]:
            participants = ', '.join(conv['participants'][:2])
            if len(conv['participants']) > 2:
                participants += f" +{len(conv['participants'])-2}"

            initials = ''.join([p[0].upper() for p in conv['participants'][0].split()[:2]])
            avatar_class = f"avatar-{conv['id'] % 8}"

            photo_badge = f'<span class="photo-badge">{conv.get("photo_count", 0)} photos</span>' if conv.get('photo_count', 0) > 0 else ''

            html_content += f'''
                <div class="conversation" onclick="loadConversation({conv['id']})">
                    <div class="conversation-avatar {avatar_class}">{initials}</div>
                    <div class="conversation-info">
                        <div class="conversation-name">{html.escape(participants)}</div>
                        <div class="conversation-meta">
                            <span>📅 {conv['first_date']} to {conv['last_date']}</span>
                            {photo_badge}
                        </div>
                    </div>
                    <div class="conversation-stats">
                        <span class="message-count">{conv['message_count']} msgs</span>
                    </div>
                </div>'''

        html_content += '''
            </div>
        </div>'''

    html_content += '''
        </div>
    </div>

    <script>
        // Search functionality
        document.getElementById('search').addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const conversations = document.querySelectorAll('.conversation');

            conversations.forEach(conv => {
                const name = conv.querySelector('.conversation-name').textContent.toLowerCase();
                if (name.includes(searchTerm)) {
                    conv.style.display = 'flex';
                } else {
                    conv.style.display = 'none';
                }
            });

            // Update category visibility
            document.querySelectorAll('.category').forEach(cat => {
                const visibleConvs = cat.querySelectorAll('.conversation:not([style*="none"])');
                cat.style.display = visibleConvs.length > 0 ? 'block' : 'none';
            });
        });

        function loadConversation(id) {
            window.location.href = '/conversation?id=' + id;
        }
    </script>
</body>
</html>'''

    return html_content

def escape_html_content(text):
    """Escape HTML but preserve line breaks"""
    if not text:
        return ''
    text = html.escape(text)
    text = re.sub(
        r'(https?://[^\s]+)',
        r'<a href="\1" target="_blank">\1</a>',
        text
    )
    return text

def load_and_process_conversation(conv_path):
    """Load and process messages from a conversation"""
    messages = []
    participants = set()

    json_path = Path(conv_path) / 'message_1.json'

    if not json_path.exists():
        raise FileNotFoundError(f"Message file not found: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extract participants
    for p in data.get('participants', []):
        name = fix_czech_chars(p.get('name', 'Unknown'))
        participants.add(name)

    # Process messages
    for msg in data.get('messages', []):
        processed_msg = {
            'sender': fix_czech_chars(msg.get('sender_name', 'Unknown')),
            'timestamp_ms': msg.get('timestamp_ms', 0),
            'content': fix_czech_chars(msg.get('content', '')),
            'photos': msg.get('photos', []),
            'videos': msg.get('videos', []),
            'reactions': [],
            'type': msg.get('type', 'Generic')
        }

        # Format timestamp
        ts_data = format_timestamp(processed_msg['timestamp_ms'])
        processed_msg.update(ts_data)

        # Process reactions
        for reaction in msg.get('reactions', []):
            processed_msg['reactions'].append({
                'actor': fix_czech_chars(reaction.get('actor', '')),
                'reaction': reaction.get('reaction', '')
            })

        # Check for links
        if processed_msg['content']:
            processed_msg['has_link'] = bool(re.search(r'https?://[^\s]+', processed_msg['content']))
        else:
            processed_msg['has_link'] = False

        messages.append(processed_msg)

    # Sort messages by timestamp (oldest first)
    messages.sort(key=lambda x: x['timestamp_ms'])

    return messages, list(participants)

def check_embeddings_exist(conversation_id):
    """Check if embeddings exist for a conversation without generating them."""
    if not SEMANTIC_SEARCH_AVAILABLE or not semantic_engine:
        return False

    cache_path = semantic_engine._get_cache_path(conversation_id)
    return cache_path.exists()

def get_or_generate_embeddings(messages, conversation_id):
    """Get or generate embeddings for messages if semantic search is available."""
    if not SEMANTIC_SEARCH_AVAILABLE or not semantic_engine:
        return None

    try:
        # Generate embeddings (will use cache if available)
        embeddings = semantic_engine.embed_messages(messages, conversation_id)
        return embeddings
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return None

def generate_embeddings_async(messages, conversation_id):
    """Generate embeddings in a background thread."""
    if not SEMANTIC_SEARCH_AVAILABLE or not semantic_engine:
        return

    def generate():
        try:
            print(f"🔄 Starting background embedding generation for conversation {conversation_id}")
            semantic_engine.embed_messages(messages, conversation_id)
            print(f"✅ Completed embedding generation for conversation {conversation_id}")
        except Exception as e:
            print(f"❌ Error generating embeddings in background: {e}")

    thread = threading.Thread(target=generate, daemon=True)
    thread.start()

def perform_semantic_search(query, messages, embeddings, top_k=20):
    """Perform semantic search on messages."""
    if not SEMANTIC_SEARCH_AVAILABLE or not semantic_engine or not embeddings:
        return []

    try:
        results = semantic_engine.search(query, messages, embeddings, top_k=top_k)
        return results
    except Exception as e:
        print(f"Error in semantic search: {e}")
        return []

def generate_conversation_html(messages, participants, conversation_id=None):
    """Generate HTML for a single conversation"""

    # Calculate stats
    stats = {
        'total': len(messages),
        'photos': sum(1 for m in messages if m['photos']),
        'videos': sum(1 for m in messages if m['videos']),
        'links': sum(1 for m in messages if m['has_link']),
        'hourly': [0] * 24,
        'first_date': messages[0]['iso_date'] if messages else '',
        'last_date': messages[-1]['iso_date'] if messages else ''
    }

    for msg in messages:
        stats['hourly'][msg['hour']] += 1

    # Generate hourly chart
    max_hour = max(stats['hourly']) if max(stats['hourly']) > 0 else 1
    hour_chart = ''
    for i, count in enumerate(stats['hourly']):
        height = (count / max_hour) * 100 if max_hour > 0 else 0
        hour_chart += f'<div class="hour-bar" style="height: {height}%" data-tooltip="{i}:00 - {count} msgs"></div>'

    # Generate messages HTML
    messages_html = ''
    last_date = None

    # Create sender color mapping
    unique_senders = list(set(msg['sender'] for msg in messages))
    sender_colors = {sender: idx % 4 for idx, sender in enumerate(unique_senders)}

    for msg in messages:
        # Add date separator
        if msg['date'] != last_date:
            messages_html += f'<div class="date-separator"><span>{msg["date"]}</span></div>\n'
            last_date = msg['date']

        # Create avatar initials
        initials = ''.join([n[0].upper() for n in msg['sender'].split()[:2]])

        # Determine sender class
        sender_class = f'message-sender-{sender_colors[msg["sender"]]}'

        # Start message
        messages_html += f'''<div class="message {sender_class}" data-timestamp="{msg['timestamp_ms']}">
    <div class="avatar">{initials}</div>
    <div class="message-content">
        <div class="message-header">
            <span class="sender-name">{html.escape(msg['sender'])}</span>
            <span class="message-time">{msg['full']}</span>
        </div>'''

        # Add message text
        if msg['content']:
            messages_html += f'\n        <div class="message-text">{escape_html_content(msg["content"])}</div>'

        # Add photos
        if msg['photos']:
            messages_html += '\n        <div class="message-photos">'
            for photo in msg['photos']:
                photo_path = photo.get('uri', '')
                # Remove 'data/' prefix if present for correct serving
                if photo_path.startswith('fb_export/'):
                    photo_path = photo_path
                elif photo_path.startswith('your_facebook_activity'):
                    photo_path = 'fb_export/' + photo_path
                messages_html += f'\n            <img src="/{photo_path}" class="message-photo" onclick="openModal(this.src)" alt="Photo" loading="lazy">'
            messages_html += '\n        </div>'

        # Add videos
        if msg['videos']:
            for video in msg['videos']:
                video_path = video.get('uri', '')
                # Remove 'data/' prefix if present for correct serving
                if video_path.startswith('fb_export/'):
                    video_path = video_path
                elif video_path.startswith('your_facebook_activity'):
                    video_path = 'fb_export/' + video_path
                messages_html += f'''
        <video controls class="message-video">
            <source src="/{video_path}" type="video/mp4">
            Your browser does not support the video tag.
        </video>'''

        # Add reactions
        if msg['reactions']:
            messages_html += '\n        <div class="reactions">'
            for reaction in msg['reactions']:
                messages_html += f'\n            <span class="reaction">{reaction["reaction"]} {html.escape(reaction["actor"])}</span>'
            messages_html += '\n        </div>'

        messages_html += '\n    </div>\n</div>\n'

    # Load template from parse_messages_final.py and modify it
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Messenger - {participants}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            color: #1c1e21;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 320px 1fr;
            height: 100vh;
        }}

        /* Back button */
        .back-button {{
            background: #f5f5f5;
            border: 1px solid #e5e7eb;
            color: #0a0a0a;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 20px;
            width: 100%;
            transition: all 0.2s;
            font-weight: 500;
        }}

        .back-button:hover {{
            background: #e5e7eb;
        }}

        /* Sidebar */
        .sidebar {{
            background: #f8f9fa;
            color: #0a0a0a;
            padding: 24px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 20px;
            border-right: 1px solid #e5e7eb;
        }}

        .sidebar h1 {{
            font-size: 1.5em;
            margin-bottom: 10px;
            color: #0a0a0a;
            font-weight: 700;
        }}

        .participants {{
            font-size: 0.9em;
            color: #6b7280;
            margin-bottom: 20px;
        }}

        .stats {{
            background: #fafafa;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}

        .stat-item {{
            margin: 10px 0;
        }}

        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #0a0a0a;
        }}

        .stat-label {{
            font-size: 0.9em;
            color: #6b7280;
        }}

        /* Date Navigation */
        .date-navigation {{
            background: #fafafa;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
        }}

        .date-picker {{
            width: 100%;
            padding: 10px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background: white;
            font-size: 14px;
            margin-bottom: 10px;
            color: #0a0a0a;
        }}

        .quick-dates {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
        }}

        .quick-date-btn {{
            padding: 8px;
            border: none;
            border-radius: 5px;
            background: white;
            border: 1px solid #e5e7eb;
            color: #0a0a0a;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }}

        .quick-date-btn:hover {{
            background: #e5e7eb;
        }}

        /* Search */
        .search-box {{
            background: #fafafa;
            border: 1px solid #e5e7eb;
            padding: 15px;
            border-radius: 10px;
        }}

        .search-toggle {{
            display: flex;
            gap: 10px;
            margin: 10px 0;
            align-items: center;
        }}

        .search-toggle-btn {{
            padding: 6px 12px;
            border: none;
            border-radius: 15px;
            background: white;
            border: 1px solid #e5e7eb;
            color: #0a0a0a;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }}

        .search-toggle-btn.active {{
            background: #3b82f6;
            border-color: #3b82f6;
            font-weight: bold;
        }}

        .search-toggle-btn:hover {{
            background: #e5e7eb;
        }}

        .search-input {{
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 10px;
        }}

        .search-info {{
            font-size: 0.85em;
            margin: 10px 0;
            min-height: 20px;
        }}

        .search-nav {{
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }}

        .search-nav button {{
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 5px;
            background: white;
            border: 1px solid #e5e7eb;
            color: #0a0a0a;
            cursor: pointer;
            font-size: 12px;
        }}

        .search-nav button:hover {{
            background: #e5e7eb;
        }}

        .search-nav button:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}

        /* Filters */
        .filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .filter-btn {{
            padding: 8px 15px;
            background: white;
            border: 1px solid #e5e7eb;
            border: none;
            border-radius: 20px;
            color: #0a0a0a;
            cursor: pointer;
            transition: background 0.3s;
        }}

        .filter-btn:hover {{
            background: #e5e7eb;
        }}

        .filter-btn.active {{
            background: #3b82f6;
            border-color: #3b82f6;
            font-weight: bold;
        }}

        /* Main content */
        .main-content {{
            background: white;
            overflow-y: auto;
            position: relative;
        }}

        .messages {{
            padding: 20px;
        }}

        /* Date separator */
        .date-separator {{
            text-align: center;
            margin: 30px 0;
            position: relative;
        }}

        .date-separator::before {{
            content: '';
            position: absolute;
            left: 0;
            right: 0;
            top: 50%;
            height: 1px;
            background: #e4e6eb;
        }}

        .date-separator span {{
            background: white;
            padding: 5px 15px;
            position: relative;
            color: #65676b;
            font-size: 13px;
        }}

        /* Message */
        .message {{
            margin: 15px 0;
            display: flex;
            align-items: flex-start;
        }}

        .message.hidden {{
            display: none;
        }}

        .avatar {{
            width: 36px;
            height: 36px;
            border-radius: 50%;
            color: #0a0a0a;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            margin-right: 10px;
            flex-shrink: 0;
        }}

        /* Different colors for different people */
        .message-sender-0 .avatar {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .message-sender-1 .avatar {{
            background: #fce7f3;
            color: #9f1239;
        }}

        .message-sender-2 .avatar {{
            background: #dcfce7;
            color: #166534;
        }}

        .message-sender-3 .avatar {{
            background: #fed7aa;
            color: #9a3412;
        }}

        .message-content {{
            flex: 1;
            max-width: 70%;
        }}

        .message-header {{
            margin-bottom: 5px;
        }}

        .sender-name {{
            font-weight: 600;
            font-size: 13px;
            color: #050505;
            display: inline-block;
            margin-right: 10px;
        }}

        .message-time {{
            color: #65676b;
            font-size: 12px;
        }}

        .message-text {{
            padding: 10px 15px;
            border-radius: 18px;
            display: inline-block;
            word-wrap: break-word;
            max-width: 100%;
        }}

        /* Different background colors for messages */
        .message-sender-0 .message-text {{
            background: #e3f2fd;
            color: #000;
        }}

        .message-sender-1 .message-text {{
            background: #fce4ec;
            color: #000;
        }}

        .message-sender-2 .message-text {{
            background: #e8f5e9;
            color: #000;
        }}

        .message-sender-3 .message-text {{
            background: #fff3e0;
            color: #000;
        }}

        .message-text a {{
            color: #216FDB;
            text-decoration: none;
        }}

        .message-text a:hover {{
            text-decoration: underline;
        }}

        /* Photos */
        .message-photos {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 10px;
        }}

        .message-photo {{
            max-width: 250px;
            max-height: 250px;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.2s;
            object-fit: cover;
        }}

        .message-photo:hover {{
            transform: scale(1.02);
        }}

        /* Videos */
        .message-video {{
            max-width: 400px;
            border-radius: 10px;
            margin-top: 10px;
        }}

        /* Reactions */
        .reactions {{
            display: flex;
            gap: 5px;
            margin-top: 5px;
            flex-wrap: wrap;
        }}

        .reaction {{
            background: white;
            border: 1px solid #e4e6eb;
            border-radius: 12px;
            padding: 2px 8px;
            font-size: 12px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            color: #65676b;
        }}

        /* Search highlight */
        .highlight {{
            background: #ffeb3b;
            padding: 2px;
            border-radius: 2px;
            color: #000;
        }}

        .highlight.current {{
            background: #ff9800;
            color: #0a0a0a;
        }}

        /* Summarization */
        .summarization-box {{
            background: #fafafa;
            border: 1px solid #e5e7eb;
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }}

        .summarization-title {{
            font-size: 0.9em;
            font-weight: bold;
            margin-bottom: 10px;
            opacity: 0.9;
        }}

        .prompt-buttons {{
            display: flex;
            flex-direction: column;
            gap: 8px;
        }}

        .prompt-btn {{
            padding: 10px;
            background: white;
            border: 1px solid #e5e7eb;
            border: none;
            border-radius: 8px;
            color: #0a0a0a;
            cursor: pointer;
            text-align: left;
            font-size: 13px;
            transition: background 0.2s;
        }}

        .prompt-btn:hover {{
            background: #e5e7eb;
        }}

        .prompt-btn .prompt-title {{
            font-weight: bold;
            margin-bottom: 3px;
        }}

        .prompt-btn .prompt-desc {{
            font-size: 11px;
            opacity: 0.8;
        }}

        .date-filter {{
            margin-top: 10px;
            display: flex;
            gap: 5px;
        }}

        .prompt-section {{
            margin-bottom: 20px;
        }}

        .prompt-section h4 {{
            font-size: 14px;
            margin-bottom: 10px;
            opacity: 0.9;
        }}

        /* Summary Modal */
        .summary-modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.8);
        }}

        .summary-modal.active {{
            display: block;
        }}

        .summary-content {{
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border-radius: 10px;
            width: 80%;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
        }}

        .summary-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ddd;
        }}

        .summary-close {{
            color: #aaa;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}

        .summary-close:hover {{
            color: black;
        }}

        .summary-body {{
            line-height: 1.6;
            color: #333;
        }}

        .summary-body h3 {{
            margin-top: 15px;
            color: #444;
        }}

        .summary-body ul {{
            margin-left: 20px;
        }}

        .date-filter input {{
            flex: 1;
            padding: 5px;
            border: none;
            border-radius: 5px;
            font-size: 12px;
        }}

        /* Summary Modal */
        .summary-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }}

        .summary-modal.active {{
            display: flex;
        }}

        .summary-content {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            position: relative;
        }}

        .summary-close {{
            position: absolute;
            top: 15px;
            right: 15px;
            font-size: 24px;
            cursor: pointer;
            color: #666;
        }}

        .summary-title {{
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
        }}

        .summary-text {{
            line-height: 1.6;
            color: #444;
            white-space: pre-wrap;
        }}

        .summary-loading {{
            text-align: center;
            padding: 40px;
        }}

        .loading-spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        /* Hourly chart */
        .hour-chart {{
            height: 100px;
            display: flex;
            align-items: flex-end;
            gap: 2px;
            margin: 20px 0;
        }}

        .hour-bar {{
            flex: 1;
            background: #3b82f6;
            border-radius: 2px 2px 0 0;
            min-height: 2px;
            position: relative;
        }}

        .hour-bar:hover::after {{
            content: attr(data-tooltip);
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: #0a0a0a;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            white-space: nowrap;
        }}

        /* Photo modal */
        .modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.9);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }}

        .modal.active {{
            display: flex;
        }}

        .modal-content {{
            max-width: 90%;
            max-height: 90%;
        }}

        .modal-close {{
            position: absolute;
            top: 20px;
            right: 40px;
            color: #0a0a0a;
            font-size: 40px;
            cursor: pointer;
        }}

        /* Progress modal */
        .progress-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            z-index: 2000;
            align-items: center;
            justify-content: center;
        }}

        .progress-modal.active {{
            display: flex;
        }}

        .progress-content {{
            background: white;
            padding: 40px;
            border-radius: 15px;
            text-align: center;
            max-width: 500px;
        }}

        .progress-title {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #333;
        }}

        .progress-bar-container {{
            width: 100%;
            height: 30px;
            background: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}

        .progress-bar {{
            height: 100%;
            background: #3b82f6;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #0a0a0a;
            font-weight: bold;
        }}

        .progress-message {{
            color: #666;
            margin-top: 20px;
            font-size: 14px;
        }}

        .progress-spinner {{
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }}

        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}

        /* Back to top */
        .back-to-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #3b82f6;
            color: #0a0a0a;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 100;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .back-to-top.visible {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Sidebar -->
        <div class="sidebar">
            <button class="back-button" onclick="window.location.href='/'">← Back to Conversations</button>

            <h1>Messenger Export</h1>
            <div class="participants">{participants}</div>

            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number">{total_messages:,}</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_photos}</div>
                    <div class="stat-label">Photos</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_videos}</div>
                    <div class="stat-label">Videos</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">{total_links}</div>
                    <div class="stat-label">Links</div>
                </div>
            </div>

            <div class="date-navigation">
                <input type="date" class="date-picker" id="date-picker"
                       min="{first_date}" max="{last_date}" value="{last_date}">
                <div class="quick-dates">
                    <button class="quick-date-btn" onclick="jumpToRelativeDate(30)">Last Month</button>
                    <button class="quick-date-btn" onclick="jumpToRelativeDate(90)">3 Months</button>
                    <button class="quick-date-btn" onclick="jumpToRelativeDate(180)">6 Months</button>
                    <button class="quick-date-btn" onclick="jumpToRelativeDate(365)">1 Year</button>
                </div>
            </div>

            <div class="search-box">
                <input type="text" class="search-input" id="search" placeholder="Search messages...">
                {semantic_toggle}
                <div class="search-info" id="search-info"></div>
                <div class="search-nav" id="search-nav" style="display: none;">
                    <button onclick="navigateSearch('prev')" id="prev-btn">← Previous</button>
                    <button onclick="navigateSearch('next')" id="next-btn">Next →</button>
                </div>
            </div>

            <div class="filters">
                <button class="filter-btn active" data-filter="all">All</button>
                <button class="filter-btn" data-filter="photos">Photos</button>
                <button class="filter-btn" data-filter="videos">Videos</button>
                <button class="filter-btn" data-filter="links">Links</button>
            </div>

            {summarization_section}

            <div class="hour-chart">
                {hour_chart}
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <div class="messages" id="messages">
                {messages_html}
            </div>
        </div>
    </div>

    <!-- Photo Modal -->
    <div class="modal" id="photo-modal">
        <span class="modal-close" onclick="closeModal()">&times;</span>
        <img class="modal-content" id="modal-image">
    </div>

    <!-- Progress Modal -->
    <div class="progress-modal" id="progress-modal">
        <div class="progress-content">
            <div class="progress-title">🧠 Generating Semantic Search Index</div>
            <div class="progress-bar-container">
                <div class="progress-bar" id="progress-bar"></div>
            </div>
            <div class="progress-message" id="progress-message">
                Preparing embeddings for semantic search...<br>
                This is a one-time process that may take a few minutes.
            </div>
            <div class="progress-spinner"></div>
        </div>
    </div>

    <!-- Summary Modal -->
    <div class="summary-modal" id="summary-modal">
        <div class="summary-content">
            <div class="summary-header">
                <h2 id="summary-title">AI Analysis</h2>
                <span class="summary-close" onclick="closeSummaryModal()">&times;</span>
            </div>
            <div class="summary-body" id="summary-text">
                <div class="summary-loading" id="summary-loading">
                    <div class="loading-spinner"></div>
                    <div>Generating AI analysis...</div>
                </div>
                <!-- Summary content will be inserted here -->
            </div>
        </div>
    </div>

    <!-- Back to top button -->
    <div class="back-to-top" id="back-to-top" onclick="scrollToTop()">↑</div>

    <script>
        // Search functionality with navigation
        let searchResults = [];
        let currentSearchIndex = -1;
        let searchMode = 'text';  // 'text' or 'semantic'
        let semanticSearchEnabled = {semantic_enabled_js};
        let embeddingsReady = false;

        const searchInput = document.getElementById('search');
        const searchInfo = document.getElementById('search-info');
        const searchNav = document.getElementById('search-nav');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');

        // Check if embeddings are being generated
        async function checkEmbeddingStatus() {{
            if (!semanticSearchEnabled) return;

            try {{
                const response = await fetch('/embedding-status?conv_id={conversation_id}');
                const data = await response.json();

                console.log('Embedding status:', data);  // Debug log

                if (data.status === 'generating') {{
                    showProgressModal();
                    updateProgress(data.progress || 0, data.message || 'Processing...');
                    // Check again in 2 seconds
                    setTimeout(checkEmbeddingStatus, 2000);
                }} else if (data.status === 'ready') {{
                    embeddingsReady = true;
                    hideProgressModal();
                }} else if (data.status === 'not_started') {{
                    // Will start when user first clicks semantic search
                    embeddingsReady = false;
                    // Check again in a bit in case generation starts
                    setTimeout(checkEmbeddingStatus, 5000);
                }}
            }} catch (error) {{
                console.error('Error checking embedding status:', error);
            }}
        }}

        function showProgressModal() {{
            document.getElementById('progress-modal').classList.add('active');
        }}

        function hideProgressModal() {{
            document.getElementById('progress-modal').classList.remove('active');
        }}

        function updateProgress(percentage, message) {{
            const progressBar = document.getElementById('progress-bar');
            const progressMessage = document.getElementById('progress-message');

            progressBar.style.width = percentage + '%';
            progressBar.textContent = percentage > 0 ? Math.round(percentage) + '%' : '';

            if (message) {{
                progressMessage.innerHTML = message + '<br><small>This is a one-time process. Future searches will be instant.</small>';
            }}
        }}

        // Check embedding status on page load
        window.addEventListener('load', () => {{
            // Start checking embedding status immediately
            checkEmbeddingStatus();

            // For large conversations, check more frequently initially
            const messageCount = document.querySelectorAll('.message').length;
            if (messageCount >= {MIN_MESSAGES_FOR_PROGRESS}) {{
                console.log(`Large conversation detected (${{messageCount}} messages) - monitoring embedding generation`);
                // Check every second for the first 10 seconds
                for (let i = 1; i <= 10; i++) {{
                    setTimeout(checkEmbeddingStatus, i * 1000);
                }}
            }}
        }});

        // Toggle search mode
        function toggleSearchMode(mode) {{
            searchMode = mode;
            document.querySelectorAll('.search-toggle-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            document.getElementById(`search-${{mode}}`).classList.add('active');

            // Clear and re-run search
            if (searchInput.value) {{
                searchInput.dispatchEvent(new Event('input'));
            }}
        }}

        // Perform semantic search
        async function performSemanticSearch(query) {{
            try {{
                // First check if embeddings are being generated
                if (!embeddingsReady) {{
                    checkEmbeddingStatus();
                }}

                const response = await fetch(`/semantic-search?q=${{encodeURIComponent(query)}}&conv_id={conversation_id}`);
                const data = await response.json();

                if (data.results && data.results.length > 0) {{
                    highlightSemanticResults(data.results);
                }} else {{
                    searchInfo.textContent = 'No semantic matches found';
                    searchNav.style.display = 'none';
                }}
            }} catch (error) {{
                console.error('Semantic search error:', error);
                searchInfo.textContent = 'Semantic search error';
            }}
        }}

        // Highlight semantic search results
        function highlightSemanticResults(results) {{
            // Clear all highlights first
            document.querySelectorAll('.message').forEach(msg => {{
                msg.classList.remove('semantic-match');
                msg.style.opacity = '0.3';
            }});

            searchResults = [];

            results.forEach((result, index) => {{
                const messages = document.querySelectorAll('.message');
                messages.forEach(msg => {{
                    if (msg.dataset.timestamp === String(result.timestamp_ms)) {{
                        msg.classList.add('semantic-match');
                        msg.style.opacity = '1';
                        searchResults.push(msg);

                        // Add score indicator
                        const scoreEl = msg.querySelector('.semantic-score');
                        if (scoreEl) {{
                            scoreEl.remove();
                        }}
                        const score = document.createElement('span');
                        score.className = 'semantic-score';
                        score.style.cssText = 'background: #4CAF50; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-left: 10px;';
                        score.textContent = `${{(result.score * 100).toFixed(0)}}% match`;
                        msg.querySelector('.message-header').appendChild(score);
                    }}
                }});
            }});

            if (searchResults.length > 0) {{
                currentSearchIndex = 0;
                searchInfo.textContent = `Found ${{searchResults.length}} semantic matches`;
                searchNav.style.display = 'flex';
                updateSearchDisplay();
            }}
        }}

        searchInput.addEventListener('input', async function() {{
            const searchTerm = this.value.toLowerCase().trim();

            // Clear previous highlights and results
            document.querySelectorAll('.highlight').forEach(el => {{
                const parent = el.parentNode;
                parent.replaceChild(document.createTextNode(el.textContent), el);
                parent.normalize();
            }});

            // Clear semantic highlights
            document.querySelectorAll('.message').forEach(msg => {{
                msg.classList.remove('semantic-match');
                msg.style.opacity = '1';
            }});
            document.querySelectorAll('.semantic-score').forEach(el => el.remove());

            searchResults = [];
            currentSearchIndex = -1;

            if (!searchTerm) {{
                searchInfo.textContent = '';
                searchNav.style.display = 'none';
                return;
            }}

            // Use semantic search if enabled and selected
            if (semanticSearchEnabled && searchMode === 'semantic') {{
                searchInfo.textContent = 'Searching semantically...';
                await performSemanticSearch(searchTerm);
                return;
            }}

            // Search and highlight
            document.querySelectorAll('.message').forEach(msg => {{
                const messageText = msg.querySelector('.message-text');
                if (!messageText) return;

                const walker = document.createTreeWalker(
                    messageText,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );

                const textNodes = [];
                let node;
                while (node = walker.nextNode()) {{
                    textNodes.push(node);
                }}

                textNodes.forEach(textNode => {{
                    const text = textNode.textContent;
                    const lowerText = text.toLowerCase();

                    if (lowerText.includes(searchTerm)) {{
                        const regex = new RegExp(`(${{searchTerm}})`, 'gi');
                        const parts = text.split(regex);

                        if (parts.length > 1) {{
                            const fragment = document.createDocumentFragment();
                            parts.forEach(part => {{
                                if (part.toLowerCase() === searchTerm) {{
                                    const highlight = document.createElement('span');
                                    highlight.className = 'highlight';
                                    highlight.textContent = part;
                                    fragment.appendChild(highlight);
                                    searchResults.push(highlight);
                                }} else if (part) {{
                                    fragment.appendChild(document.createTextNode(part));
                                }}
                            }});
                            textNode.parentNode.replaceChild(fragment, textNode);
                        }}
                    }}
                }});
            }});

            // Update search info
            if (searchResults.length > 0) {{
                currentSearchIndex = 0;
                updateSearchDisplay();
                searchNav.style.display = 'flex';
            }} else {{
                searchInfo.textContent = 'No results found';
                searchNav.style.display = 'none';
            }}
        }});

        function updateSearchDisplay() {{
            if (searchResults.length === 0) return;

            // Update info
            searchInfo.textContent = `Result ${{currentSearchIndex + 1}} of ${{searchResults.length}}`;

            // Update highlight classes
            searchResults.forEach((el, index) => {{
                if (index === currentSearchIndex) {{
                    el.classList.add('current');
                    el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                }} else {{
                    el.classList.remove('current');
                }}
            }});

            // Update buttons
            prevBtn.disabled = currentSearchIndex === 0;
            nextBtn.disabled = currentSearchIndex === searchResults.length - 1;
        }}

        function navigateSearch(direction) {{
            if (searchResults.length === 0) return;

            if (direction === 'prev' && currentSearchIndex > 0) {{
                currentSearchIndex--;
            }} else if (direction === 'next' && currentSearchIndex < searchResults.length - 1) {{
                currentSearchIndex++;
            }}

            updateSearchDisplay();
        }}

        // Date navigation
        const datePicker = document.getElementById('date-picker');

        datePicker.addEventListener('change', function() {{
            const selectedDate = new Date(this.value);
            const messages = document.querySelectorAll('.message');

            let targetMessage = null;
            for (const msg of messages) {{
                const msgTime = parseInt(msg.dataset.timestamp);
                const msgDate = new Date(msgTime);

                if (msgDate >= selectedDate) {{
                    targetMessage = msg;
                    break;
                }}
            }}

            if (targetMessage) {{
                targetMessage.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }}
        }});

        function jumpToRelativeDate(daysAgo) {{
            const targetDate = new Date();
            targetDate.setDate(targetDate.getDate() - daysAgo);

            datePicker.value = targetDate.toISOString().split('T')[0];
            datePicker.dispatchEvent(new Event('change'));
        }}

        // Filter functionality
        const filterButtons = document.querySelectorAll('.filter-btn');

        filterButtons.forEach(btn => {{
            btn.addEventListener('click', function() {{
                // Update active button
                filterButtons.forEach(b => b.classList.remove('active'));
                this.classList.add('active');

                const filter = this.dataset.filter;
                const allMessages = document.querySelectorAll('.message');

                // Show/hide messages based on filter
                allMessages.forEach(msg => {{
                    if (filter === 'all') {{
                        msg.classList.remove('hidden');
                    }} else if (filter === 'photos') {{
                        if (msg.querySelector('.message-photos')) {{
                            msg.classList.remove('hidden');
                        }} else {{
                            msg.classList.add('hidden');
                        }}
                    }} else if (filter === 'videos') {{
                        if (msg.querySelector('.message-video')) {{
                            msg.classList.remove('hidden');
                        }} else {{
                            msg.classList.add('hidden');
                        }}
                    }} else if (filter === 'links') {{
                        if (msg.querySelector('.message-text a')) {{
                            msg.classList.remove('hidden');
                        }} else {{
                            msg.classList.add('hidden');
                        }}
                    }}
                }});

                // Also show/hide date separators appropriately
                document.querySelectorAll('.date-separator').forEach(sep => {{
                    const nextMsg = sep.nextElementSibling;
                    if (!nextMsg || !nextMsg.classList.contains('message')) {{
                        sep.style.display = 'block';
                        return;
                    }}

                    let hasVisibleMessage = false;
                    let sibling = nextMsg;
                    while (sibling && !sibling.classList.contains('date-separator')) {{
                        if (sibling.classList.contains('message') && !sibling.classList.contains('hidden')) {{
                            hasVisibleMessage = true;
                            break;
                        }}
                        sibling = sibling.nextElementSibling;
                    }}
                    sep.style.display = hasVisibleMessage ? 'block' : 'none';
                }});
            }});
        }});

        // Photo modal
        function openModal(imageSrc) {{
            const modal = document.getElementById('photo-modal');
            const modalImg = document.getElementById('modal-image');
            modal.classList.add('active');
            modalImg.src = imageSrc;
        }}

        function closeModal() {{
            const modal = document.getElementById('photo-modal');
            modal.classList.remove('active');
        }}

        // Close modal on background click
        document.getElementById('photo-modal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeModal();
            }}
        }});

        // Back to top button
        const backToTop = document.getElementById('back-to-top');
        const mainContent = document.querySelector('.main-content');

        mainContent.addEventListener('scroll', function() {{
            if (this.scrollTop > 500) {{
                backToTop.classList.add('visible');
            }} else {{
                backToTop.classList.remove('visible');
            }}
        }});

        function scrollToTop() {{
            mainContent.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }}

        // Summarization functionality
        const conversationId = '{conversation_id}';
        const llmAvailable = {llm_available_js};

        async function generateSummary(promptType, dateFilter = null, customPrompt = null) {{
            if (!llmAvailable) {{
                alert('Summarization not available. Please install Ollama and llama3.2:3b');
                return;
            }}

            // Show modal with loading state
            const modal = document.getElementById('summary-modal');
            const titleEl = document.getElementById('summary-title');
            const textEl = document.getElementById('summary-text');

            // Set title based on prompt type
            const titles = {{
                'overview': '📝 Conversation Overview',
                'topics': '🏷️ Main Topics',
                'timeline': '📅 Timeline of Events',
                'memory': '💭 Important Information',
                'date': `📅 Summary for ${{dateFilter}}`
            }};

            titleEl.textContent = titles[dateFilter ? 'date' : promptType] || 'Summary';
            textEl.innerHTML = '<div class="summary-loading"><div class="loading-spinner"></div><div>Generating summary...</div></div>';
            modal.classList.add('active');

            try {{
                // Build query parameters
                const params = new URLSearchParams({{
                    conv_id: conversationId,
                    type: promptType
                }});

                if (dateFilter) {{
                    params.append('date', dateFilter);
                }}

                if (customPrompt) {{
                    params.append('prompt', customPrompt);
                }}

                // Fetch summary from server
                const response = await fetch(`/summarize?${{params}}`);
                const data = await response.json();

                // Display summary
                textEl.textContent = data.summary;

            }} catch (error) {{
                console.error('Error generating summary:', error);
                textEl.textContent = 'Error generating summary. Please try again.';
            }}
        }}

        function closeSummaryModal() {{
            document.getElementById('summary-modal').classList.remove('active');
        }}

        // Helper functions for ready-made prompts
        function generateSummaryWithDate(promptPrefix) {{
            // Show date picker or use current month
            const date = prompt('Enter month (YYYY-MM format, e.g., 2023-03):');
            if (date && /^\\d{{4}}-\\d{{2}}$/.test(date)) {{
                generateSummary('overview', date, `${{promptPrefix}} ${{date}}`);
            }} else if (date) {{
                alert('Please enter date in YYYY-MM format (e.g., 2023-03)');
            }}
        }}

        function generateSummaryLastMonth() {{
            const now = new Date();
            const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            const dateFilter = `${{lastMonth.getFullYear()}}-${{String(lastMonth.getMonth() + 1).padStart(2, '0')}}`;
            generateSummary('overview', dateFilter, `What happened in ${{dateFilter}}`);
        }}

        function generateSummaryLastYear() {{
            const now = new Date();
            const lastYear = now.getFullYear() - 1;
            const dateFilter = String(lastYear);
            generateSummary('overview', dateFilter, `Year ${{lastYear}} in review`);
        }}

        function showCustomPromptInput() {{
            document.getElementById('customPromptInput').style.display = 'block';
            document.getElementById('customPromptText').focus();
        }}

        function hideCustomPromptInput() {{
            document.getElementById('customPromptInput').style.display = 'none';
            document.getElementById('customPromptText').value = '';
        }}

        function submitCustomPrompt() {{
            const prompt = document.getElementById('customPromptText').value.trim();
            if (prompt) {{
                generateSummary('custom', null, prompt);
                hideCustomPromptInput();
            }}
        }}

        // Close modal on background click
        document.getElementById('summary-modal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeSummaryModal();
            }}
        }});

        // Get date filter for summarization
        function getSummaryDateFilter() {{
            const input = document.getElementById('summary-date-filter');
            return input ? input.value : null;
        }}
    </script>
</body>
</html>'''

    # Create semantic search toggle and summarization section if available
    llm_available_js = 'false'  # Default
    if SEMANTIC_SEARCH_AVAILABLE and conversation_id:
        semantic_toggle = '''
                <div class="search-toggle">
                    <button id="search-text" class="search-toggle-btn active" onclick="toggleSearchMode('text')">
                        🔤 Text Search
                    </button>
                    <button id="search-semantic" class="search-toggle-btn" onclick="toggleSearchMode('semantic')">
                        🧠 Semantic Search
                    </button>
                    <span style="font-size: 11px; opacity: 0.8; margin-left: 10px;">
                        (Czech & English supported)
                    </span>
                </div>'''
        semantic_enabled_js = 'true'

        # Check if LLM is available for summarization
        if semantic_engine and semantic_engine.llm_model:
            llm_available_js = 'true'

        # Add summarization section with ready-made prompts
        summarization_section = '''
        <div class="summarization-box">
            <h3>🤖 AI Conversation Analysis</h3>
            <p style="margin-bottom: 15px; color: #666;">Click a button to generate AI-powered insights about this conversation:</p>

            <div class="prompt-section">
                <h4>📊 Overview & Topics</h4>
                <div class="prompt-buttons">
                    <button class="prompt-btn" onclick="generateSummary('overview', null, 'Summarize this conversation')">
                        📝 Summarize this conversation
                    </button>
                    <button class="prompt-btn" onclick="generateSummary('topics', null, 'What were the main topics?')">
                        🏷️ What were the main topics?
                    </button>
                    <button class="prompt-btn" onclick="generateSummary('timeline', null, 'Create a timeline of key events')">
                        📅 Timeline of key events
                    </button>
                </div>
            </div>

            <div class="prompt-section">
                <h4>📅 Time-based Analysis</h4>
                <div class="prompt-buttons">
                    <button class="prompt-btn" onclick="generateSummaryWithDate('What did we discuss in')">
                        🗓️ What did we discuss in... (select month)
                    </button>
                    <button class="prompt-btn" onclick="generateSummaryLastMonth()">
                        📆 What happened last month?
                    </button>
                    <button class="prompt-btn" onclick="generateSummaryLastYear()">
                        📅 Year in review
                    </button>
                </div>
            </div>

            <div class="prompt-section">
                <h4>🔍 Memory Search</h4>
                <div class="prompt-buttons">
                    <button class="prompt-btn" onclick="generateSummary('memory', null, 'Find all plans and decisions')">
                        📋 Find all plans and decisions
                    </button>
                    <button class="prompt-btn" onclick="showCustomPromptInput()">
                        ✏️ Ask a custom question...
                    </button>
                </div>
            </div>

            <div id="customPromptInput" style="display: none; margin-top: 15px;">
                <input type="text" id="customPromptText" placeholder="e.g., When did we plan that trip to Prague?"
                       style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 10px;"
                       onkeypress="if(event.key === 'Enter') submitCustomPrompt()">
                <button onclick="submitCustomPrompt()" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    🔍 Ask Question
                </button>
                <button onclick="hideCustomPromptInput()" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 5px;">
                    Cancel
                </button>
            </div>

            <div id="summaryLoading" style="display: none; margin-top: 20px; text-align: center;">
                <div class="spinner"></div>
                <p style="margin-top: 10px; color: #666;">Generating AI analysis...</p>
            </div>
        </div>
        '''
    else:
        semantic_toggle = ''
        semantic_enabled_js = 'false'
        summarization_section = ''
        llm_available_js = 'false'

    # Format the template
    html_content = html_template.format(
        participants=' & '.join(participants),
        total_messages=stats['total'],
        total_photos=stats['photos'],
        total_videos=stats['videos'],
        total_links=stats['links'],
        first_date=stats['first_date'],
        last_date=stats['last_date'],
        hour_chart=hour_chart,
        messages_html=messages_html,
        semantic_toggle=semantic_toggle,
        semantic_enabled_js=semantic_enabled_js,
        conversation_id=conversation_id or 0,
        MIN_MESSAGES_FOR_PROGRESS=MIN_MESSAGES_FOR_PROGRESS,
        summarization_section=summarization_section,
        llm_available_js=llm_available_js
    )

    return html_content

class MessengerHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == '/':
            # Serve conversation list
            conversations = load_conversation_index()
            html_content = generate_index_html(conversations)

            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        elif parsed_path.path == '/conversation':
            # Parse conversation ID
            query_params = parse_qs(parsed_path.query)
            conv_id = query_params.get('id', [None])[0]

            if conv_id is None:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing conversation ID")
                return

            try:
                conv_id = int(conv_id)
                conversations = load_conversation_index()

                if conv_id >= len(conversations):
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"Conversation not found")
                    return

                conv = conversations[conv_id]
                print(f"Loading conversation: {conv['participants'][:2]}")

                # Load and process conversation
                messages, participants = load_and_process_conversation(conv['path'])

                # Handle embeddings for semantic search
                if SEMANTIC_SEARCH_AVAILABLE:
                    # Store conversation data for later use
                    self.server.conversation_data = {
                        'messages': messages,
                        'embeddings': None,  # Will be loaded/generated on demand
                        'conv_id': str(conv_id)
                    }

                    # Check if embeddings exist or need generation
                    if check_embeddings_exist(str(conv_id)):
                        # Embeddings exist, they'll be loaded when needed
                        print(f"✅ Embeddings already cached for conversation {conv_id}")
                    else:
                        # Check if conversation is large enough to show progress
                        if len(messages) >= MIN_MESSAGES_FOR_PROGRESS:
                            # Start generation in background for large conversations
                            print(f"📊 Large conversation ({len(messages)} messages) - starting background embedding generation")
                            generate_embeddings_async(messages, str(conv_id))
                        else:
                            # For small conversations, generate immediately without showing progress
                            print(f"📝 Small conversation ({len(messages)} messages) - generating embeddings immediately")
                            generate_embeddings_async(messages, str(conv_id))

                html_content = generate_conversation_html(messages, participants, str(conv_id))

                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html_content.encode('utf-8'))

            except Exception as e:
                print(f"Error loading conversation: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error: {str(e)}".encode('utf-8'))

        elif parsed_path.path == '/semantic-search':
            # Handle semantic search requests
            query_params = parse_qs(parsed_path.query)
            query = query_params.get('q', [None])[0]
            conv_id = query_params.get('conv_id', [None])[0]

            if not query or not SEMANTIC_SEARCH_AVAILABLE:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid request or semantic search not available'}).encode())
                return

            # Get conversation data
            if hasattr(self.server, 'conversation_data') and self.server.conversation_data.get('conv_id') == conv_id:
                messages = self.server.conversation_data['messages']
                embeddings = self.server.conversation_data.get('embeddings')

                # Load embeddings if not already loaded
                if embeddings is None:
                    print(f"Loading embeddings for semantic search on conversation {conv_id}")
                    embeddings = get_or_generate_embeddings(messages, conv_id)
                    self.server.conversation_data['embeddings'] = embeddings

                # Perform semantic search
                results = perform_semantic_search(query, messages, embeddings, top_k=20)

                # Format results for JSON
                json_results = []
                for msg, score in results:
                    json_results.append({
                        'timestamp_ms': msg['timestamp_ms'],
                        'sender': msg['sender'],
                        'content': msg['content'][:200],  # Truncate for preview
                        'score': float(score)
                    })

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'results': json_results}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Conversation data not loaded'}).encode())

        elif parsed_path.path == '/embedding-status':
            # Return current embedding generation progress
            query_params = parse_qs(parsed_path.query)
            conv_id = query_params.get('conv_id', [None])[0]

            if SEMANTIC_SEARCH_AVAILABLE and semantic_engine and conv_id:
                # Check if embeddings are cached
                if check_embeddings_exist(conv_id):
                    status = {'status': 'ready', 'progress': 100, 'message': 'Embeddings loaded from cache'}
                else:
                    # Check generation progress
                    status = semantic_engine.generation_progress.get(conv_id, {'status': 'not_started'})

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(status).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'not_available'}).encode())

        elif parsed_path.path == '/summarize':
            # Handle conversation summarization requests
            query_params = parse_qs(parsed_path.query)
            conv_id = query_params.get('conv_id', [None])[0]
            prompt_type = query_params.get('type', ['overview'])[0]
            date_filter = query_params.get('date', [None])[0]
            custom_prompt = query_params.get('prompt', [None])[0]

            if not SEMANTIC_SEARCH_AVAILABLE or not semantic_engine:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'summary': '⚠️ Summarization not available. Please install Ollama and llama3.2.'
                }).encode())
                return

            # Get conversation data
            if hasattr(self.server, 'conversation_data') and self.server.conversation_data.get('conv_id') == conv_id:
                messages = self.server.conversation_data['messages']

                # Generate summary
                print(f"🤖 Generating {prompt_type} summary for conversation {conv_id}")
                if date_filter:
                    print(f"   Filtering for date: {date_filter}")

                summary = semantic_engine.summarize_messages(
                    messages,
                    prompt_type=prompt_type,
                    date_filter=date_filter,
                    custom_prompt=custom_prompt
                )

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'summary': summary}).encode())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'summary': 'Conversation not loaded'}).encode())

        elif parsed_path.path == '/rebuild':
            # Force rebuild index
            conversations = build_conversation_index()
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()

        elif parsed_path.path.startswith('/fb_export/') or parsed_path.path.startswith('/your_facebook_activity/'):
            # Serve static files (photos, videos)
            if parsed_path.path.startswith('/your_facebook_activity/'):
                file_path = 'fb_export' + parsed_path.path
            else:
                file_path = parsed_path.path[1:]  # Remove leading /

            if os.path.exists(file_path):
                # Determine content type
                if file_path.endswith(('.jpg', '.jpeg')):
                    content_type = 'image/jpeg'
                elif file_path.endswith('.png'):
                    content_type = 'image/png'
                elif file_path.endswith('.gif'):
                    content_type = 'image/gif'
                elif file_path.endswith('.mp4'):
                    content_type = 'video/mp4'
                else:
                    content_type = 'application/octet-stream'

                # Serve the file
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    print(f"Error serving file {file_path}: {e}")
                    self.send_response(500)
                    self.end_headers()
            else:
                print(f"File not found: {file_path}")
                self.send_response(404)
                self.end_headers()
        else:
            # Try to serve as static file
            super().do_GET()

def main():
    PORT = 8000

    print(f"🚀 Starting Messenger Server on port {PORT}")
    print(f"📱 Open http://localhost:{PORT} in your browser")
    print(f"🔄 To rebuild index: http://localhost:{PORT}/rebuild")

    with socketserver.TCPServer(("", PORT), MessengerHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

if __name__ == '__main__':
    main()