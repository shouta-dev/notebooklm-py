# Network Traffic Analysis Methodology for NotebookLM RPC Reverse Engineering

**Created**: 2026-01-04
**Purpose**: Systematic approach for capturing and analyzing network traffic to reverse-engineer NotebookLM RPC calls

---

## Table of Contents

1. [Overview](#overview)
2. [Tools & Setup](#tools--setup)
3. [Capture Process](#capture-process)
4. [Payload Analysis](#payload-analysis)
5. [Response Analysis](#response-analysis)
6. [Documentation Template](#documentation-template)
7. [Validation Process](#validation-process)
8. [Known RPC Methods](#known-rpc-methods)
9. [Troubleshooting](#troubleshooting)

---

## Overview

NotebookLM uses Google's `batchexecute` protocol for API communication. This is a proprietary RPC-over-HTTP mechanism used across many Google products. Understanding this protocol is essential for reverse engineering.

### Key Concepts

| Term | Description |
|------|-------------|
| **batchexecute** | Google's internal RPC protocol endpoint |
| **RPC ID** | Short string identifier for each method (e.g., `wXbhsf`, `s0tc2d`) |
| **f.req** | URL-encoded JSON payload containing the RPC request |
| **at** | CSRF token (SNlM0e value) |
| **Anti-XSSI prefix** | `)]}'` prefix on responses to prevent JSON hijacking |
| **Chunked response** | Response format with byte counts before each JSON chunk |

### Protocol Flow

```
1. Client builds RPC request: [[[rpc_id, json_params, null, "generic"]]]
2. Client encodes to f.req URL parameter
3. Client POSTs to /_/LabsTailwindUi/data/batchexecute
4. Server responds with )]}' prefix + chunked JSON
5. Client strips prefix, parses chunks, extracts result
```

---

## Tools & Setup

### Required Tools

1. **Chrome DevTools** (primary)
   - Network tab for request capture
   - Console for debugging
   - Application tab for cookies/storage

2. **Optional Tools**
   - HAR file viewer/analyzer
   - curl for manual request testing
   - Python for automated testing

### Chrome DevTools Configuration

#### Network Tab Setup

1. Open Chrome DevTools (`F12` or `Cmd+Option+I`)
2. Go to **Network** tab
3. Enable these options:
   - [x] **Preserve log** (prevents clearing on navigation)
   - [x] **Disable cache** (ensures fresh requests)
4. Set filter to `batchexecute` to only show RPC calls

#### Recommended Filters

```
# Show only batchexecute calls
Filter: batchexecute

# Show only specific RPC method
Filter: rpcids=s0tc2d

# Show all XHR requests
Filter: XHR
```

### Authentication Verification

Before capturing traffic, verify you're logged in:

1. Navigate to `https://notebooklm.google.com/`
2. Open DevTools → Application → Cookies
3. Verify these cookies exist:
   - `SID`
   - `HSID`
   - `SSID`
   - `APISID`
   - `SAPISID`

---

## Capture Process

### Step-by-Step Capture Protocol

#### Phase 1: Preparation

```
1. Open NotebookLM in Chrome
2. Open DevTools → Network tab
3. Clear network log (Ctrl+L or click clear button)
4. Set filter to: batchexecute
5. Enable "Preserve log" checkbox
```

#### Phase 2: Isolate Single Action

**CRITICAL**: Perform ONE action at a time to isolate the exact RPC call.

```
1. Clear network log immediately before action
2. Perform the UI action (e.g., rename notebook)
3. Wait for request to complete (check status code)
4. DO NOT perform any other actions
```

#### Phase 3: Capture Request

1. Click on the `batchexecute` request in Network tab
2. Go to **Headers** tab:
   - Note the `rpcids` query parameter (this is the RPC method ID)
   - Note the `source-path` parameter
   
3. Go to **Payload** tab:
   - Find `f.req` parameter (this is the encoded payload)
   - Find `at` parameter (CSRF token)

4. Go to **Response** tab:
   - Note the response structure

#### Phase 4: Export for Analysis

**Option A: Copy as cURL**

Right-click request → Copy → Copy as cURL

```bash
# Example output:
curl 'https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute?rpcids=s0tc2d&source-path=/notebook/abc123&f.sid=xxx&rt=c' \
  -H 'content-type: application/x-www-form-urlencoded;charset=UTF-8' \
  -H 'cookie: SID=xxx; HSID=xxx; ...' \
  --data-raw 'f.req=...'
```

**Option B: Export HAR**

1. Right-click in Network tab
2. Select "Save all as HAR with content"
3. Save file for later analysis

---

## Payload Analysis

### URL Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `rpcids` | RPC method identifier | `s0tc2d` |
| `source-path` | Context path | `/notebook/{id}` |
| `f.sid` | Session ID (FdrFJe value) | `123456789` |
| `rt` | Response type | `c` (chunked) |
| `hl` | Language | `en` |
| `_reqid` | Request ID (incrementing) | `100000` |

### Body Parameters

| Parameter | Description |
|-----------|-------------|
| `f.req` | URL-encoded JSON payload |
| `at` | CSRF token (SNlM0e value) |

### Decoding f.req Payload

The `f.req` value is URL-encoded JSON. To decode:

#### Manual Decoding

1. Copy the `f.req` value from Payload tab
2. URL-decode it (use online tool or browser console):

```javascript
// In browser console:
decodeURIComponent('your_encoded_string_here')
```

3. Parse the resulting JSON:

```javascript
JSON.parse(decodedString)
```

#### Expected Structure

```json
[
  [
    [
      "rpc_id",           // e.g., "s0tc2d"
      "json_params",      // JSON-encoded parameters as string
      null,               // Reserved
      "generic"           // Request type
    ]
  ]
]
```

The `json_params` field is itself a JSON string that needs double-decoding:

```javascript
// Full decode example:
const fReq = decodeURIComponent(encodedFReq);
const outer = JSON.parse(fReq);
const rpcId = outer[0][0][0];           // "s0tc2d"
const paramsJson = outer[0][0][1];      // "[\"notebook_id\", {...}]"
const params = JSON.parse(paramsJson);  // ["notebook_id", {...}]
```

### Python Decoding Script

```python
import json
from urllib.parse import unquote

def decode_f_req(encoded_f_req: str) -> dict:
    """Decode f.req parameter to extract RPC details."""
    # Step 1: URL decode
    decoded = unquote(encoded_f_req)
    
    # Step 2: Parse outer JSON
    outer = json.loads(decoded)
    
    # Step 3: Extract inner structure
    inner = outer[0][0]
    rpc_id = inner[0]
    params_json = inner[1]
    
    # Step 4: Parse params JSON
    params = json.loads(params_json)
    
    return {
        "rpc_id": rpc_id,
        "params": params,
        "raw_inner": inner,
    }

# Usage:
# result = decode_f_req("your_encoded_value")
# print(json.dumps(result, indent=2))
```

---

## Response Analysis

### Response Format

Responses have this structure:

```
)]}'                          <- Anti-XSSI prefix
123                           <- Byte count of next chunk
["wrb.fr","rpc_id","..."]    <- JSON chunk
45                           <- Byte count
["di",123]                   <- Another chunk
```

### Parsing Response

```python
import json
import re

def parse_batchexecute_response(response_text: str, rpc_id: str) -> any:
    """Parse batchexecute response and extract result."""
    # Step 1: Strip anti-XSSI prefix
    if response_text.startswith(")]}'"):
        response_text = re.sub(r"^\)\]\}'\r?\n", "", response_text)
    
    # Step 2: Parse chunks
    chunks = []
    lines = response_text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        try:
            byte_count = int(line)
            i += 1
            if i < len(lines):
                json_str = lines[i]
                chunks.append(json.loads(json_str))
            i += 1
        except ValueError:
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                pass
            i += 1
    
    # Step 3: Find result for our RPC ID
    for chunk in chunks:
        if isinstance(chunk, list) and len(chunk) >= 3:
            if chunk[0] == "wrb.fr" and chunk[1] == rpc_id:
                result_data = chunk[2]
                # Double-decode if string
                if isinstance(result_data, str):
                    return json.loads(result_data)
                return result_data
    
    return None
```

### Common Chunk Types

| Prefix | Description |
|--------|-------------|
| `wrb.fr` | Result chunk for an RPC call |
| `di` | Debug/timing information |
| `er` | Error chunk |
| `e` | Generic envelope |

---

## Documentation Template

Use this template when documenting a newly discovered RPC method:

```markdown
### RPC Method: {METHOD_NAME}

**RPC ID**: `{rpc_id}`
**Purpose**: {Brief description of what this method does}
**Discovered**: {Date}

#### Request Structure

**URL Parameters**:
- `rpcids`: `{rpc_id}`
- `source-path`: `{typical source path}`

**Payload (f.req decoded)**:
```json
[
  // Describe each parameter
  "param1",     // Description of param1
  {"key": "value"},  // Description of object param
  null,         // Unused/optional
]
```

**Example Payload**:
```json
["notebook_id_here", {"title": "New Title"}]
```

#### Response Structure

**Success Response**:
```json
{
  // Document response structure
}
```

**Error Response**:
```json
["er", "{rpc_id}", "Error message"]
```

#### Implementation Notes

- {Any quirks or special handling needed}
- {What the UI does vs what the API expects}

#### Test Command

```bash
# curl command to test this RPC
curl 'https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute?rpcids={rpc_id}&...' \
  -H 'content-type: application/x-www-form-urlencoded;charset=UTF-8' \
  --data-raw 'f.req=...'
```

#### Python Implementation

```python
async def method_name(self, notebook_id: str, ...) -> Any:
    params = [...]  # Document the exact params
    return await self._rpc_call(
        RPCMethod.METHOD_NAME,
        params,
        source_path=f"/notebook/{notebook_id}",
    )
```
```

---

## Validation Process

### Step 1: Capture Working Request

1. Perform action in UI successfully
2. Capture the exact request that worked
3. Document all parameters exactly as sent

### Step 2: Reproduce with curl

```bash
# Copy the captured curl command
# Execute it to verify it still works
curl 'https://notebooklm.google.com/_/...' \
  -H 'cookie: ...' \
  --data-raw 'f.req=...'
```

### Step 3: Test with Python

```python
# Test in Python REPL or script
import asyncio
from notebooklm import NotebookLMClient

async def test():
    async with await NotebookLMClient.from_storage() as client:
        result = await client.your_method("notebook_id", ...)
        print(result)

asyncio.run(test())
```

### Step 4: Compare with Go Library

Check if the method exists in the [tmc/nlm](https://github.com/tmc/nlm) Go library:

```bash
# Clone and search
git clone https://github.com/tmc/nlm
grep -r "rpc_id_here" nlm/
```

Relevant files in tmc/nlm:
- `internal/api/client.go` - Main API methods
- `gen/method/` - Generated method definitions
- `internal/batchexecute/` - Protocol implementation

### Step 5: Verify Side Effects

After API call:
1. Refresh the UI
2. Verify the change was applied
3. Check if any other state was affected

---

## Known RPC Methods

### Currently Implemented

| RPC ID | Method | Status | Notes |
|--------|--------|--------|-------|
| `wXbhsf` | LIST_NOTEBOOKS | Working | Lists all user notebooks |
| `CCqFvf` | CREATE_NOTEBOOK | Working | Creates new notebook |
| `rLM1Ne` | GET_NOTEBOOK | Working | Gets notebook details |
| `WWINqb` | DELETE_NOTEBOOK | Working | Deletes notebook |
| `s0tc2d` | RENAME_NOTEBOOK | Working | Fixed 2026-01-04 via browser capture |
| `izAoDd` | ADD_SOURCE | Working | Adds URL or text source |
| `AHyHrd` | CREATE_AUDIO | Working | Generates podcast |
| `R7cb6c` | CREATE_VIDEO | Working | Generates video/slides |
| `gArtLc` | POLL_STUDIO | Working | Polls generation status |
| `hXya6e` | ACT_ON_SOURCES | Working | Mind map, FAQ, study guide, etc. |

### Documented RPC Methods

#### RENAME_NOTEBOOK (s0tc2d)

**Discovered**: 2026-01-04 via Playwright browser capture

**Request**:
- URL: `/_/LabsTailwindUi/data/batchexecute?rpcids=s0tc2d&source-path=%2F&...`
- source-path: `/` (root, NOT `/notebook/{id}`)

**Payload Format**:
```json
[
  "notebook_id",
  [
    [
      null,
      null,
      null,
      [null, "New Title Here"]
    ]
  ]
]
```

**Python Implementation**:
```python
params = [notebook_id, [[None, None, None, [None, new_title]]]]
await self._rpc_call(RPCMethod.RENAME_NOTEBOOK, params, source_path="/", allow_null=True)
```

**Response**: Returns `null` on success

**Key Discovery**: The title is nested at `params[1][0][3][1]`, not in a simple object like `{"title": "..."}`.

### Methods Needing Investigation

No methods currently need investigation.

---

## Troubleshooting

### Request Returns Null but No Error

**Symptom**: API returns `null` but doesn't show error.

**Causes**:
1. Payload format is close but not exact
2. Missing required field
3. Wrong data type for a field

**Solution**: Capture exact browser request and compare byte-by-byte.

### RPC ID Not Found in Response

**Symptom**: `extract_rpc_result` returns None.

**Causes**:
1. Wrong RPC ID being searched
2. Response uses different chunk format
3. Request failed silently

**Solution**: Log raw response and examine all chunks.

### Changes Not Persisted

**Symptom**: API returns success but change doesn't appear in UI.

**Causes**:
1. Payload accepted but not processed
2. Missing context (source-path, etc.)
3. Server-side validation failing silently

**Solution**: Compare working UI request with failing programmatic request.

### CSRF Token Issues

**Symptom**: 403 or authentication errors.

**Causes**:
1. Stale CSRF token
2. Token not included in request
3. Wrong encoding

**Solution**: Re-fetch tokens from page HTML or refresh storage state.

---

## Example: Capturing rename_notebook

### Step 1: Navigate to NotebookLM

```
https://notebooklm.google.com/
```

### Step 2: Open DevTools and Clear Network

1. F12 → Network tab
2. Clear log
3. Filter: `batchexecute`

### Step 3: Perform Rename Action

1. Find a notebook in the list
2. Click the three-dot menu (⋮)
3. Select "Edit title"
4. Enter new title
5. Press Enter or click Save

### Step 4: Capture the Request

1. Look for the new batchexecute request
2. Check `rpcids` parameter (should be `s0tc2d` or similar)
3. Copy the full `f.req` value

### Step 5: Decode and Document

```javascript
// In console:
const encoded = "paste_f_req_here";
const decoded = decodeURIComponent(encoded);
const outer = JSON.parse(decoded);
console.log(JSON.stringify(outer, null, 2));
const params = JSON.parse(outer[0][0][1]);
console.log("Params:", JSON.stringify(params, null, 2));
```

### Step 6: Update api_client.py

Based on captured payload, update the `rename_notebook` method with correct params structure.

---

## Appendix: batchexecute Protocol Reference

### Request Encoding

```python
def encode_rpc_request(rpc_id: str, params: list) -> str:
    """Encode params for batchexecute."""
    import json
    from urllib.parse import quote
    
    # Compact JSON encoding
    params_json = json.dumps(params, separators=(",", ":"))
    
    # Triple-nested structure
    request = [[[rpc_id, params_json, None, "generic"]]]
    request_json = json.dumps(request, separators=(",", ":"))
    
    return quote(request_json)
```

### Response Decoding

```python
def decode_response(raw: str, rpc_id: str) -> any:
    """Decode batchexecute response."""
    import json
    import re
    
    # Strip anti-XSSI
    if raw.startswith(")]}'"):
        raw = re.sub(r"^\)\]\}'\r?\n", "", raw)
    
    # Parse chunks
    for line in raw.split("\n"):
        try:
            chunk = json.loads(line)
            if chunk[0] == "wrb.fr" and chunk[1] == rpc_id:
                result = chunk[2]
                if isinstance(result, str):
                    return json.loads(result)
                return result
        except:
            continue
    return None
```

---

**End of Network Traffic Analysis Methodology**

---

## Appendix: Captured RPC Formats (2026-01-04)

### Automated Capture Results

The following RPC formats were captured via automated Playwright browser interaction:

#### LIST_NOTEBOOKS (wXbhsf)
```json
[null, 1, null, [2]]
```
**Status**: ✅ Implementation matches

#### CREATE_NOTEBOOK (CCqFvf)
```json
["", null, null, [2], [1, null, null, null, null, null, null, null, null, null, [1]]]
```
**Status**: ✅ Working (implementation uses shorter last param but API accepts it)

#### GET_NOTEBOOK (rLM1Ne)
```json
["notebook_id", null, [2], null, 0]
```
**Status**: ✅ Implementation matches

#### ADD_SOURCE_TEXT (izAoDd)
```json
[
  [[null, ["Title", "Content"], null, 2, null, null, null, null, null, null, 1]],
  "notebook_id",
  [2],
  [1, null, null, null, null, null, null, null, null, null, [1]]
]
```
**Status**: ✅ Working

#### ADD_SOURCE_URL (izAoDd)
```json
[
  [[null, null, null, null, null, null, null, ["url"], null, null, 1]],
  "notebook_id",
  [2],
  [1, null, null, null, null, null, null, null, null, null, [1]]
]
```
**Note**: URL is at position 7 in the source array, text content is at position 1

#### IMPORT_RESEARCH (LBwxtb)
```json
[
  null,
  [1],
  "research_session_id",
  "notebook_id",
  [
    [null, null, ["url", "title"], null, null, null, null, null, null, null, 2],
    // ... more sources to import
  ]
]
```
**Purpose**: Imports research findings as sources into a notebook

#### POLL_STUDIO (gArtLc) - List Artifacts
```json
[[2], "notebook_id", "NOT artifact.status = \"ARTIFACT_STATUS_SUGGESTED\""]
```
**Note**: Browser uses filter string to exclude suggested artifacts

#### VfAZjd - Get Summary
```json
["notebook_id", [2]]
```

#### cFji9 - LIST_MIND_MAPS
```json
["notebook_id"]
```

#### rc3d8d - GET_SOURCE_OVERVIEW (New Discovery)
```json
[
  ["source_id", "source_title"],
  [["title"]]
]
```
**Purpose**: Retrieves source overview/title information

#### v9rmvd - GET_SOURCE_DETAILS (New Discovery)
```json
["source_id"]
```
**Purpose**: Gets detailed source information

#### JFMDGd - Unknown (Notebook-level)
```json
["notebook_id", [2]]
```
**Purpose**: Unknown, called during source operations

### RPC IDs Discovered

#### Confirmed RPCs (Working)

| RPC ID | Constant | Purpose | Params |
|--------|----------|---------|--------|
| `wXbhsf` | LIST_NOTEBOOKS | List all notebooks | `[null, 1, null, [2]]` |
| `CCqFvf` | CREATE_NOTEBOOK | Create new notebook | `["", null, null, [2], [...]]` |
| `rLM1Ne` | GET_NOTEBOOK | Get notebook details | `[notebook_id, null, [2], null, 0]` |
| `s0tc2d` | RENAME_NOTEBOOK | Rename notebook | `[notebook_id, [[null, null, null, [null, title]]]]` |
| `WWINqb` | DELETE_NOTEBOOK | Delete notebook | (needs capture) |
| `izAoDd` | ADD_SOURCE | Add URL/text source | `[[[null, [title, content], null, 2, ...]], notebook_id, [2], [...]]` |
| `VfAZjd` | SUMMARIZE | Get notebook summary | `[notebook_id, [2]]` |
| `gArtLc` | POLL_STUDIO | List/poll artifacts | `[[2], notebook_id, "NOT artifact.status..."]` |
| `AHyHrd` | CREATE_AUDIO | Generate podcast | (needs capture) |
| `R7cb6c` | CREATE_VIDEO | Generate video/slides | (needs capture) |
| `hXya6e` | ACT_ON_SOURCES | FAQ, Study Guide, etc. | (needs capture) |
| `cFji9` | LIST_MIND_MAPS | List saved mind maps | `[notebook_id]` |
| `e3bVqc` | POLL_RESEARCH | Poll research status | `[null, null, notebook_id]` |

#### Supporting RPCs (Auto-triggered)

| RPC ID | Purpose | Params |
|--------|---------|--------|
| `ZwVcOc` | Page initialization/auth | `[null, [1, null, null, ..., [1]]]` |
| `ub2Bae` | Mode/feature flags | `[[2]]` |
| `ozz5Z` | Pagination/infinite scroll | `[[[[null, "1", 627], [...], 1]]]` |
| `hPTbtc` | Unknown (notebook context) | `[[], null, notebook_id, 20]` |
| `sqTeoe` | Unknown (feature check) | `[[2], null, 1]` |
| `khqZz` | Unknown (session/chat context) | `[[], null, null, source_id, 20]` |

#### Source Operations

| RPC ID | Constant | Purpose |
|--------|----------|---------|
| `izAoDd` | ADD_SOURCE | Add URL or text source |
| `tGMBJ` | DELETE_SOURCE | Delete a source |
| `hizoJc` | GET_SOURCE | Get source details |
| `yR9Yof` | CHECK_FRESHNESS | Check source freshness |
| `FLmJqe` | SYNC_DRIVE | Sync Google Drive sources |

#### Research Operations

| RPC ID | Constant | Purpose |
|--------|----------|---------|
| `Ljjv0c` | START_FAST_RESEARCH | Start fast web research |
| `QA9ei` | START_DEEP_RESEARCH | Start deep web research |
| `e3bVqc` | POLL_RESEARCH | Poll research status |
| `LBwxtb` | IMPORT_RESEARCH | Import research findings |

#### Studio/Artifact Operations

| RPC ID | Constant | Purpose |
|--------|----------|---------|
| `AHyHrd` | CREATE_AUDIO | Generate audio overview |
| `VUsiyb` | GET_AUDIO | Get audio artifact |
| `sJDbic` | DELETE_AUDIO | Delete audio artifact |
| `R7cb6c` | CREATE_VIDEO | Generate video/slides |
| `gArtLc` | POLL_STUDIO | Poll artifact status |
| `V5N4be` | DELETE_STUDIO | Delete artifact |
| `xpWGLf` | CREATE_ARTIFACT | Create generic artifact |
| `BnLyuf` | GET_ARTIFACT | Get artifact details |
| `yyryJe` | ACT_ON_SOURCES | Generate FAQ, Guide, Timeline, etc. |
| `CYK0Xb` | SAVE_MIND_MAP | Save mind map |
| `cFji9` | LIST_MIND_MAPS | List saved mind maps |

---

## Automated Capture Tools

Two scripts are available for systematic RPC capture:

### Manual Capture (`scripts/manual_rpc_capture.py`)

Opens a browser with network interception. Perform operations manually and all RPCs are captured:

```bash
cd /Users/blackmyth/src/notion-notebooklm
source .venv/bin/activate
python scripts/manual_rpc_capture.py
```

Output: `captured_rpcs/manual_{timestamp}/`

### Automated Capture (`scripts/systematic_rpc_capture.py`)

Uses notebooklm-tools to automate operations while capturing RPCs:

```bash
# Requires notebooklm-tools dependencies
uv pip install structlog pydantic tenacity typer rich python-dotenv

python scripts/systematic_rpc_capture.py
```

Output: `captured_rpcs/{timestamp}/`

---

### Verification Results (Updated 2026-01-04)

All key methods verified against real API:

#### Core Operations
| Method | Status | Notes |
|--------|--------|-------|
| list_notebooks | ✅ Works | |
| get_notebook | ✅ Works | Returns sources |
| create_notebook | ✅ Works | |
| delete_notebook | ✅ Works | |
| rename_notebook | ✅ Works | Fixed payload format |
| add_source_text | ✅ Works | |
| add_source_url | ✅ Works | |
| get_summary | ✅ Works | |

#### Artifact Generation (R7cb6c)
| Method | Status | Type Code | Notes |
|--------|--------|-----------|-------|
| generate_briefing_doc | ✅ Works | 2 | Returns artifact ID |
| generate_quiz | ✅ Works | 4 (subtype=2) | Returns artifact ID |
| generate_flashcards | ✅ Works | 4 (subtype=1) | Returns artifact ID |
| generate_slides | ✅ Works | 8 | Returns artifact ID |
| generate_infographic | ✅ Works | 7 | Async (returns null) |
| generate_data_table | ✅ Works | 9 | Async (returns null) |

#### Mind Map & Notes
| Method | Status | RPC ID | Notes |
|--------|--------|--------|-------|
| generate_mind_map | ✅ Works | yyryJe | Returns JSON structure |
| list_mind_maps | ✅ Works | cFji9 | |
| create_note | ✅ Works | CYK0Xb | Returns note ID |
| save_note_content | ✅ Works | cYAfTb | |
| delete_note | ✅ Works | AH0mwd | |
| delete_mind_map | ✅ Works | AH0mwd | |

#### Artifact Management
| Method | Status | RPC ID | Notes |
|--------|--------|--------|-------|
| delete_studio_content | ✅ Works | V5N4be | For audio/video/quiz/etc |
| rename_artifact | ✅ Works | rc3d8d | |
| export_artifact | ✅ Works | Krh3pd | |
| poll_studio_status | ✅ Works | gArtLc | |

#### Research
| Method | Status | Notes |
|--------|--------|-------|
| start_research | ✅ Captured | Ljjv0c (fast) / QA9ei (deep) |
| poll_research | ✅ Captured | e3bVqc |
| import_research | ✅ Captured | LBwxtb |

---

## Capture Summary (2026-01-04)

### Total RPCs Captured: 52+

Across multiple automated capture sessions, the following operations were captured:

| Operation | RPCs Captured |
|-----------|---------------|
| navigate_to_notebook | 14 |
| add_source_text | 11 |
| generate_faq | 2 |
| generate_study_guide | 3 |
| generate_timeline | 22 |
| generate_briefing_doc | 7 |
| navigate_home | 4 |

### Newly Discovered RPCs

| RPC ID | Purpose | Discovery |
|--------|---------|-----------|
| `rc3d8d` | Get source overview | Source operations |
| `v9rmvd` | Get source details | Source operations |
| `JFMDGd` | Notebook-level query | Source operations |
| `LBwxtb` | Import research results | Research operations |

### Chat Query Note

Chat queries use a different endpoint (`GenerateFreeFormStreamed`) that streams responses. This is not a standard batchexecute RPC.

---

## Verified RPC Payload Formats (2026-01-04)

### Artifact Generation via R7cb6c

All artifact types use the same RPC ID (`R7cb6c`) with different type codes:

#### Briefing Doc (Type 2)
```json
[[2], "notebook_id", [
  null, null, 2,
  [[[source_id1]], [[source_id2]]],
  null, null, null,
  [null, ["Briefing Doc", "Key insights...", null,
    [[source_id1], [source_id2]], "en", "prompt"]]
]]
```

#### Quiz (Type 4, Subtype 2)
```json
[[2], "notebook_id", [
  null, null, 4,
  [[[source_id1]], [[source_id2]]],
  null, null, null, null, null,
  [null, [2, null, null, null, null, null, null, [2, 2]]]
]]
```

#### Flashcards (Type 4, Subtype 1)
```json
[[2], "notebook_id", [
  null, null, 4,
  [[[source_id1]], [[source_id2]]],
  null, null, null, null, null,
  [null, [1, null, null, null, null, null, [2, 2]]]
]]
```

#### Slides (Type 8)
```json
[[2], "notebook_id", [
  null, null, 8,
  [[[source_id1]], [[source_id2]]],
  null, null, null, null, null, null,
  null, null, null, null, null, null, []
]]
```

#### Infographic (Type 7)
```json
[[2], "notebook_id", [null, null, 7, [[[source_id1]], [[source_id2]]]]]
```

#### Data Table (Type 9)
```json
[[2], "notebook_id", [null, null, 9, [[[source_id1]], [[source_id2]]]]]
```

### Mind Map Generation (yyryJe)
```json
[
  [[[source_id1]], [[source_id2]]],
  null, null, null, null,
  ["interactive_mindmap", [["[CONTEXT]", ""]], ""],
  null,
  [2, null, [1]]
]
```

### Note Operations

#### Create Note (CYK0Xb)
```json
["notebook_id", "", [1], null, "New Note"]
```

#### Save Note Content (cYAfTb)
```json
["notebook_id", "note_id", [[["<p>content</p>", "title", [], 0]]]]
```

#### Delete Note/Mind Map (AH0mwd)
```json
["notebook_id", null, ["artifact_id"]]
```

### Artifact Management

#### Delete Studio Content (V5N4be)
```json
[[2], "artifact_id"]
```

#### Rename Artifact (rc3d8d)
```json
[["artifact_id", "new_title"], [["title"]]]
```

#### Export Artifact (Krh3pd)
```json
[null, "artifact_id", "content_or_null", "title", export_type]
```
- export_type: 1 = Google Docs, 2 = Google Sheets

### Source ID Nesting Patterns

Different operations require different nesting levels:

| Operation | Nesting | Example |
|-----------|---------|---------|
| R7cb6c artifacts | Triple | `[[[id]]]` per source |
| yyryJe (mind map) | Triple | `[[[id]]]` per source |
| Briefing doc metadata | Double | `[[id]]` per source |
| Simple operations | Single | `[id]` |

---

## RPC Method Reference

### Complete RPC ID List

| RPC ID | Constant | Purpose | Verified |
|--------|----------|---------|----------|
| `wXbhsf` | LIST_NOTEBOOKS | List notebooks | ✅ |
| `CCqFvf` | CREATE_NOTEBOOK | Create notebook | ✅ |
| `rLM1Ne` | GET_NOTEBOOK | Get notebook | ✅ |
| `s0tc2d` | RENAME_NOTEBOOK | Rename notebook | ✅ |
| `WWINqb` | DELETE_NOTEBOOK | Delete notebook | ✅ |
| `izAoDd` | ADD_SOURCE | Add source | ✅ |
| `tGMBJ` | DELETE_SOURCE | Delete source | ✅ |
| `hizoJc` | GET_SOURCE | Get source | ✅ |
| `VfAZjd` | SUMMARIZE | Get summary | ✅ |
| `R7cb6c` | CREATE_VIDEO | Video/Slides/Quiz/etc | ✅ |
| `yyryJe` | ACT_ON_SOURCES | Mind map/FAQ/etc | ✅ |
| `gArtLc` | POLL_STUDIO | Poll/list artifacts | ✅ |
| `V5N4be` | DELETE_STUDIO | Delete artifacts | ✅ |
| `CYK0Xb` | SAVE_MIND_MAP | Create note/save map | ✅ |
| `cYAfTb` | SAVE_NOTE_CONTENT | Save note content | ✅ |
| `AH0mwd` | DELETE_NOTE_MINDMAP | Delete note/map | ✅ |
| `rc3d8d` | RENAME_ARTIFACT | Rename artifact | ✅ |
| `Krh3pd` | EXPORT_ARTIFACT | Export to Docs/Sheets | ✅ |
| `cFji9` | LIST_MIND_MAPS | List mind maps | ✅ |
| `hPTbtc` | GET_CONVERSATION_HISTORY | Chat history | Captured |
| `AHyHrd` | CREATE_AUDIO | Generate audio | Partial |
| `Ljjv0c` | START_FAST_RESEARCH | Fast research | Captured |
| `QA9ei` | START_DEEP_RESEARCH | Deep research | Captured |
| `e3bVqc` | POLL_RESEARCH | Poll research | ✅ |
| `LBwxtb` | IMPORT_RESEARCH | Import research | Captured |
