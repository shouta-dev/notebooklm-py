"""Shared fixtures for CLI unit tests."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_auth():
    """Mock authentication for CLI commands.

    After CLI refactoring, auth is loaded via cli.helpers module.
    We patch both the main CLI and the helpers module for full coverage.
    """
    with patch("notebooklm.cli.helpers.load_auth_from_storage") as mock:
        mock.return_value = {
            "SID": "test",
            "HSID": "test",
            "SSID": "test",
            "APISID": "test",
            "SAPISID": "test",
        }
        yield mock


@pytest.fixture
def mock_fetch_tokens():
    """Mock fetch_tokens for CLI commands.

    After CLI refactoring, fetch_tokens is called via cli.helpers module.
    """
    with patch("notebooklm.cli.helpers.fetch_tokens") as mock:
        mock.return_value = ("csrf_token", "session_id")
        yield mock


def create_mock_client():
    """Helper to create a properly configured mock client.

    Returns a MagicMock configured as an async context manager
    that can be used with `async with NotebookLMClient(...) as client:`.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def patch_client_for_module(module_path: str):
    """Create a context manager that patches NotebookLMClient in the given module.

    Args:
        module_path: The module name within notebooklm.cli (e.g., "source", "artifact")

    Returns:
        A patch context manager for NotebookLMClient

    Example:
        with patch_client_for_module("source") as mock_cls:
            mock_client = create_mock_client()
            mock_cls.return_value = mock_client
            # ... run test
    """
    return patch(f"notebooklm.cli.{module_path}.NotebookLMClient")


def patch_main_cli_client():
    """Create a context manager that patches NotebookLMClient in the main CLI module.

    Use this for testing notebook commands which are now top-level in notebooklm_cli.py.

    Returns:
        A patch context manager for NotebookLMClient

    Example:
        with patch_main_cli_client() as mock_cls:
            mock_client = create_mock_client()
            mock_cls.return_value = mock_client
            # ... run test
    """
    return patch("notebooklm.notebooklm_cli.NotebookLMClient")


@pytest.fixture
def mock_context_file(tmp_path):
    """Provide a temporary context file for testing context commands."""
    context_file = tmp_path / "context.json"
    with patch("notebooklm.cli.helpers.CONTEXT_FILE", context_file):
        yield context_file
