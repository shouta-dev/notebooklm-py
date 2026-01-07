# Troubleshooting

Common issues, known limitations, and workarounds for `notebooklm-py`.

## Common Errors

### Authentication Errors

#### "Unauthorized" or redirect to login page

**Cause:** Session expired or cookies invalid.

**Solution:**
```bash
notebooklm login
```

#### "CSRF token missing" or "SNlM0e not found"

**Cause:** CSRF token expired or couldn't be extracted.

**Solution:**
```python
# In Python
await client.refresh_auth()
```
Or re-run `notebooklm login`.

#### Browser opens but login fails

**Cause:** Google detecting automation and blocking login.

**Solution:**
1. Delete the browser profile: `rm -rf ~/.notebooklm/browser_profile/`
2. Run `notebooklm login` again
3. Complete any CAPTCHA or security challenges Google presents
4. Ensure you're using a real mouse/keyboard (not pasting credentials via script)

### RPC Errors

#### "RPCError: No result found for RPC ID: XyZ123"

**Cause:** The RPC method ID may have changed (Google updates these periodically), or:
- Rate limiting from Google
- Account quota exceeded
- API restrictions

**Diagnosis:**
```bash
# Enable debug mode to see what RPC IDs the server returns
NOTEBOOKLM_DEBUG_RPC=1 notebooklm <your-command>
```

This will show output like:
```
DEBUG: Looking for RPC ID: Ljjv0c
DEBUG: Found RPC IDs in response: ['NewId123']
```

If the IDs don't match, the method ID has changed. Report the new ID in a GitHub issue.

**Workaround:**
- Wait 5-10 minutes and retry
- Try with fewer sources selected
- Reduce generation frequency

#### "RPCError: [3]" or "UserDisplayableError"

**Cause:** Google API returned an error, typically:
- Invalid parameters
- Resource not found
- Rate limiting

**Solution:**
- Check that notebook/source IDs are valid
- Add delays between operations (see Rate Limiting section)

### Generation Failures

#### Audio/Video generation returns None

**Cause:** Known issue with artifact generation under heavy load or rate limiting.

**Workaround:**
```bash
# Use --wait to see if it eventually succeeds
notebooklm generate audio --wait

# Or poll manually
notebooklm artifact poll <task_id>
```

#### Mind map or data table "generates" but doesn't appear

**Cause:** Generation may silently fail without error.

**Solution:**
- Wait 60 seconds and check `artifact list`
- Try regenerating with different/fewer sources

### File Upload Issues

#### Text/Markdown files upload but return None

**Cause:** Known issue with native text file uploads.

**Workaround:** Use `add_text` instead:
```bash
# Instead of: notebooklm source add ./notes.txt
# Do:
notebooklm source add "$(cat ./notes.txt)"
```

Or in Python:
```python
content = Path("notes.txt").read_text()
await client.sources.add_text(nb_id, "My Notes", content)
```

#### Large files time out

**Cause:** Files over ~20MB may exceed upload timeout.

**Solution:** Split large documents or use text extraction locally.

---

## Known Limitations

### Rate Limiting

Google enforces strict rate limits on the batchexecute endpoint.

**Symptoms:**
- RPC calls return `None`
- `RPCError` with ID `R7cb6c`
- `UserDisplayableError` with code `[3]`

**Best Practices:**
```python
import asyncio

# Add delays between intensive operations
for url in urls:
    await client.sources.add_url(nb_id, url)
    await asyncio.sleep(2)  # 2 second delay

# Use exponential backoff on failures
async def retry_with_backoff(coro, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await coro
        except RPCError:
            wait = 2 ** attempt  # 1, 2, 4 seconds
            await asyncio.sleep(wait)
    raise Exception("Max retries exceeded")
```

### Quota Restrictions

Some features have daily/hourly quotas:
- **Audio Overviews:** Limited generations per day per account
- **Video Overviews:** More restricted than audio
- **Deep Research:** Consumes significant backend resources

### Session Expiration

Sessions expire based on Google's internal policies:
- Typically last days to weeks
- Security events can trigger earlier expiration
- Heavy API usage may trigger earlier expiration

### Non-Functional RPC Methods

Some discovered RPC endpoints don't work as expected:

| RPC ID | Issue | Workaround |
|--------|-------|------------|
| `BnLyuf` (GET_ARTIFACT) | Returns 400 | Use `list` and filter |
| `hizoJc` (GET_SOURCE) | Unreliable | Get from notebook metadata |

### Download Requirements

Artifact downloads (audio, video, images) require Playwright because:
- URLs use Google's `lh3.googleusercontent.com` domain
- Cross-domain cookie authentication is complex
- Standard HTTP clients can't handle the redirect chain

**Solution:** Ensure browser support is installed:
```bash
pip install "notebooklm-client[browser]"
playwright install chromium
```

### URL Expiry

Download URLs for audio/video are temporary:
- Expire within hours
- Always fetch fresh URLs before downloading:

```python
# Get fresh artifact list before download
artifacts = await client.artifacts.list(nb_id)
audio = next(a for a in artifacts if a.artifact_type == "audio")
# Use audio.url immediately
```

---

## Platform-Specific Issues

### Linux

**Playwright missing dependencies:**
```bash
playwright install-deps chromium
```

**No display available (headless server):**
- Browser login requires a display
- Authenticate on a machine with GUI, then copy `storage_state.json`

### macOS

**Chromium not opening:**
```bash
# Re-install Playwright browsers
playwright install chromium
```

**Security warning about Chromium:**
- Allow in System Preferences → Security & Privacy

### Windows

**Path issues:**
- Use forward slashes or raw strings: `r"C:\path\to\file"`
- Ensure `~` expansion works: use `Path.home()` in Python

### WSL

**Browser opens in Windows, not WSL:**
- This is expected behavior
- Storage file is saved in WSL filesystem

---

## Debugging Tips

### Enable Verbose Output

Check what's happening under the hood:

```bash
# See full error messages
notebooklm list 2>&1

# Verify auth is working
notebooklm status
```

### Check Storage State

Verify your session file is valid:

```bash
# Check file exists and has content
cat ~/.notebooklm/storage_state.json | python -m json.tool | head -20
```

### Test Basic Operations

Start simple to isolate issues:

```bash
# 1. Can you list notebooks?
notebooklm list

# 2. Can you create a notebook?
notebooklm create "Test"

# 3. Can you add a source?
notebooklm source add "https://example.com"
```

### Network Debugging

If you suspect network issues:

```python
import httpx

# Test basic connectivity
async with httpx.AsyncClient() as client:
    r = await client.get("https://notebooklm.google.com")
    print(r.status_code)  # Should be 200 or 302
```

---

## Getting Help

1. Check this troubleshooting guide
2. Search [existing issues](https://github.com/user/notebooklm-client/issues)
3. Open a new issue with:
   - Command/code that failed
   - Full error message
   - Python version (`python --version`)
   - Library version (`notebooklm --version`)
   - Operating system
