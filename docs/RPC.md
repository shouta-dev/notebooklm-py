# NotebookLM RPC Documentation

NotebookLM uses Google's `batchexecute` protocol. This document describes the reverse-engineered RPC layer.

## Protocol Overview

- **Endpoint**: `https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute`
- **Method**: POST
- **Format**: `application/x-www-form-urlencoded`
- **Body**: `f.req=[[[method_id, params_json, None, "generic"]]]&at=CSRF_TOKEN`

## RPC Method IDs

These obfuscated IDs map to specific operations:

| Method ID | Enum Name | Purpose |
|-----------|-----------|---------|
| `wXbhsf` | `LIST_NOTEBOOKS` | Get all notebooks for the user |
| `CCqFvf` | `CREATE_NOTEBOOK` | Create a new project |
| `rLM1Ne` | `GET_NOTEBOOK` | Fetch notebook structure and sources |
| `s0tc2d` | `RENAME_NOTEBOOK` | Change notebook title |
| `WWINqb` | `DELETE_NOTEBOOK` | Remove a notebook |
| `izAoDd` | `ADD_SOURCE` | Add URL or text source |
| `AHyHrd` | `CREATE_AUDIO` | Start audio overview generation |
| `R7cb6c` | `CREATE_VIDEO` | Start video overview generation |
| `gArtLc` | `POLL_STUDIO` | Poll status for artifact generation |
| `QA9ei` | `START_DEEP_RESEARCH` | Trigger deep research agent |

## Payload Structure

Most requests follow a nested list structure. For example, creating a notebook:

```python
# params = [title, None, None, None, None]
# RPC Request = [[["CCqFvf", '["My Notebook", null, null, null, null]', null, "generic"]]]
```

## Response Format

Responses are chunked and prefixed with `)]}'`.
Example chunk:
```
123
[[["wXbhsf",[[["notebook-id","Title",...]]],null,"generic"]]]
```

The library strips the prefix and parses the JSON to extract results based on the matching RPC ID.

## Adding New RPC Methods

1. **Capture Traffic**: Use Browser DevTools (Network tab) and filter by `batchexecute`.
2. **Identify ID**: Look for the `rpcids` parameter in the URL.
3. **Analyze Payload**: Look at the `f.req` parameter. It's often URL-encoded JSON.
4. **Update `RPCMethod`**: Add the new ID to `src/notebooklm/rpc/types.py`.
5. **Implement in Client**: Add a new method to `NotebookLMClient` using `self._rpc_call`.
