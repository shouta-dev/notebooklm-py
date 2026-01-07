# Configuration

This guide covers storage locations, environment settings, and configuration options for `notebooklm-py`.

## File Locations

All data is stored under `~/.notebooklm/` by default:

```
~/.notebooklm/
├── storage_state.json    # Authentication cookies and session
├── context.json          # CLI context (active notebook, conversation)
└── browser_profile/      # Persistent Chromium profile
```

### Storage State (`storage_state.json`)

Contains the authentication data extracted from your browser session:

```json
{
  "cookies": [
    {
      "name": "SID",
      "value": "...",
      "domain": ".google.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true,
      "sameSite": "Lax"
    },
    ...
  ],
  "origins": []
}
```

**Required cookies:** `SID`, `HSID`, `SSID`, `APISID`, `SAPISID`, `__Secure-1PSID`, `__Secure-3PSID`

**Override location:**
```bash
notebooklm --storage /path/to/storage_state.json list
```

### Context File (`context.json`)

Stores the current CLI context (active notebook and conversation):

```json
{
  "notebook_id": "abc123def456",
  "conversation_id": "conv789"
}
```

This file is managed automatically by `notebooklm use` and `notebooklm clear`.

### Browser Profile (`browser_profile/`)

A persistent Chromium user data directory used during `notebooklm login`.

**Why persistent?** Google blocks automated login attempts. A persistent profile makes the browser appear as a regular user installation, avoiding bot detection.

**To reset:** Delete the `browser_profile/` directory and run `notebooklm login` again.

## CLI Options

### Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--storage PATH` | Path to storage_state.json | `~/.notebooklm/storage_state.json` |
| `--version` | Show version | - |
| `--help` | Show help | - |

### Example: Custom Storage Location

```bash
# Use a different storage file
notebooklm --storage ./my-session.json list

# Or set for all commands in a session
export NOTEBOOKLM_STORAGE=./my-session.json
notebooklm list
```

## Python API Configuration

### Default Initialization

```python
from notebooklm import NotebookLMClient

# Uses ~/.notebooklm/storage_state.json
async with await NotebookLMClient.from_storage() as client:
    ...
```

### Custom Storage Path

```python
from pathlib import Path
from notebooklm import NotebookLMClient

# Specify a different storage file
async with await NotebookLMClient.from_storage(
    path=Path("./custom-storage.json")
) as client:
    ...
```

### Manual Authentication

```python
from notebooklm import NotebookLMClient, AuthTokens

# Provide tokens directly
auth = AuthTokens(
    cookies={"SID": "...", "HSID": "...", ...},
    csrf_token="SNlM0e_value",
    session_id="FdrFJe_value"
)

async with NotebookLMClient(auth) as client:
    ...
```

## Session Management

### Session Lifetime

Authentication sessions are tied to Google's cookie expiration:
- Sessions typically last several days to weeks
- Google may invalidate sessions for security reasons
- Rate limiting or suspicious activity can trigger earlier expiration

### Refreshing Sessions

If your session expires:

```bash
# Re-authenticate
notebooklm login
```

### Multiple Accounts

To use multiple Google accounts:

```bash
# Account 1
notebooklm --storage ~/.notebooklm/account1.json login
notebooklm --storage ~/.notebooklm/account1.json list

# Account 2
notebooklm --storage ~/.notebooklm/account2.json login
notebooklm --storage ~/.notebooklm/account2.json list
```

## Debugging

### Enable Verbose Output

Some commands support verbose output via Rich console:

```bash
# Most errors are printed to stderr with details
notebooklm list 2>&1 | cat
```

### Check Authentication

Verify your session is working:

```bash
# Should list notebooks or show empty list
notebooklm list

# If you see "Unauthorized" or redirect errors, re-login
notebooklm login
```

### Network Issues

The CLI uses `httpx` for HTTP requests. Common issues:

- **Timeout**: Google's API can be slow; large operations may time out
- **SSL errors**: Ensure your system certificates are up to date
- **Proxy**: Set standard environment variables (`HTTP_PROXY`, `HTTPS_PROXY`) if needed

## Platform Notes

### macOS

Works out of the box. Chromium is downloaded automatically by Playwright.

### Linux

```bash
# Install Playwright dependencies
playwright install-deps chromium

# Then install Chromium
playwright install chromium
```

### Windows

Works with PowerShell or CMD. Use backslashes for paths:

```powershell
notebooklm --storage C:\Users\Name\.notebooklm\storage_state.json list
```

### WSL

Browser login opens in the Windows host browser. The storage file is saved in the WSL filesystem.

### Headless Environments (CI/CD)

Browser login requires a display. For CI/CD:

1. Authenticate locally and copy `storage_state.json` to your CI environment
2. Use secrets management to inject the storage file
3. Note: Sessions expire, so this approach requires periodic refresh

```yaml
# GitHub Actions example
- name: Setup NotebookLM auth
  run: echo "${{ secrets.NOTEBOOKLM_STORAGE }}" > ~/.notebooklm/storage_state.json
```
