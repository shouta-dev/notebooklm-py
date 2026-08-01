"""NotebookLM/Gemini Notebook domain constants."""

import os

DEFAULT_BASE_URL = "https://notebook.google.com"
LEGACY_BASE_URL = "https://notebooklm.google.com"


def get_base_url() -> str:
    """Return the preferred NotebookLM base URL.

    Google is migrating NotebookLM to Gemini Notebook on notebook.google.com.
    Keep this configurable so operations can switch domains without code edits.
    """
    return os.environ.get("NOTEBOOKLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_legacy_base_url() -> str:
    return LEGACY_BASE_URL


def get_upload_base_url() -> str:
    """Return the host used by the resumable upload endpoint.

    Gemini Notebook currently serves the app on notebook.google.com, but file
    uploads still succeed against the legacy NotebookLM host. Keep upload
    routing separate from normal RPC routing so create/list/ask can follow the
    app host without breaking source uploads.
    """
    return os.environ.get("NOTEBOOKLM_UPLOAD_BASE_URL", LEGACY_BASE_URL).rstrip("/")


def get_base_urls() -> list[str]:
    primary = get_base_url()
    urls = [primary, LEGACY_BASE_URL]
    return list(dict.fromkeys(urls))
