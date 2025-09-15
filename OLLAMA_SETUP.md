# 🤖 Ollama Setup for Semantic Search

This guide helps you set up Ollama for semantic search with Czech language support.

## 1. Install Ollama

### macOS
```bash
brew install ollama
```

### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### Windows
Download from: https://ollama.ai/download/windows

## 2. Start Ollama Service

```bash
ollama serve
```
Keep this running in a terminal window.

## 3. Install Embedding Model

We recommend `nomic-embed-text` for good multilingual support including Czech:

```bash
ollama pull nomic-embed-text
```

This downloads ~274MB and provides 768-dimensional embeddings.

### Alternative Models

For better quality (but larger):
```bash
ollama pull mxbai-embed-large
```

For faster/smaller:
```bash
ollama pull all-minilm
```

## 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## 5. Test Ollama

```python
import ollama

# Test embedding
response = ollama.embeddings(
    model='nomic-embed-text',
    prompt='Ahoj, jak se máš?'  # Czech test
)

print(f"Embedding size: {len(response['embedding'])}")
# Should print: Embedding size: 768
```

## Usage

Once set up, the messenger server will automatically:
1. Detect Ollama is available
2. Generate embeddings for messages
3. Cache them in `server_data/embeddings/`
4. Enable semantic search in the UI

## Troubleshooting

### "Ollama not found"
- Make sure `ollama serve` is running
- Check installation: `ollama --version`

### "Model not found"
- Pull the model: `ollama pull nomic-embed-text`
- List installed models: `ollama list`

### Slow performance
- First-time embedding generation takes time (~5-10 min for 10k messages)
- Subsequent searches use cached embeddings (fast)
- Consider using smaller model like `all-minilm`

## Privacy Note

✅ **100% Local**: All processing happens on your machine
✅ **No Internet Required**: After model download
✅ **Your Data Stays Private**: Nothing sent to external servers