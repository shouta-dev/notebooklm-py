# AGENTS.md

Guidelines for AI agents working on `notebooklm-py`.

**IMPORTANT:** Follow documentation rules in [CONTRIBUTING.md](CONTRIBUTING.md) - especially the file creation and naming conventions.

## Quick Reference

See [CLAUDE.md](CLAUDE.md) for full project context. Essential commands:

```bash
source .venv/bin/activate    # Always activate venv first
pytest                       # Run tests
pip install -e ".[all]"      # Install in dev mode
```

## Code Style Guidelines

### Type Annotations (Python 3.9+)
```python
def process(items: list[str]) -> dict[str, Any]: ...
async def query(notebook_id: str, source_ids: Optional[list[str]] = None): ...

# Use TYPE_CHECKING for circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..api_client import NotebookLMClient
```

### Async Patterns
```python
# All client methods are async - use namespaced APIs
async with await NotebookLMClient.from_storage() as client:
    notebooks = await client.notebooks.list()
    await client.sources.add_url(nb_id, url)
    result = await client.chat.ask(nb_id, question)
```

### Data Structures
```python
@dataclass
class Notebook:
    id: str
    title: str
    created_at: Optional[datetime] = None

    @classmethod
    def from_api_response(cls, data: list[Any]) -> "Notebook": ...
```

### Enums for Constants
```python
class RPCMethod(str, Enum):
    LIST_NOTEBOOKS = "wXbhsf"

class AudioFormat(int, Enum):
    DEEP_DIVE = 1
```

### Error Handling
```python
class RPCError(Exception):
    def __init__(self, message: str, rpc_id: Optional[str] = None, code: Optional[Any] = None):
        self.rpc_id, self.code = rpc_id, code
        super().__init__(message)

raise RPCError(f"No result found for RPC ID: {rpc_id}", rpc_id=rpc_id)
raise ValueError(f"Invalid YouTube URL: {url}")  # For validation
```

### Docstrings
```python
def decode_response(raw_response: str, rpc_id: str, allow_null: bool = False) -> Any:
    """Complete decode pipeline: strip prefix -> parse chunks -> extract result.

    Args:
        raw_response: Raw response text from batchexecute
        rpc_id: RPC method ID to extract result for
        allow_null: If True, return None instead of raising when null

    Returns:
        Decoded result data

    Raises:
        RPCError: If RPC returned an error or result not found
    """
```

## Testing Patterns

```python
# Class-based for related tests
class TestDecodeResponse:
    def test_full_decode_pipeline(self): ...

# Markers
@pytest.mark.e2e      # End-to-end (requires auth)
@pytest.mark.slow     # Long-running (audio/video)
@pytest.mark.asyncio  # Async tests

# Async tests
@pytest.mark.asyncio
async def test_list_notebooks(self, client):
    notebooks = await client.notebooks.list()
    assert isinstance(notebooks, list)
```

## Do NOT

- Suppress type errors with `# type: ignore`
- Commit `.env` files or credentials
- Add dependencies without updating `pyproject.toml`
- Change RPC method IDs without verifying via network capture
- Delete or modify e2e tests without running them
- Create documentation files without following CONTRIBUTING.md rules
