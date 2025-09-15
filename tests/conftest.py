#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for tests.
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def mock_fb_export(temp_dir):
    """Create a mock Facebook export structure."""
    export_path = Path(temp_dir) / "fb_export" / "your_facebook_activity" / "messages"

    # Create folder structure
    folders = ['inbox', 'archived_threads', 'filtered_threads']
    for folder in folders:
        folder_path = export_path / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        # Create sample conversations
        for i in range(2):
            conv_path = folder_path / f"conversation_{i}"
            conv_path.mkdir(exist_ok=True)

            # Create message file
            messages = {
                "participants": [
                    {"name": f"User {i}"},
                    {"name": f"Friend {i}"}
                ],
                "messages": [
                    {
                        "sender_name": f"User {i}",
                        "timestamp_ms": 1704110400000 + (j * 1000),
                        "content": f"Test message {j}",
                        "type": "Generic"
                    }
                    for j in range(5)
                ]
            }

            with open(conv_path / "message_1.json", "w", encoding="utf-8") as f:
                json.dump(messages, f)

    return export_path


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        {
            "sender_name": "Alice",
            "timestamp_ms": 1704110400000,
            "content": "Hello! How are you?",
            "type": "Generic"
        },
        {
            "sender_name": "Bob",
            "timestamp_ms": 1704110500000,
            "content": "I'm good, thanks! And you?",
            "type": "Generic",
            "reactions": [
                {"actor": "Alice", "reaction": "👍"}
            ]
        },
        {
            "sender_name": "Alice",
            "timestamp_ms": 1704110600000,
            "content": "Check out this photo!",
            "photos": [{"uri": "photo_1.jpg"}],
            "type": "Generic"
        },
        {
            "sender_name": "Bob",
            "timestamp_ms": 1704110700000,
            "content": "Nice! Here's a video",
            "videos": [{"uri": "video_1.mp4"}],
            "type": "Generic"
        },
        {
            "sender_name": "Alice",
            "timestamp_ms": 1704110800000,
            "content": "Visit https://example.com for more info",
            "type": "Generic"
        }
    ]


@pytest.fixture
def sample_czech_messages():
    """Create sample Czech messages for testing."""
    return [
        {
            "sender_name": "Petr",
            "timestamp_ms": 1704110400000,
            "content": "Ahoj! Jak se máš?",
            "type": "Generic"
        },
        {
            "sender_name": "Lucie",
            "timestamp_ms": 1704110500000,
            "content": "Dobře, díky! Půjdeme zítra na kávu?",
            "type": "Generic"
        },
        {
            "sender_name": "Petr",
            "timestamp_ms": 1704110600000,
            "content": "Určitě! V kolik hodin?",
            "type": "Generic"
        }
    ]


@pytest.fixture
def mock_ollama():
    """Mock Ollama for testing without actual model."""
    with patch('semantic_search.ollama') as mock:
        # Mock list response
        mock.list.return_value = {
            'models': [
                {'name': 'nomic-embed-text'},
                {'name': 'llama3.2:3b'}
            ]
        }

        # Mock embeddings response
        mock.embeddings.return_value = {
            'embedding': [0.1] * 768
        }

        # Mock generate response
        mock.generate.return_value = {
            'response': 'This is a test summary.'
        }

        # Mock show response
        mock.show.return_value = {
            'name': 'nomic-embed-text',
            'parameters': 'embedding_size: 768'
        }

        yield mock


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        'PORT': '8080',
        'SEMANTIC_SEARCH_ENABLED': 'true',
        'OLLAMA_MODEL': 'test-model',
        'EMBEDDINGS_CACHE_DIR': 'test_cache',
        'MIN_MESSAGES_FOR_PROGRESS': '100'
    }

    with patch.dict('os.environ', env_vars):
        yield env_vars


@pytest.fixture
def mock_http_request():
    """Create a mock HTTP request."""
    request = Mock()
    request.makefile.return_value = Mock()
    return request


@pytest.fixture
def mock_http_server():
    """Create a mock HTTP server."""
    server = Mock()
    server.conversation_data = {}
    return server