"""Integration tests for NotebookLM API client."""

import pytest
import json
from pytest_httpx import HTTPXMock

from notebooklm.api_client import NotebookLMClient
from notebooklm.auth import AuthTokens
from notebooklm.rpc import BATCHEXECUTE_URL


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
        csrf_token="test_csrf_token",
        session_id="test_session_id",
    )


class TestClientInitialization:
    @pytest.mark.asyncio
    async def test_client_initialization(self, auth_tokens):
        async with NotebookLMClient(auth_tokens) as client:
            assert client.auth == auth_tokens
            assert client._http_client is not None

    @pytest.mark.asyncio
    async def test_client_context_manager_closes(self, auth_tokens):
        async with NotebookLMClient(auth_tokens) as client:
            http = client._http_client
        assert client._http_client is None

    @pytest.mark.asyncio
    async def test_client_raises_if_not_initialized(self, auth_tokens):
        client = NotebookLMClient(auth_tokens)
        with pytest.raises(RuntimeError, match="not initialized"):
            await client.list_notebooks()


class TestListNotebooks:
    @pytest.mark.asyncio
    async def test_list_notebooks_returns_data(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.list_notebooks()

        assert len(result) == 2
        assert result[0][0] == "My First Notebook"
        assert result[0][2] == "nb_001"

    @pytest.mark.asyncio
    async def test_list_notebooks_request_format(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.list_notebooks()

        request = httpx_mock.get_request()
        assert request.method == "POST"
        assert "wXbhsf" in str(request.url)
        assert b"f.req=" in request.content

    @pytest.mark.asyncio
    async def test_request_includes_cookies(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.list_notebooks()

        request = httpx_mock.get_request()
        cookie_header = request.headers.get("cookie", "")
        assert "SID=test_sid" in cookie_header
        assert "HSID=test_hsid" in cookie_header

    @pytest.mark.asyncio
    async def test_request_includes_csrf(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.list_notebooks()

        request = httpx_mock.get_request()
        body = request.content.decode()
        assert "at=test_csrf_token" in body


class TestCreateNotebook:
    @pytest.mark.asyncio
    async def test_create_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("CCqFvf", ["new_nb_id", "My Notebook"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.create_notebook("My Notebook")

        assert result[0] == "new_nb_id"

    @pytest.mark.asyncio
    async def test_create_notebook_request_contains_title(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("CCqFvf", ["id", "title"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.create_notebook("Test Title")

        request = httpx_mock.get_request()
        assert "CCqFvf" in str(request.url)


class TestGetNotebook:
    @pytest.mark.asyncio
    async def test_get_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "rLM1Ne", ["nb_123", "Notebook Name", [["source1"], ["source2"]]]
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.get_notebook("nb_123")

        assert result[0] == "nb_123"

    @pytest.mark.asyncio
    async def test_get_notebook_uses_source_path(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("rLM1Ne", ["nb_123", "Name"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.get_notebook("nb_123")

        request = httpx_mock.get_request()
        assert "source-path=%2Fnotebook%2Fnb_123" in str(request.url)


class TestDeleteNotebook:
    @pytest.mark.asyncio
    async def test_delete_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("WWINqb", [True])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.delete_notebook("nb_123")

        assert result[0] is True


class TestAddSource:
    @pytest.mark.asyncio
    async def test_add_source_url(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("izAoDd", ["source_id", "https://example.com"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.add_source_url("nb_123", "https://example.com")

        assert result[0] == "source_id"

    @pytest.mark.asyncio
    async def test_add_source_text(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("izAoDd", ["source_id", "My Document"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.add_source_text(
                "nb_123", "My Document", "This is the content"
            )

        assert result[0] == "source_id"


class TestStudioContent:
    @pytest.mark.asyncio
    async def test_generate_audio(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        notebook_response = build_rpc_response(
            "rLM1Ne", [["Notebook", [["src_001", "Source 1"]], "nb_123"]]
        )
        httpx_mock.add_response(content=notebook_response.encode())

        response = build_rpc_response("R7cb6c", ["task_id_123", "pending"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_audio(
                notebook_id="nb_123",
            )

        assert result[0] == "task_id_123"

        request = httpx_mock.get_requests()[-1]
        assert "R7cb6c" in str(request.url)

    @pytest.mark.asyncio
    async def test_generate_audio_with_format_and_length(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        from notebooklm.rpc import AudioFormat, AudioLength

        notebook_response = build_rpc_response(
            "rLM1Ne", [["Notebook", [["src_001", "Source 1"]], "nb_123"]]
        )
        httpx_mock.add_response(content=notebook_response.encode())

        response = build_rpc_response("R7cb6c", ["task_id_123", "pending"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_audio(
                notebook_id="nb_123",
                audio_format=AudioFormat.DEBATE,
                audio_length=AudioLength.LONG,
            )

        assert result[0] == "task_id_123"

    @pytest.mark.asyncio
    async def test_generate_video_with_format_and_style(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        from notebooklm.rpc import VideoFormat, VideoStyle

        notebook_response = build_rpc_response(
            "rLM1Ne", [["Test Notebook", [[["source_123"], "Source"]], "nb_123"]]
        )
        video_response = build_rpc_response("R7cb6c", ["task_id_456", "pending"])
        httpx_mock.add_response(content=notebook_response.encode())
        httpx_mock.add_response(content=video_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_video(
                notebook_id="nb_123",
                video_format=VideoFormat.BRIEF,
                video_style=VideoStyle.ANIME,
            )

        assert result[0] == "task_id_456"

    @pytest.mark.asyncio
    async def test_generate_slides(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        notebook_response = build_rpc_response(
            "rLM1Ne", [["Test Notebook", [[["source_123"], "Source"]], "nb_123"]]
        )
        slides_response = build_rpc_response("R7cb6c", ["task_id_456", "pending"])
        httpx_mock.add_response(content=notebook_response.encode())
        httpx_mock.add_response(content=slides_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_slides(notebook_id="nb_123")

        assert result[0] == "task_id_456"

    @pytest.mark.asyncio
    async def test_poll_studio_status(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "gArtLc", ["task_id_123", "completed", "https://audio.url"]
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.poll_studio_status(
                notebook_id="nb_123",
                task_id="task_id_123",
            )

        assert result[1] == "completed"
        assert result[2] == "https://audio.url"


class TestSummary:
    @pytest.mark.asyncio
    async def test_get_summary(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("VfAZjd", ["Summary of the notebook content..."])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.get_summary("nb_123")

        assert "Summary" in result[0]


class TestRenameNotebook:
    @pytest.mark.asyncio
    async def test_rename_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("s0tc2d", ["nb_123", "New Title"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.rename_notebook("nb_123", "New Title")

        assert result[0] == "nb_123"
        assert result[1] == "New Title"

    @pytest.mark.asyncio
    async def test_rename_notebook_request_format(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("s0tc2d", ["nb_123", "Renamed"])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.rename_notebook("nb_123", "Renamed")

        request = httpx_mock.get_request()
        assert "s0tc2d" in str(request.url)
        assert "source-path=%2F" in str(request.url)


class TestDeleteSource:
    @pytest.mark.asyncio
    async def test_delete_source(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("tGMBJ", [True])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.delete_source("nb_123", "source_456")

        assert result[0] is True

    @pytest.mark.asyncio
    async def test_delete_source_request_format(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("tGMBJ", [True])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.delete_source("nb_123", "source_456")

        request = httpx_mock.get_request()
        assert "tGMBJ" in str(request.url)
        assert "source-path=%2Fnotebook%2Fnb_123" in str(request.url)


class TestGetSource:
    @pytest.mark.asyncio
    async def test_get_source(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "hizoJc", ["source_456", "Source Title", "Content preview..."]
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.get_source("nb_123", "source_456")

        assert result[0] == "source_456"
        assert result[1] == "Source Title"


class TestGenerateQuiz:
    @pytest.mark.asyncio
    async def test_generate_quiz(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        notebook_response = build_rpc_response(
            "rLM1Ne", [["Test Notebook", [[["source_123"], "Source"]], "nb_123"]]
        )
        quiz_response = build_rpc_response("R7cb6c", {"task_id": "quiz_123"})
        httpx_mock.add_response(content=notebook_response.encode())
        httpx_mock.add_response(content=quiz_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_quiz("nb_123")

        assert result == {"task_id": "quiz_123"}


class TestDeleteStudioContent:
    @pytest.mark.asyncio
    async def test_delete_studio_content(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response("V5N4be", [True])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.delete_studio_content("nb_123", "task_id_123")

        assert result[0] is True


class TestMindMap:
    @pytest.mark.asyncio
    async def test_generate_mind_map(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        notebook_response = build_rpc_response(
            "rLM1Ne", [["Test Notebook", [[["source_123"], "Source"]], "nb_123"]]
        )
        mindmap_response = build_rpc_response("yyryJe", None)
        httpx_mock.add_response(content=notebook_response.encode())
        httpx_mock.add_response(content=mindmap_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.generate_mind_map("nb_123")

        assert result is None

    @pytest.mark.asyncio
    async def test_list_mind_maps(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "cFji9",
            [
                [
                    ["mm_001", '{"nodes": [], "children": []}'],
                    ["mm_002", '{"nodes": [], "children": []}'],
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.list_mind_maps("nb_123")

        assert len(result) == 2
