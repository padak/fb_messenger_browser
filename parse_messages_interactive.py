#!/usr/bin/env python3
import json
import os
from datetime import datetime
from pathlib import Path
import html
import re
import sys

def fix_czech_chars(text):
    """Fix Czech character encoding issues"""
    if not text:
        return text

    # First, try to fix mojibake by re-encoding
    try:
        if isinstance(text, str):
            # Detect if text has mojibake patterns
            if 'Ã' in text or 'Ä' in text or 'Å' in text:
                # Try to fix by encoding to latin-1 and decoding as utf-8
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
            first_msg = messages[-1]  # Messages are in reverse chronological order
            last_msg = messages[0]
            first_date = datetime.fromtimestamp(first_msg.get('timestamp_ms', 0) / 1000).strftime('%Y-%m-%d')
            last_date = datetime.fromtimestamp(last_msg.get('timestamp_ms', 0) / 1000).strftime('%Y-%m-%d')
        else:
            first_date = 'N/A'
            last_date = 'N/A'

        return {
            'participants': participants,
            'message_count': message_count,
            'first_date': first_date,
            'last_date': last_date,
            'path': conv_path
        }
    except Exception as e:
        return None

def list_all_conversations():
    """List all conversations in the Facebook export"""
    base_path = Path('fb_export/your_facebook_activity/messages')
    conversations = []

    # Check all main folders
    folders_to_check = ['inbox', 'filtered_threads', 'archived_threads', 'message_requests', 'e2ee_cutover']

    for folder in folders_to_check:
        folder_path = base_path / folder
        if not folder_path.exists():
            continue

        # Find all conversation folders
        for conv_folder in folder_path.iterdir():
            if conv_folder.is_dir():
                info = get_conversation_info(conv_folder)
                if info:
                    info['category'] = folder
                    conversations.append(info)

    return conversations

