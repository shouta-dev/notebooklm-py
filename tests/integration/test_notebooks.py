"""Integration tests for NotebooksAPI."""

import pytest
from pytest_httpx import HTTPXMock

from notebooklm import NotebookLMClient, Notebook


class TestListNotebooks:
    @pytest.mark.asyncio
    async def test_list_notebooks_returns_notebooks(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            notebooks = await client.notebooks.list()

        assert len(notebooks) == 2
        assert all(isinstance(nb, Notebook) for nb in notebooks)
        assert notebooks[0].title == "My First Notebook"
        assert notebooks[0].id == "nb_001"

    @pytest.mark.asyncio
    async def test_list_notebooks_request_format(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        mock_list_notebooks_response,
    ):
        httpx_mock.add_response(content=mock_list_notebooks_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.notebooks.list()

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
            await client.notebooks.list()

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
            await client.notebooks.list()

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
        response = build_rpc_response(
            "CCqFvf",
            [
                "My Notebook",
                [],
                "new_nb_id",
                "📓",
                None,
                [None, None, None, None, None, [1704067200, 0]],
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            notebook = await client.notebooks.create("My Notebook")

        assert isinstance(notebook, Notebook)
        assert notebook.id == "new_nb_id"
        assert notebook.title == "My Notebook"

    @pytest.mark.asyncio
    async def test_create_notebook_request_contains_title(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "CCqFvf",
            ["Test Title", [], "id", "📓", None, [None, None, None, None, None, [1704067200, 0]]],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.notebooks.create("Test Title")

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
            "rLM1Ne",
            [
                [
                    "Test Notebook",
                    [["source1"], ["source2"]],
                    "nb_123",
                    "📘",
                    None,
                    [None, None, None, None, None, [1704067200, 0]],
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            notebook = await client.notebooks.get("nb_123")

        assert isinstance(notebook, Notebook)
        assert notebook.id == "nb_123"
        assert notebook.title == "Test Notebook"

    @pytest.mark.asyncio
    async def test_get_notebook_uses_source_path(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "rLM1Ne",
            [["Name", [], "nb_123", "📘", None, [None, None, None, None, None, [1704067200, 0]]]],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.notebooks.get("nb_123")

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
            result = await client.notebooks.delete("nb_123")

        assert result is True


class TestSummary:
    @pytest.mark.asyncio
    async def test_get_summary(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "VfAZjd", ["Summary of the notebook content..."]
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.notebooks.get_summary("nb_123")

        assert "Summary" in result


class TestRenameNotebook:
    @pytest.mark.asyncio
    async def test_rename_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        # First response for rename (returns null)
        rename_response = build_rpc_response("s0tc2d", None)
        httpx_mock.add_response(content=rename_response.encode())
        # Second response for get_notebook call after rename
        get_response = build_rpc_response(
            "rLM1Ne",
            [
                [
                    "New Title",
                    [],
                    "nb_123",
                    "📘",
                    None,
                    [None, None, None, None, None, [1704067200, 0]],
                ]
            ],
        )
        httpx_mock.add_response(content=get_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            notebook = await client.notebooks.rename("nb_123", "New Title")

        assert isinstance(notebook, Notebook)
        assert notebook.id == "nb_123"
        assert notebook.title == "New Title"

    @pytest.mark.asyncio
    async def test_rename_notebook_request_format(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        # Rename response (returns null)
        rename_response = build_rpc_response("s0tc2d", None)
        httpx_mock.add_response(content=rename_response.encode())
        # Get notebook response after rename
        get_response = build_rpc_response(
            "rLM1Ne",
            [["Renamed", [], "nb_123", "📘", None, [None, None, None, None, None, [1704067200, 0]]]],
        )
        httpx_mock.add_response(content=get_response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            await client.notebooks.rename("nb_123", "Renamed")

        request = httpx_mock.get_requests()[0]
        assert "s0tc2d" in str(request.url)
        assert "source-path=%2F" in str(request.url)


class TestNotebooksAPIAdditional:
    """Additional integration tests for NotebooksAPI."""

    @pytest.mark.asyncio
    async def test_share_notebook(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test sharing a notebook with settings."""
        response = build_rpc_response(
            "QDyure",
            ["https://notebooklm.google.com/notebook/abc123?share=true"],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            # share() takes settings dict, not public=True
            result = await client.notebooks.share("nb_123", settings={"public": True})

        assert result is not None
        request = httpx_mock.get_request()
        assert "QDyure" in str(request.url)

    @pytest.mark.asyncio
    async def test_get_summary_additional(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test getting notebook summary."""
        response = build_rpc_response(
            "VfAZjd",
            ["This is a comprehensive summary of the notebook content..."],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.notebooks.get_summary("nb_123")

        assert "summary" in result.lower()

    @pytest.mark.asyncio
    async def test_get_analytics(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test getting analytics for notebook."""
        response = build_rpc_response(
            "AUrzMb",
            [10, 5, 3],  # views, edits, shares
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.notebooks.get_analytics("nb_123")

        assert result is not None
        request = httpx_mock.get_request()
        assert "AUrzMb" in str(request.url)
