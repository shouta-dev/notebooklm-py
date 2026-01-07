"""Integration tests for SourcesAPI."""

import pytest
from pytest_httpx import HTTPXMock

from notebooklm import NotebookLMClient, Source


class TestAddSource:
    @pytest.mark.asyncio
    async def test_add_source_url(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "izAoDd",
            [
                [
                    [
                        ["source_id"],
                        "Example Site",
                        [None, 11, None, None, 5, None, 1, ["https://example.com"]],
                        [None, 2],
                    ]
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.add_url("nb_123", "https://example.com")

        assert isinstance(source, Source)
        assert source.id == "source_id"
        assert source.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_add_source_text(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        response = build_rpc_response(
            "izAoDd", [[[["source_id"], "My Document", [None, 11], [None, 2]]]]
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.add_text(
                "nb_123", "My Document", "This is the content"
            )

        assert isinstance(source, Source)
        assert source.id == "source_id"
        assert source.title == "My Document"


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
            result = await client.sources.delete("nb_123", "source_456")

        assert result is True

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
            await client.sources.delete("nb_123", "source_456")

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
        # get_source filters from get_notebook, so mock GET_NOTEBOOK response
        response = build_rpc_response(
            "rLM1Ne",
            [
                [
                    "Test Notebook",
                    [
                        [["source_456"], "Source Title", [None, 0, [1704067200, 0]], [None, 2]],
                        [["source_789"], "Other Source", [None, 0, [1704153600, 0]], [None, 2]],
                    ],
                    "nb_123",
                    "📘",
                    None,
                    [None, None, None, None, None, [1704067200, 0]],
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.get("nb_123", "source_456")

        assert isinstance(source, Source)
        assert source.id == "source_456"
        assert source.title == "Source Title"


class TestSourcesAPI:
    """Integration tests for SourcesAPI methods."""

    @pytest.mark.asyncio
    async def test_list_sources(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test listing sources with various types."""
        response = build_rpc_response(
            "rLM1Ne",
            [
                [
                    "Test Notebook",
                    [
                        [["src_001"], "My Article", [None, 11, [1704067200, 0], None, 5, None, None, ["https://example.com"]], [None, 2]],
                        [["src_002"], "My Text", [None, 0, [1704153600, 0]], [None, 2]],
                        [["src_003"], "YouTube Video", [None, 11, [1704240000, 0], None, 5, None, None, ["https://youtube.com/watch?v=abc"]], [None, 2]],
                    ],
                    "nb_123",
                    "📘",
                    None,
                    [None, None, None, None, None, [1704067200, 0]],
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            sources = await client.sources.list("nb_123")

        assert len(sources) == 3
        assert sources[0].id == "src_001"
        assert sources[0].source_type == "url"
        assert sources[0].url == "https://example.com"
        assert sources[2].source_type == "youtube"

    @pytest.mark.asyncio
    async def test_list_sources_empty(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test listing sources from empty notebook."""
        response = build_rpc_response(
            "rLM1Ne",
            [["Empty Notebook", [], "nb_123", "📘", None, [None, None, None, None, None, [1704067200, 0]]]],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            sources = await client.sources.list("nb_123")

        assert sources == []

    @pytest.mark.asyncio
    async def test_get_source_not_found(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test getting a non-existent source."""
        response = build_rpc_response(
            "rLM1Ne",
            [["Notebook", [[["src_001"], "Source 1", [None, 0], [None, 2]]], "nb_123", "📘", None, [None, None, None, None, None, [1704067200, 0]]]],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.get("nb_123", "nonexistent")

        assert source is None

    @pytest.mark.asyncio
    async def test_add_drive_source(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test adding a Google Drive source."""
        response = build_rpc_response(
            "izAoDd",
            [[[["drive_001"], "My Doc", [None, 0], [None, 2]]]],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.add_drive(
                "nb_123",
                file_id="abc123xyz",
                title="My Doc",
                mime_type="application/vnd.google-apps.document",
            )

        assert source is not None
        request = httpx_mock.get_request()
        assert "izAoDd" in str(request.url)

    @pytest.mark.asyncio
    async def test_refresh_source(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test refreshing a source."""
        response = build_rpc_response("FLmJqe", None)
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            result = await client.sources.refresh("nb_123", "src_001")

        assert result is True
        request = httpx_mock.get_request()
        assert "FLmJqe" in str(request.url)

    @pytest.mark.asyncio
    async def test_check_freshness_fresh(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test checking freshness - source is fresh."""
        response = build_rpc_response("yR9Yof", True)
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            is_fresh = await client.sources.check_freshness("nb_123", "src_001")

        assert is_fresh is True

    @pytest.mark.asyncio
    async def test_check_freshness_stale(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test checking freshness - source is stale."""
        response = build_rpc_response("yR9Yof", False)
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            is_fresh = await client.sources.check_freshness("nb_123", "src_001")

        assert is_fresh is False

    @pytest.mark.asyncio
    async def test_get_guide(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test getting source guide."""
        response = build_rpc_response(
            "tr032e",
            [
                [
                    None,
                    ["This is a **summary** of the source content..."],
                    [["keyword1", "keyword2", "keyword3"]],
                ]
            ],
        )
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            guide = await client.sources.get_guide("nb_123", "src_001")

        assert "summary" in guide
        assert "keywords" in guide
        assert "**summary**" in guide["summary"]

    @pytest.mark.asyncio
    async def test_get_guide_empty(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test getting guide for source with no AI analysis."""
        response = build_rpc_response("tr032e", [[None, [], []]])
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            guide = await client.sources.get_guide("nb_123", "src_001")

        assert guide["summary"] == ""
        assert guide["keywords"] == []

    @pytest.mark.asyncio
    async def test_rename_source(
        self,
        auth_tokens,
        httpx_mock: HTTPXMock,
        build_rpc_response,
    ):
        """Test renaming a source."""
        response = build_rpc_response("b7Wfje", None)
        httpx_mock.add_response(content=response.encode())

        async with NotebookLMClient(auth_tokens) as client:
            source = await client.sources.rename("nb_123", "src_001", "New Title")

        assert source.title == "New Title"

        request = httpx_mock.get_request()
        assert "b7Wfje" in str(request.url)
