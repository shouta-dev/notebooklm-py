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

    File uploads now use the same Gemini Notebook host as normal RPCs. Keep an
    independent override because this is an undocumented endpoint, but do not
    silently fall back to the legacy host when Google rejects the configured
    route.
    """
    return os.environ.get("NOTEBOOKLM_UPLOAD_BASE_URL", get_base_url()).rstrip("/")


def get_base_urls() -> list[str]:
    primary = get_base_url()
    urls = [primary, LEGACY_BASE_URL]
    return list(dict.fromkeys(urls))
