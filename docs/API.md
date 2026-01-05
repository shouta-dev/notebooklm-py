# NotebookLM API Reference

Detailed documentation for the NotebookLM Python API client and high-level services.

## NotebookLMClient

The primary interface for interacting with NotebookLM's reverse-engineered RPC API.

### Initialization

```python
from notebooklm import NotebookLMClient

# From storage (recommended)
async with await NotebookLMClient.from_storage() as client:
    ...

# Manual initialization
from notebooklm.auth import AuthTokens
auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=sid)
async with NotebookLMClient(auth) as client:
    ...
```

### Notebook Operations

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `list_notebooks` | - | `list` | List all notebooks with metadata |
| `create_notebook` | `title: str` | `list` | Create a new notebook |
| `get_notebook` | `id: str` | `list` | Get detailed notebook data |
| `rename_notebook` | `id: str, title: str` | `list` | Rename an existing notebook |
| `delete_notebook` | `id: str` | `list` | Delete a notebook |

### Source Operations

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `add_source_url` | `nb_id: str, url: str` | `list` | Add URL source (YouTube supported) |
| `add_source_text` | `nb_id: str, title: str, text: str` | `list` | Add raw text content |
| `add_source_file` | `nb_id: str, file_path: str\|Path, mime_type: str` | `list` | Add file source (native upload) |
| `get_source` | `nb_id: str, src_id: str` | `list` | Get source details |
| `delete_source` | `nb_id: str, src_id: str` | `list` | Remove a source |

#### Add File Source (Native Upload)

Upload files directly to NotebookLM (PDF, TXT, MD, DOCX, etc.):

```python
await client.add_source_file(notebook_id, "document.pdf")

await client.add_source_file(
    notebook_id, 
    "report.docx",
    mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

await client.add_source_file(notebook_id, "notes.txt")
await client.add_source_file(notebook_id, "readme.md")
await client.add_source_file(notebook_id, "paper.pdf")
```

**Supported MIME types:**
- `application/pdf` - PDF documents
- `text/plain` - Text files
- `text/markdown` - Markdown files
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document` - Word documents

### AI Features

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `query` | `nb_id, question, conv_id, ...` | `dict` | Chat with the notebook |
| `get_summary` | `nb_id: str` | `str` | Get notebook auto-summary |
| `start_research` | `nb_id, query, src, mode` | `dict` | Start research agent |
| `poll_research` | `nb_id: str` | `dict` | Check research status |

### Studio Content (Artifacts)

| Method | Parameters | Return Type | Description |
|--------|------------|-------------|-------------|
| `generate_audio` | `nb_id, source_ids, lang, format, length` | `list` | Generate podcast |
| `generate_video` | `nb_id, source_ids, lang, instructions, style, format` | `list` | Generate video |
| `generate_slides` | `nb_id: str` | `list` | Generate slide deck |
| `generate_quiz` | `nb_id: str` | `list` | Generate quiz/flashcards |
| `poll_studio_status` | `nb_id, task_id` | `list` | Check generation status |

---

## High-Level Services

Services provide a more Pythonic, object-oriented way to interact with the API.

### NotebookService

```python
from notebooklm.services import NotebookService

service = NotebookService(client)

# Returns List[Notebook] objects
notebooks = await service.list()

# Create and get typed object
nb = await service.create("New Title")
print(nb.id, nb.title)
```

### SourceService

```python
from notebooklm.services import SourceService

service = SourceService(client)

# Add PDF (converts to text locally first)
source = await service.add_pdf(nb_id, Path("doc.pdf"))

# Add file (native upload - no conversion)
source = await service.add_file(nb_id, "document.pdf")

# Add URL
source = await service.add_url(nb_id, "https://...")
```

### ArtifactService

```python
from notebooklm.services import ArtifactService

service = ArtifactService(client)

# Generate and wait
status = await service.generate_audio(nb_id)
result = await service.wait_for_completion(nb_id, status.task_id)

if result.is_complete:
    print(f"Download link: {result.url}")
```

---

## Enums and Types

Found in `notebooklm.rpc`:

- `AudioFormat`: `DEEP_DIVE`, `BRIEF`, `CRITIQUE`, `DEBATE`
- `AudioLength`: `SHORT`, `DEFAULT`, `LONG`
- `VideoStyle`: `CLASSIC`, `WHITEBOARD`, `KAWAII`, `ANIME`, `WATERCOLOR`, etc.
- `VideoFormat`: `EXPLAINER`, `BRIEF`
- `QuizDifficulty`: `EASY`, `MEDIUM`, `HARD`
