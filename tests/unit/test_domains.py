"""Tests for NotebookLM domain resolution."""

from unittest.mock import patch

from notebooklm._domains import get_base_url, get_upload_base_url


def test_upload_base_url_defaults_to_current_app_host():
    with patch.dict("os.environ", {}, clear=True):
        assert get_base_url() == "https://notebook.google.com"
        assert get_upload_base_url() == "https://notebook.google.com"


def test_upload_base_url_can_be_overridden_independently():
    with patch.dict(
        "os.environ",
        {
            "NOTEBOOKLM_BASE_URL": "https://notebook.google.com",
            "NOTEBOOKLM_UPLOAD_BASE_URL": "https://notebooklm.google.com/",
        },
        clear=True,
    ):
        assert get_base_url() == "https://notebook.google.com"
        assert get_upload_base_url() == "https://notebooklm.google.com"
