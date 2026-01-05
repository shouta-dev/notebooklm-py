# Known Issues and Limitations

## Resolved Issues ✅

### Async Artifact Generation (Fixed in v0.1.0)

**Previously:** Artifact generation methods returned `None` instead of task/artifact metadata.

**Resolution:** The issue was a parameter order bug in our implementation, not an API limitation. We had swapped `format_code` and `length_code` positions in the audio_options array.

**Current Behavior:** All artifact generation methods now return a dictionary with metadata:
```python
{
    "artifact_id": str,       # Unique identifier
    "status": str,            # "in_progress" or "completed"  
    "title": Optional[str],   # Artifact title
    "create_time": Optional[str]  # ISO timestamp
}
```

**Example:**
```python
result = await client.generate_audio(notebook_id)
print(f"Artifact ID: {result['artifact_id']}")
print(f"Status: {result['status']}")
```

---

## Technical Limitations

### Private API / RPC Stability
This library uses reverse-engineered private APIs. Google does not officially support these endpoints, and they may change without notice. If IDs like `wXbhsf` change, functionality will break until the library is updated.

### Authentication Expiry
Cookies saved via `notebooklm login` eventually expire. If you receive "Unauthorized" or "Session Expired" errors, you must re-run the login command.

### Rate Limiting
Automating a private API can trigger Google's anti-abuse mechanisms. Avoid making hundreds of requests in a short period.

## Specific Feature Issues

### `list_artifacts_alt` API
The alternative artifact listing method (`LfTXoe`) sometimes returns empty results or inconsistent structures compared to the primary `gArtLc` method.

### PDF Native Upload
The library currently implements PDF support by extracting text locally and uploading it as a "Text Source". This avoids complex multipart PDF uploads to Google's internal storage but may lose some formatting compared to native PDF uploads.

### Stream Parsing
The `query` endpoint returns a complex stream of chunks. The library uses heuristics to identify the final answer chunk. In some edge cases (e.g., very long responses), the parser might miss parts of the response.
