# notebooklm-client

**Unofficial Python client for Google NotebookLM API**

A comprehensive Python library and CLI for automating Google NotebookLM. Programmatically manage notebooks, add sources, query content, and generate studio artifacts like podcasts, videos, quizzes, and research reports using reverse-engineered RPC APIs.

[![PyPI version](https://badge.fury.io/py/notebooklm-client.svg)](https://badge.fury.io/py/notebooklm-client)
[![Python Version](https://img.shields.io/pypi/pyversions/notebooklm-client.svg)](https://pypi.org/project/notebooklm-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Notebook Management**: Create, list, rename, and delete notebooks.
- **Source Integration**:
  - Web URLs (with automatic YouTube transcript extraction).
  - Raw text content.
  - PDF documents (via Docling or PyMuPDF backends).
  - Native file uploads (PDF, TXT, MD, DOCX) without local text extraction.
- **AI-Powered Querying**: Full-featured chat interface with streaming support and conversation history.
- **Studio Artifacts**:
  - **Audio Overviews**: Generate two-person podcasts with custom instructions, formats (Deep Dive, Brief, Critique, Debate), and lengths.
  - **Video Overviews**: Create explainer videos with multiple visual styles (Classic, Anime, Whiteboard, etc.).
  - **Educational Tools**: Generate Quizzes, Flashcards, and Study Guides.
  - **Visuals & Data**: Create Infographics, Slide Decks, and Data Tables.
- **Agentic Research**: Trigger Fast or Deep research agents to gather information from the web or Google Drive and import findings directly.

## Installation

### Basic (CLI + API)
```bash
pip install notebooklm-client
```

### With Browser Login Support (Required for first-time setup)
```bash
pip install "notebooklm-client[browser]"
playwright install chromium
```

### With PDF Processing Support
```bash
# Docling backend (Recommended for better structure)
pip install "notebooklm-client[pdf-docling]"

# PyMuPDF backend (Faster, lightweight)
pip install "notebooklm-client[pdf-pymupdf]"

# Full PDF support
pip install "notebooklm-client[pdf]"
```

### Full Installation
```bash
pip install "notebooklm-client[all]"
playwright install chromium
```

## Authentication

NotebookLM uses Google's internal `batchexecute` RPC protocol, which requires valid session cookies and CSRF tokens.

### Option 1: CLI Login (Recommended)
The easiest way to authenticate is using the built-in login command:
```bash
notebooklm login
```
This will:
1. Open a real Chromium window using a **persistent browser profile** (located at `~/.notebooklm/browser_profile/`).
2. Allow you to log in to your Google account manually.
3. Save the session state to `~/.notebooklm/storage_state.json`.

**Why a persistent profile?** Google often blocks automated login attempts. Using a persistent profile makes the browser appear as a regular user installation, significantly reducing bot detection.

### Option 2: Custom Storage Path
If you need to manage multiple accounts or specific paths:
```bash
notebooklm login --storage /path/to/auth.json
notebooklm --storage /path/to/auth.json list
```

## Quick Start

### CLI Usage
```bash
# Create a notebook
notebooklm create "AI Research"

# Add a source
notebooklm add-url <notebook_id> "https://en.wikipedia.org/wiki/Artificial_intelligence"

# Ask a question
notebooklm query <notebook_id> "Summarize the history of AI"

# Generate a podcast
notebooklm audio <notebook_id> --instructions "Make it humorous and casual"
```

### Python API
```python
import asyncio
from notebooklm import NotebookLMClient

async def main():
    # Automatically loads auth from default storage path
    async with await NotebookLMClient.from_storage() as client:
        # 1. Create notebook
        nb = await client.create_notebook("My Project")
        nb_id = nb[0]
        
        # 2. Add sources
        await client.add_source_url(nb_id, "https://example.com/data")
        
        # 3. Query
        response = await client.query(nb_id, "What are the key findings?")
        print(f"AI: {response['answer']}")
        
        # 4. Generate Audio Overview
        status = await client.generate_audio(nb_id)
        print(f"Generation Task ID: {status[0]}")

asyncio.run(main())
```

## CLI Reference

| Command | Arguments | Description |
|---------|-----------|-------------|
| `login` | `[--storage PATH]` | Authenticate via browser |
| `list` | - | List all notebooks |
| `create` | `TITLE` | Create a new notebook |
| `delete` | `NB_ID` | Delete a notebook |
| `rename` | `NB_ID TITLE` | Rename a notebook |
| `add-url` | `NB_ID URL` | Add URL source (supports YouTube) |
| `add-text` | `NB_ID TITLE TEXT`| Add raw text source |
| `add-file` | `NB_ID PATH [--mime-type]` | Add file source (native upload) |
| `add-pdf` | `NB_ID PATH` | Add PDF source (with text extraction) |
| `query` | `NB_ID TEXT` | Chat with the notebook |
| `audio` | `NB_ID` | Generate podcast overview |
| `slides` | `NB_ID` | Generate slide deck |
| `research`| `NB_ID QUERY` | Start AI research agent |

## Advanced API Usage

### High-Level Services
For a cleaner, object-oriented approach, use the service classes:

```python
from notebooklm.services import NotebookService, SourceService, ArtifactService

# notebook_svc.list() returns List[Notebook] objects
notebook_svc = NotebookService(client)
notebooks = await notebook_svc.list()

# artifact_svc handles polling and status
artifact_svc = ArtifactService(client)
status = await artifact_svc.generate_audio(nb_id, host_instructions="Focus on safety")
result = await artifact_svc.wait_for_completion(nb_id, status.task_id)
print(f"Audio URL: {result.url}")
```

### Customizing Generation

```python
from notebooklm.rpc import VideoStyle, VideoFormat, AudioFormat

# Generate a video with specific style
await client.generate_video(
    nb_id,
    video_style=VideoStyle.ANIME,
    video_format=VideoFormat.EXPLAINER,
    instructions="Focus on visual metaphors"
)

# Generate a 'Debate' style podcast
await client.generate_audio(
    nb_id,
    audio_format=AudioFormat.DEBATE
)
```

## Troubleshooting

### "Auth not found" or "Unauthorized"
- Run `notebooklm login` again to refresh your session.
- Ensure the `storage_state.json` file exists at `~/.notebooklm/storage_state.json`.

### Google Login Blocked
- If you see a "This browser or app may not be secure" message, ensure you are using the `notebooklm login` command which uses a persistent profile.
- Try logging into Google in a regular Chrome browser first, then run `notebooklm login`.

### PDF Extraction Errors
- If `add-pdf` fails, ensure you installed the required extras: `pip install "notebooklm[pdf]"`.
- For `docling`, some systems may require additional libraries (libGL, etc.). Try the `pymupdf` backend if `docling` fails.

## Known Issues

- **RPC Stability**: Since this uses reverse-engineered private APIs, Google may change internal IDs (`wXbhsf`, etc.) at any time, which would break the library.
- **Audio Instructions**: The exact parameter position for audio instructions is still being verified for some edge cases.
- **Rate Limiting**: Heavy usage may trigger Google's rate limiting or temporary bans. Use responsibly.

## License

MIT License. See [LICENSE](LICENSE) for details.

---
*Disclaimer: This is an unofficial library and is not affiliated with or endorsed by Google.*
