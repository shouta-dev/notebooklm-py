"""Unit tests for CLI source add-files command."""

import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from notebooklm.cli.source import source
from notebooklm.types import Source

# Get the actual module object (not the Click group)
_source_mod = importlib.import_module("notebooklm.cli.source")


@pytest.fixture
def runner():
    return CliRunner()


class TestSourceAddFiles:
    """Tests for source add-files CLI command."""

    def test_add_files_requires_files(self, runner):
        """引数なしでエラー"""
        result = runner.invoke(source, ["add-files"])
        assert result.exit_code != 0

    def test_add_files_nonexistent_file(self, runner):
        """存在しないファイルでエラー"""
        result = runner.invoke(source, ["add-files", "/nonexistent/file.md", "-n", "nb-123"])
        assert result.exit_code != 0

    def test_add_files_json_output(self, runner, tmp_path):
        """--json でJSON出力"""
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("content a")
        f2.write_text("content b")

        mock_auth = MagicMock()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.sources = AsyncMock()
        mock_client.sources.close = AsyncMock()
        mock_client.sources.add_files = AsyncMock(
            return_value=[
                Source(id="s1", title="a.md", _type_code=None),
                Source(id="s2", title="b.md", _type_code=None),
            ]
        )

        with (
            patch.object(_source_mod, "NotebookLMClient", return_value=mock_client),
            patch("notebooklm.cli.helpers.get_auth_tokens", return_value=mock_auth),
            patch.object(_source_mod, "resolve_notebook_id", new_callable=AsyncMock, return_value="nb-123"),
        ):
            result = runner.invoke(
                source,
                ["add-files", str(f1), str(f2), "-n", "nb-123", "--json"],
            )

        assert result.exit_code == 0 or "files_uploaded" in result.output
