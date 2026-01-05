"""Integration tests for domain services."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from notebooklm.services import (
    NotebookService,
    SourceService,
    ArtifactService,
    Notebook,
    Source,
    ArtifactStatus,
)
from notebooklm.auth import AuthTokens


@pytest.fixture
def auth_tokens():
    return AuthTokens(
        cookies={
            "SID": "test_sid",
            "HSID": "test_hsid",
            "SSID": "test_ssid",
            "APISID": "test_apisid",
            "SAPISID": "test_sapisid",
        },
        csrf_token="test_csrf",
        session_id="test_session",
    )


class TestNotebookService:
    @pytest.mark.asyncio
    async def test_list_notebooks(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.list_notebooks.return_value = [
            [
                "First Notebook",
                [],
                "nb_001",
                "📘",
                None,
                [None, None, None, None, None, [1704067200, 0]],
            ],
            [
                "Second Notebook",
                [],
                "nb_002",
                "📚",
                None,
                [None, None, None, None, None, [1704153600, 0]],
            ],
        ]

        service = NotebookService(mock_client)
        notebooks = await service.list()

        assert len(notebooks) == 2
        assert notebooks[0].id == "nb_001"
        assert notebooks[0].title == "First Notebook"

    @pytest.mark.asyncio
    async def test_create_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.create_notebook.return_value = [
            "My Research",
            [],
            "nb_new",
            "📓",
            None,
            [None, None, None, None, None, [1704067200, 0]],
        ]

        service = NotebookService(mock_client)
        notebook = await service.create("My Research")

        assert notebook.id == "nb_new"
        assert notebook.title == "My Research"
        mock_client.create_notebook.assert_called_once_with("My Research")

    @pytest.mark.asyncio
    async def test_get_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_notebook.return_value = [
            "Test Notebook",
            [["src_001", "Source 1"], ["src_002", "Source 2"]],
            "nb_001",
        ]

        service = NotebookService(mock_client)
        notebook = await service.get("nb_001")

        assert notebook.id == "nb_001"
        assert notebook.title == "Test Notebook"

    @pytest.mark.asyncio
    async def test_delete_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.delete_notebook.return_value = [True]

        service = NotebookService(mock_client)
        result = await service.delete("nb_001")

        assert result is True
        mock_client.delete_notebook.assert_called_once_with("nb_001")

    @pytest.mark.asyncio
    async def test_rename_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.rename_notebook.return_value = [
            "Renamed Notebook",
            [],
            "nb_001",
            "📘",
            None,
            [None, None, None, None, None, [1704067200, 0]],
        ]

        service = NotebookService(mock_client)
        notebook = await service.rename("nb_001", "Renamed Notebook")

        assert notebook.id == "nb_001"
        assert notebook.title == "Renamed Notebook"
        mock_client.rename_notebook.assert_called_once_with(
            "nb_001", "Renamed Notebook"
        )


class TestSourceService:
    @pytest.mark.asyncio
    async def test_add_url(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.add_source_url.return_value = [
            [
                [
                    ["src_001"],
                    "Example Site",
                    [None, 11, None, None, 5, None, 1, ["https://example.com"]],
                    [None, 2],
                ]
            ]
        ]

        service = SourceService(mock_client)
        source = await service.add_url("nb_001", "https://example.com")

        assert source.id == "src_001"
        assert source.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_add_text(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.add_source_text.return_value = [
            [[["src_002"], "My Notes", [None, 11], [None, 2]]]
        ]

        service = SourceService(mock_client)
        source = await service.add_text("nb_001", "My Notes", "Content here")

        assert source.id == "src_002"
        assert source.title == "My Notes"

    @pytest.mark.asyncio
    async def test_get_source(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_source.return_value = [
            [[["src_001"], "Source Title", [None, 11], [None, 2]]]
        ]

        service = SourceService(mock_client)
        source = await service.get("nb_001", "src_001")

        assert source.id == "src_001"
        assert source.title == "Source Title"
        mock_client.get_source.assert_called_once_with("nb_001", "src_001")

    @pytest.mark.asyncio
    async def test_delete_source(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.delete_source.return_value = [True]

        service = SourceService(mock_client)
        result = await service.delete("nb_001", "src_001")

        assert result is True
        mock_client.delete_source.assert_called_once_with("nb_001", "src_001")


class TestArtifactService:
    @pytest.mark.asyncio
    async def test_generate_audio(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_audio.return_value = ["task_001", "pending"]

        service = ArtifactService(mock_client)
        status = await service.generate_audio("nb_001")

        assert status.task_id == "task_001"
        assert status.status == "pending"

    @pytest.mark.asyncio
    async def test_generate_audio_with_instructions(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_audio.return_value = ["task_002", "pending"]

        service = ArtifactService(mock_client)
        await service.generate_audio("nb_001", host_instructions="Be casual")

        mock_client.generate_audio.assert_called_once_with(
            "nb_001", host_instructions="Be casual"
        )

    @pytest.mark.asyncio
    async def test_generate_slides(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_slides.return_value = ["task_003", "pending"]

        service = ArtifactService(mock_client)
        status = await service.generate_slides("nb_001")

        assert status.task_id == "task_003"

    @pytest.mark.asyncio
    async def test_poll_status(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.poll_studio_status.return_value = [
            "task_001",
            "completed",
            "https://storage.googleapis.com/audio.mp3",
        ]

        service = ArtifactService(mock_client)
        status = await service.poll_status("nb_001", "task_001")

        assert status.status == "completed"
        assert status.url == "https://storage.googleapis.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.poll_studio_status.side_effect = [
            ["task_001", "pending", None],
            ["task_001", "processing", None],
            ["task_001", "completed", "https://result.mp3"],
        ]

        service = ArtifactService(mock_client)
        status = await service.wait_for_completion(
            "nb_001", "task_001", poll_interval=0.01
        )

        assert status.status == "completed"
        assert mock_client.poll_studio_status.call_count == 3
