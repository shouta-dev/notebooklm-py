# Adding New RPC Methods

**Status:** Active
**Last Updated:** 2026-01-07

Step-by-step guide for adding new RPC methods to `notebooklm-py`.

## When You Need This

- **New feature**: NotebookLM adds a feature you want to support
- **Method ID changed**: Google updated an RPC ID (causes `RPCError: No result found`)
- **Payload changed**: Existing method returns unexpected results

## Overview

```
1. Capture → 2. Decode → 3. Implement → 4. Test → 5. Document
```

| Step | Tools | Output |
|------|-------|--------|
| Capture | Chrome DevTools or Playwright | Raw request/response |
| Decode | Browser console or Python | RPC ID + params structure |
| Implement | Code editor | types.py + _*.py changes |
| Test | pytest | Unit + integration + E2E tests |
| Document | Markdown | Update rpc-ui-reference.md |

---

## Step 1: Capture the RPC Call

Use one of these approaches (see [rpc-capture.md](../reference/internals/rpc-capture.md) for details):

### Quick: Chrome DevTools

1. Open NotebookLM in Chrome
2. Open DevTools → Network tab
3. Filter by `batchexecute`
4. Perform the action in the UI
5. Click the request → copy from Headers and Payload tabs

### Systematic: Playwright

```python
# See rpc-capture.md for full setup
async def capture_action(page, action_name):
    # Clear, perform action, capture request
    ...
```

### What to Capture

From the request:
- **URL `rpcids` parameter**: The 6-character RPC ID (e.g., `wXbhsf`)
- **`f.req` body**: URL-encoded payload

From the response:
- **Response body**: Starts with `)]}'\n`, contains result

---

## Step 2: Decode the Payload

### Decode f.req in Browser Console

```javascript
// Paste the f.req value
const encoded = "[[...encoded data...]]";
const decoded = decodeURIComponent(encoded);
const outer = JSON.parse(decoded);

console.log("RPC ID:", outer[0][0][0]);
console.log("Params:", JSON.parse(outer[0][0][1]));
```

### Decode in Python

```python
import json
from urllib.parse import unquote

def decode_f_req(encoded: str) -> dict:
    decoded = unquote(encoded)
    outer = json.loads(decoded)
    inner = outer[0][0]
    return {
        "rpc_id": inner[0],
        "params": json.loads(inner[1]) if inner[1] else None,
    }
```

### Understand the Structure

RPC params are **position-sensitive arrays**. Document each position:

```python
# Example: ADD_SOURCE for URL
params = [
    [[None, None, [url], None, None, None, None, None]],  # 0: Source data, URL at [2]
    notebook_id,   # 1: Notebook ID
    [2],           # 2: Fixed flag
    None,          # 3: Optional settings
    None,          # 4: Optional settings
]
```

Key patterns to identify:
- **Nested source IDs**: `[id]`, `[[id]]`, `[[[id]]]` - check existing methods
- **Fixed flags**: Arrays like `[2]`, `[1]` that don't change
- **Optional positions**: Often `None`

---

## Step 3: Implement

### 3a. Add RPC Method ID

Edit `src/notebooklm/rpc/types.py`:

```python
class RPCMethod(str, Enum):
    # ... existing methods ...

    # Add new method with descriptive name
    NEW_FEATURE = "abc123"  # 6-char ID from capture
```

### 3b. Implement Client Method

Choose the appropriate API file:
- `_notebooks.py` - Notebook operations
- `_sources.py` - Source operations
- `_artifacts.py` - Artifact/generation operations
- `_chat.py` - Chat operations
- `_notes.py` - Note operations
- `_research.py` - Research operations

Add the method:

```python
async def new_feature(
    self,
    notebook_id: str,
    some_param: str,
    optional_param: Optional[str] = None,
) -> SomeResult:
    """Short description of what this does.

    Args:
        notebook_id: The notebook ID.
        some_param: Description.
        optional_param: Description.

    Returns:
        Description of return value.

    Raises:
        RPCError: If the RPC call fails.
    """
    # Build params array matching captured structure
    params = [
        some_param,      # Position 0
        notebook_id,     # Position 1
        [2],             # Position 2: Fixed flag
    ]

    # Make RPC call
    result = await self._core.rpc_call(
        RPCMethod.NEW_FEATURE,
        params,
        source_path=f"/notebook/{notebook_id}",
    )

    # Parse response into dataclass
    if result is None:
        return None
    return SomeResult.from_api_response(result)
```

### 3c. Add Dataclass (if needed)

