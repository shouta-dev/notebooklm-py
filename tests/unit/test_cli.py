"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, patch, MagicMock

from notebooklm.notebooklm_cli import cli, main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_auth():
    with patch("notebooklm.notebooklm_cli.load_auth_from_storage") as mock:
        mock.return_value = {
            "SID": "test",
            "HSID": "test",
            "SSID": "test",
            "APISID": "test",
            "SAPISID": "test",
        }
        yield mock


class TestCLIBasics:
    def test_cli_exists(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "NotebookLM" in result.output

    def test_version_flag(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestListNotebooks:
    def test_list_command_exists(self, runner):
        result = runner.invoke(cli, ["list", "--help"])
        assert result.exit_code == 0

    def test_list_notebooks(self, runner, mock_auth):
        with patch("notebooklm.notebooklm_cli.NotebookLMClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.list_notebooks = AsyncMock(
                return_value=[
                    ["nb_001", "First Notebook", None, None, 1704067200000],
                    ["nb_002", "Second Notebook", None, None, 1704153600000],
                ]
            )
            mock_client_cls.return_value = mock_client

            with patch("notebooklm.notebooklm_cli.fetch_tokens") as mock_fetch:
                mock_fetch.return_value = ("csrf", "session")
                result = runner.invoke(cli, ["list"])

            assert result.exit_code == 0
            assert "First Notebook" in result.output or "nb_001" in result.output


class TestCreateNotebook:
    def test_create_command_exists(self, runner):
        result = runner.invoke(cli, ["create", "--help"])
        assert result.exit_code == 0
        assert "TITLE" in result.output

    def test_create_notebook(self, runner, mock_auth):
        with patch("notebooklm.notebooklm_cli.NotebookLMClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.create_notebook = AsyncMock(
                return_value=["nb_new", "My Research", None, None, 1704067200000]
            )
            mock_client_cls.return_value = mock_client

            with patch("notebooklm.notebooklm_cli.fetch_tokens") as mock_fetch:
                mock_fetch.return_value = ("csrf", "session")
                result = runner.invoke(cli, ["create", "My Research"])

            assert result.exit_code == 0


class TestAddSource:
    def test_add_url_command_exists(self, runner):
        result = runner.invoke(cli, ["add-url", "--help"])
        assert result.exit_code == 0
        assert "NOTEBOOK_ID" in result.output
        assert "URL" in result.output

    def test_add_text_command_exists(self, runner):
        result = runner.invoke(cli, ["add-text", "--help"])
        assert result.exit_code == 0


class TestGenerateAudio:
    def test_audio_command_exists(self, runner):
        result = runner.invoke(cli, ["audio", "--help"])
        assert result.exit_code == 0
        assert "NOTEBOOK_ID" in result.output

    def test_audio_with_instructions_option(self, runner):
        result = runner.invoke(cli, ["audio", "--help"])
        assert "--instructions" in result.output or "-i" in result.output
