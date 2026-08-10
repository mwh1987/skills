---
name: "chroma-kb"
description: "Manage a local Chroma vector database for semantic knowledge search with FastEmbed BGE-small-zh-v1.5 embeddings and markitdown document ingestion."
---

# Chroma Knowledge Base

Local vector database with FastEmbed BGE embeddings for semantic Chinese document search.

## Architecture

```
Documents → markitdown → markdown → chunks → FastEmbed BGE → Chroma DB
                                                                   ↓
User query → FastEmbed BGE → Chroma similarity search → results
```

## Quick Start

```bash
# 1. Start servers (if not running)
chroma run --path /home/mwh1987/.openclaw/workspace/chroma-data --port 8000 --host 127.0.0.1 &
python3 /home/mwh1987/.openclaw/workspace/chroma_mcp_server.py --mcp-port 9000 --chroma-port 8000 &

# 2. Ingest files
python3 /home/mwh1987/.openclaw/workspace/chroma_ingest.py ingest <file_or_dir> -c xiangban_tong

# 3. Search
python3 /home/mwh1987/.openclaw/workspace/chroma_ingest.py search "关键词"
```

## Ingestion Pipeline

1. **Convert** — `markitdown` converts PDF/DOCX/XLSX/PPTX/HTML/etc to markdown
2. **Chunk** — split into ~500 char chunks with 50 char overlap, preferring newline boundaries
3. **Embed** — `FastEmbed BAAI/bge-small-zh-v1.5` (512-dim cosine similarity)
4. **Store** — Chroma persistent client at `chroma-data/`

## Key Files

| File | Purpose |
|------|---------|
| `chroma_db.py` | Core library: FastEmbed BGE function, client helpers |
| `chroma_ingest.py` | CLI tool for ingest/search/list |
| `chroma_mcp_server.py` | MCP HTTP server for other agents |
| `chroma-data/` | Persistent Chroma storage |

## Embedding Model

- **Model:** `FastEmbed BAAI/bge-small-zh-v1.5`
- **Dimensions:** 512
- **Similarity:** Cosine
- **Inference:** ONNX, CPU-friendly

## MCP Connection

MCP server runs at `http://127.0.0.1:9000/mcp` (streamable-http).

For other agents (antigravity, etc.):

```json
{
  "baseUrl": "http://127.0.0.1:9000/mcp"
}
```

### Available MCP Tools

| Tool | Purpose |
|------|---------|
| `chroma_list_collections` | List all collections |
| `chroma_create_collection` | Create with HNSW config |
| `chroma_add_documents` | Add docs with metadata |
| `chroma_query_documents` | Semantic search |
| `chroma_get_documents` | Get by IDs/filters |
| `chroma_update_documents` | Update content/metadata |
| `chroma_delete_documents` | Delete docs |
| `chroma_peek_collection` | Sample preview |
| `chroma_get_collection_info` | Stats & metadata |
| `chroma_get_collection_count` | Document count |
| `chroma_modify_collection` | Rename/update |
| `chroma_delete_collection` | Delete collection |
| `chroma_fork_collection` | Fork a collection |

## Troubleshooting

- **Chroma won't start:** `chroma run --path /home/mwh1987/.openclaw/workspace/chroma-data --port 8000`
- **MCP won't start:** `python3 /home/mwh1987/.openclaw/workspace/chroma_mcp_server.py --mcp-port 9000`
- **FastEmbed download:** First run auto-downloads BGE model via HF mirror
- **No results:** Check collection has docs: `chroma_ingest.py list`
