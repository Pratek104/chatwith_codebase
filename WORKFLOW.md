# User Workflow - Seamless Experience

## How It Works Now

### Step 1: Connect Repository (Preprocessing Phase)
When user clicks "Connect Repository":

1. **Frontend**: Shows loading screen with steps:
   - Cloning repository...
   - Parsing code files...
   - Generating embeddings...
   - Finalizing knowledge base...

2. **Backend** (`POST /api/process`):
   - Clones the GitHub repository
   - Parses all supported code files
   - Chunks the code into manageable pieces
   - Creates embeddings using HuggingFace model
   - Stores everything in ChromaDB with unique identifier
   - Returns success message

**Time**: 20-60 seconds (one-time cost)

### Step 2: Ask Questions (Query Phase)
After repository is processed, user can ask questions:

1. **Frontend**: Shows "Thinking..." message (brief)

2. **Backend** (`POST /api/chat`):
   - Loads existing vector DB (instant!)
   - Retrieves only relevant code chunks (5 most relevant)
   - Sends to LLM with context
   - Returns answer with sources

**Time**: 2-5 seconds (feels instant!)

## Benefits

✅ **Seamless Experience**: Heavy processing happens upfront with clear progress
✅ **Fast Queries**: Subsequent questions are near-instant
✅ **Smart Caching**: Same repo = no reprocessing (until 1 hour expiry)
✅ **Clear Feedback**: Users see exactly what's happening

## API Endpoints

### Process Repository
```bash
POST /api/process
{
  "repo_url": "https://github.com/username/repo"
}

Response:
{
  "status": "success",
  "message": "Repository processed and indexed successfully",
  "repo_identifier": "username_repo_abc123"
}
```

### Chat with Repository
```bash
POST /api/chat
{
  "repo_url": "https://github.com/username/repo",
  "query": "What does this project do?"
}

Response:
{
  "answer": "This project is...",
  "sources": [...]
}
```

## Error Handling

If user tries to chat without processing first:
```
Error: "Repository not processed yet. Please process it first using /api/process endpoint."
```

If cache expires:
```
Error: "Repository cache expired. Please process it again."
```

## User Flow

```
1. User visits homepage (/)
   ↓
2. Clicks "Connect Repo"
   ↓
3. Enters GitHub URL
   ↓
4. Clicks "Connect Repository"
   ↓
5. [PREPROCESSING - 20-60s]
   - Cloning...
   - Parsing...
   - Embedding...
   ↓
6. Chat interface appears
   ↓
7. User asks questions
   ↓
8. [INSTANT RESPONSES - 2-5s]
   - Thinking...
   - Answer appears!
```

## Technical Details

- **Vector DB**: ChromaDB with persistent storage
- **Embeddings**: HuggingFace all-MiniLM-L6-v2
- **LLM**: Groq (openai/gpt-oss-120b)
- **Caching**: 1 hour per repository
- **Retrieval**: MMR (Maximum Marginal Relevance) for diverse results