def display_conversations(conversations):
    """Display conversations in a nice table format"""
    print("\n" + "="*100)
    print("FACEBOOK MESSENGER CONVERSATIONS")
    print("="*100)

    # Group by category
    categories = {}
    for conv in conversations:
        cat = conv['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(conv)

    idx = 1
    conv_index = {}

    for category, convs in categories.items():
        print(f"\n📁 {category.upper().replace('_', ' ')}")
        print("-"*100)

        for conv in sorted(convs, key=lambda x: x['message_count'], reverse=True):
            participants = ', '.join(conv['participants'][:2])
            if len(conv['participants']) > 2:
                participants += f" +{len(conv['participants'])-2}"

            print(f"{idx:3}. {participants[:50]:<50} | {conv['message_count']:>6} msgs | {conv['first_date']} to {conv['last_date']}")
            conv_index[idx] = conv
            idx += 1

    return conv_index

def load_messages(base_path):
    """Load all messages from Facebook export"""
    messages = []
    participants = set()

    json_path = Path(base_path) / 'message_1.json'

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

        # Check for links in content
        if processed_msg['content']:
            processed_msg['has_link'] = bool(re.search(r'https?://[^\s]+', processed_msg['content']))
        else:
            processed_msg['has_link'] = False

        messages.append(processed_msg)

    # Sort messages by timestamp (oldest first)
    messages.sort(key=lambda x: x['timestamp_ms'])

    return messages, list(participants)

def generate_stats(messages):
    """Generate statistics from messages"""
    stats = {
        'total': len(messages),
        'photos': sum(1 for m in messages if m['photos']),
        'videos': sum(1 for m in messages if m['videos']),
        'links': sum(1 for m in messages if m['has_link']),
        'hourly': [0] * 24
    }

    # Calculate hourly distribution
    for msg in messages:
        stats['hourly'][msg['hour']] += 1

    # Get date range
    if messages:
        stats['first_date'] = messages[0]['iso_date']
        stats['last_date'] = messages[-1]['iso_date']

    return stats

def escape_html_content(text):
    """Escape HTML but preserve line breaks"""
    if not text:
        return ''
    text = html.escape(text)
    # Convert URLs to links
    text = re.sub(
        r'(https?://[^\s]+)',
        r'<a href="\1" target="_blank">\1</a>',
        text
    )
    return text

def generate_html(messages, participants, stats, conv_name):
    """Generate HTML file with ALL messages"""

    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facebook Messenger Export - {participants}</title>
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

        /* Sidebar */
        .sidebar {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .sidebar h1 {{
            font-size: 1.5em;
            margin-bottom: 10px;
        }}

        .participants {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 20px;
        }}

        .stats {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
        }}

        .stat-item {{
            margin: 10px 0;
        }}

        .stat-number {{
            font-size: 2em;
            font-weight: bold;
        }}

        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}

        /* Date Navigation */
        .date-navigation {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
        }}

        .date-picker {{
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 10px;
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
            background: rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.2s;
        }}

        .quick-date-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}

        /* Search */
        .search-box {{
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
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
            background: rgba(255,255,255,0.2);
            color: white;
            cursor: pointer;
            font-size: 12px;
        }}

        .search-nav button:hover {{
            background: rgba(255,255,255,0.3);
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
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 20px;
            color: white;
            cursor: pointer;
            transition: background 0.3s;
        }}

        .filter-btn:hover {{
            background: rgba(255,255,255,0.3);
        }}

        .filter-btn.active {{
            background: rgba(255,255,255,0.4);
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
            color: white;
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
            background: linear-gradient(135deg, #0084ff, #44bec7);
        }}

        .message-sender-1 .avatar {{
            background: linear-gradient(135deg, #fa3c4c, #d696bb);
        }}

        .message-sender-2 .avatar {{
            background: linear-gradient(135deg, #00c851, #00ff87);
        }}

        .message-sender-3 .avatar {{
            background: linear-gradient(135deg, #ff6900, #fcb900);
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
            color: white;
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
            background: rgba(255,255,255,0.5);
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
            color: white;
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
            color: white;
            font-size: 40px;
            cursor: pointer;
        }}

        /* Back to top */
        .back-to-top {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #667eea;
            color: white;
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

    <!-- Back to top button -->
    <div class="back-to-top" id="back-to-top" onclick="scrollToTop()">↑</div>

    <script>
        // Search functionality with navigation
        let searchResults = [];
        let currentSearchIndex = -1;
        const searchInput = document.getElementById('search');
        const searchInfo = document.getElementById('search-info');
        const searchNav = document.getElementById('search-nav');
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');

        searchInput.addEventListener('input', function() {{
            const searchTerm = this.value.toLowerCase().trim();

            // Clear previous highlights and results
            document.querySelectorAll('.highlight').forEach(el => {{
                const parent = el.parentNode;
                parent.replaceChild(document.createTextNode(el.textContent), el);
                parent.normalize();
            }});

            searchResults = [];
            currentSearchIndex = -1;

            if (!searchTerm) {{
                searchInfo.textContent = '';
                searchNav.style.display = 'none';
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
    </script>
</body>
</html>'''

    # Generate hourly chart
    max_hour = max(stats['hourly']) if max(stats['hourly']) > 0 else 1
    hour_chart = ''
    for i, count in enumerate(stats['hourly']):
        height = (count / max_hour) * 100 if max_hour > 0 else 0
        hour_chart += f'<div class="hour-bar" style="height: {height}%" data-tooltip="{i}:00 - {count} msgs"></div>'

    # Generate messages HTML with sender-based coloring
    messages_html = ''
    last_date = None

    # Create a mapping of senders to indices for consistent coloring
    unique_senders = list(set(msg['sender'] for msg in messages))
    sender_colors = {sender: idx % 4 for idx, sender in enumerate(unique_senders)}

    for msg in messages:
        # Add date separator if needed
        if msg['date'] != last_date:
            messages_html += f'<div class="date-separator"><span>{msg["date"]}</span></div>\n'
            last_date = msg['date']

        # Create avatar initials
        initials = ''.join([n[0].upper() for n in msg['sender'].split()[:2]])

        # Determine sender class for coloring
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
                messages_html += f'\n            <img src="{photo_path}" class="message-photo" onclick="openModal(this.src)" alt="Photo" loading="lazy">'
            messages_html += '\n        </div>'

        # Add videos
        if msg['videos']:
            for video in msg['videos']:
                video_path = video.get('uri', '')
                messages_html += f'''
        <video controls class="message-video">
            <source src="{video_path}" type="video/mp4">
            Your browser does not support the video tag.
        </video>'''

        # Add reactions (with emoji support)
        if msg['reactions']:
            messages_html += '\n        <div class="reactions">'
            for reaction in msg['reactions']:
                messages_html += f'\n            <span class="reaction">{reaction["reaction"]} {html.escape(reaction["actor"])}</span>'
            messages_html += '\n        </div>'

        messages_html += '\n    </div>\n</div>\n'

    # Format the template
    html_content = html_template.format(
        participants=' & '.join(participants),
        total_messages=stats['total'],
        total_photos=stats['photos'],
        total_videos=stats['videos'],
        total_links=stats['links'],
        first_date=stats.get('first_date', 'N/A'),
        last_date=stats.get('last_date', 'N/A'),
        hour_chart=hour_chart,
        messages_html=messages_html
    )

    return html_content

def main():
    print("\n🔍 Scanning Facebook Messenger export...")
    conversations = list_all_conversations()

    if not conversations:
        print("❌ No conversations found in the export!")
        return

    conv_index = display_conversations(conversations)

    print("\n" + "="*100)
    print("Enter the number of the conversation you want to export (or 'q' to quit):")

    while True:
        try:
            choice = input("\n📝 Your choice: ").strip()

            if choice.lower() == 'q':
                print("👋 Goodbye!")
                return

            choice_num = int(choice)

            if choice_num not in conv_index:
                print("❌ Invalid number. Please try again.")
                continue

            selected = conv_index[choice_num]
            break

        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit.")

    # Process the selected conversation
    conv_path = selected['path']
    conv_name = ' & '.join(selected['participants'][:2])

    print(f"\n✅ Selected: {conv_name}")
    print(f"📂 Path: {conv_path}")
    print("⏳ Loading messages...")

    messages, participants = load_messages(conv_path)
    print(f"✅ Loaded {len(messages)} messages")

    print("📊 Generating statistics...")
    stats = generate_stats(messages)

    print("🔨 Generating HTML...")
    html_content = generate_html(messages, participants, stats, conv_name)

    # Create output filename based on participants
    safe_name = '_'.join(selected['participants'][:2]).replace(' ', '').lower()
    output_file = f'server_data/export_{safe_name}.html'

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ HTML file generated: {output_file}")
    print(f"📊 {len(messages)} messages included")
    print(f"🔍 Search with result count and navigation")
    print(f"📅 Date picker for navigation")
    print(f"😀 Emoji reactions display")
    print(f"\n🌐 Open http://localhost:8000/{output_file} in your browser")
    print(f"💡 Don't forget to run: python3 server.py")

if __name__ == '__main__':
    main()