Edit `src/notebooklm/types.py`:

```python
@dataclass
class SomeResult:
    id: str
    title: str
    # ... other fields

    @classmethod
    def from_api_response(cls, data: list[Any]) -> "SomeResult":
        """Parse API response array into dataclass."""
        return cls(
            id=data[0],
            title=data[1],
            # Map positions to fields
        )
```

### 3d. Add CLI Command (if needed)

Edit appropriate CLI file in `src/notebooklm/cli/`:

```python
@some_group.command("new-feature")
@click.argument("param")
@click.pass_context
@async_command
async def new_feature_cmd(ctx, param: str):
    """Short description."""
    nb_id = get_notebook_id(ctx)
    async with get_client(ctx) as client:
        result = await client.some_api.new_feature(nb_id, param)
        console.print(f"Result: {result}")
```

---

## Step 4: Test

### 4a. Unit Test (encoding)

`tests/unit/test_encoder.py`:

```python
def test_encode_new_feature():
    params = ["value", "notebook_id", [2]]
    result = encode_rpc_request(RPCMethod.NEW_FEATURE, params)

    assert "abc123" in result  # RPC ID
    assert "value" in result
```

### 4b. Integration Test (mocked response)

`tests/integration/test_new_feature.py`:

```python
@pytest.mark.asyncio
async def test_new_feature(mock_client):
    mock_response = ["result_id", "Result Title"]

    with patch('notebooklm._core.ClientCore.rpc_call', new_callable=AsyncMock) as mock:
        mock.return_value = mock_response

        result = await mock_client.some_api.new_feature("nb_id", "param")

        assert result.id == "result_id"
        assert result.title == "Result Title"
```

### 4c. E2E Test (real API)

`tests/e2e/test_new_feature_e2e.py`:

```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_new_feature_e2e(client, read_only_notebook_id):
    """Test new feature against real API."""
    # Use read_only_notebook_id for read-only tests
    # Use temp_notebook for CRUD tests
    # Use generation_notebook_id for artifact generation tests
    # See docs/contributing/testing.md for fixture guidance
    result = await client.some_api.new_feature(read_only_notebook_id, "param")
    assert result is not None
```

### Run Tests

```bash
# Unit + integration
pytest tests/unit tests/integration -v

# E2E (requires auth)
pytest tests/e2e/test_new_feature_e2e.py -m e2e -v
```

---

## Step 5: Document

Update `docs/reference/internals/rpc-ui-reference.md`:

```markdown
### NEW_FEATURE (`abc123`)

**Purpose:** Short description

**Params:**
```python
params = [
    some_value,      # 0: Description
    notebook_id,     # 1: Notebook ID
    [2],             # 2: Fixed flag
]
```

**Response:** Description of response structure

**Source:** `_some_api.py:123`
```

---

## Common Pitfalls

### Wrong nesting level

Different methods need different source ID nesting:

```python
# Single: [source_id]
# Double: [[source_id]]
# Triple: [[[source_id]]]
```

Check similar methods for the pattern.

### Position sensitivity

Params are arrays, not dicts. Position matters:

```python
# WRONG - missing position 2
params = [value, notebook_id, settings]

# RIGHT - explicit None for unused positions
params = [value, notebook_id, None, settings]
```

### Forgetting source_path

Some methods require `source_path` for routing:

```python
# Without source_path - may fail
await self._core.rpc_call(RPCMethod.X, params)

# With source_path - correct
await self._core.rpc_call(
    RPCMethod.X,
    params,
    source_path=f"/notebook/{notebook_id}",
)
```

### Response parsing

API returns nested arrays. Print raw response first:

```python
result = await self._core.rpc_call(...)
print(f"DEBUG: {result}")  # See actual structure
```

---

## Checklist

- [ ] Captured RPC ID and params structure
- [ ] Added to `RPCMethod` enum in `rpc/types.py`
- [ ] Implemented method in appropriate `_*.py` file
- [ ] Added dataclass if needed in `types.py`
- [ ] Added CLI command if needed
- [ ] Unit test for encoding
- [ ] Integration test with mock
- [ ] E2E test (manual verification OK for rare operations)
- [ ] Updated `rpc-ui-reference.md`

---

## See Also

- [RPC Capture Guide](../reference/internals/rpc-capture.md) - Detailed capture methodology
- [RPC UI Reference](../reference/internals/rpc-ui-reference.md) - Existing payloads
- [Debugging Guide](debugging.md) - Troubleshooting RPC issues
- [Testing Guide](testing.md) - Test patterns and fixtures
