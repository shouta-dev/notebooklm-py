import pytest
from .conftest import requires_auth


@requires_auth
@pytest.mark.e2e
class TestSourceOperations:
    @pytest.mark.asyncio
    async def test_add_text_source(
        self, client, test_notebook_id, created_sources, cleanup_sources
    ):
        result = await client.add_source_text(
            test_notebook_id,
            "E2E Test Text Source",
            "This is test content for E2E testing. It contains enough text for NotebookLM to process.",
        )
        assert result is not None
        source_id = result[0][0][0]
        created_sources.append(source_id)
        assert source_id is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_add_url_source(
        self, client, test_notebook_id, created_sources, cleanup_sources
    ):
        result = await client.add_source_url(
            test_notebook_id, "https://httpbin.org/html"
        )
        assert result is not None
        source_id = result[0][0][0]
        created_sources.append(source_id)
        assert source_id is not None

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_add_youtube_source(
        self, client, test_notebook_id, created_sources, cleanup_sources
    ):
        result = await client.add_youtube_source(
            test_notebook_id, "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        )
        assert result is not None
        source_id = result[0][0][0]
        created_sources.append(source_id)
        assert source_id is not None

    @pytest.mark.asyncio
    async def test_rename_source(self, client, test_notebook_id):
        notebook = await client.get_notebook(test_notebook_id)
        source_ids = client._extract_source_ids(notebook)
        if not source_ids:
            pytest.skip("No sources available to rename")

        source_id = source_ids[0]
        original_title = None
        for src in notebook[0][1]:
            if isinstance(src, list) and src[0][0] == source_id:
                original_title = src[1]
                break

        result = await client.rename_source(
            test_notebook_id, source_id, "Renamed Test Source"
        )
        assert result is not None

        if original_title:
            await client.rename_source(test_notebook_id, source_id, original_title)


@requires_auth
@pytest.mark.e2e
class TestSourceRetrieval:
    @pytest.mark.asyncio
    async def test_extract_source_ids(self, client, test_notebook_id):
        notebook = await client.get_notebook(test_notebook_id)
        source_ids = client._extract_source_ids(notebook)
        assert isinstance(source_ids, list)
