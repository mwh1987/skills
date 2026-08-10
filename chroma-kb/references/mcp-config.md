# Chroma MCP Connection Config

MCP server for Chroma DB provides vector search capabilities via Model Context Protocol.

## Setup

1. Ensure Chroma server is running:
   ```bash
   chroma run --path /home/mwh1987/.openclaw/workspace/chroma-data --port 8000 --host 127.0.0.1
   ```

2. MCP server command (via chroma-mcp):
   ```json
   {
     "chroma": {
       "command": "chroma-mcp",
       "args": ["--client-type", "http", "--host", "127.0.0.1", "--port", "8000"]
     }
   }
   ```

3. Persistent client (alternative):
   ```json
   {
     "chroma": {
       "command": "chroma-mcp",
       "args": ["--client-type", "persistent", "--data-dir", "/home/mwh1987/.openclaw/workspace/chroma-data"]
     }
   }
   ```

## Tools Provided by MCP

- `chroma_list_collections` - List all collections
- `chroma_create_collection` - Create a new collection
- `chroma_peek_collection` - View sample documents
- `chroma_get_collection_info` - Get collection stats
- `chroma_get_collection_count` - Get document count
- `chroma_add_documents` - Add documents
- `chroma_query_documents` - Semantic search
- `chroma_get_documents` - Get by IDs/filters
- `chroma_update_documents` - Update documents
- `chroma_delete_documents` - Delete documents
- `chroma_delete_collection` - Delete a collection
- `chroma_modify_collection` - Update name/metadata
