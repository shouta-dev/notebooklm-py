import pytest
from .conftest import requires_auth


@requires_auth
@pytest.mark.e2e
class TestNotebookOperations:
    @pytest.mark.asyncio
    async def test_list_notebooks(self, client):
        notebooks = await client.list_notebooks()
        assert isinstance(notebooks, list)

    @pytest.mark.asyncio
    async def test_get_notebook(self, client, test_notebook_id):
        notebook = await client.get_notebook(test_notebook_id)
        assert notebook is not None
        assert isinstance(notebook, list)

    @pytest.mark.asyncio
    async def test_create_rename_delete_notebook(
        self, client, created_notebooks, cleanup_notebooks
    ):
        result = await client.create_notebook("E2E Test Notebook")
        nb_id = result[0]
        created_notebooks.append(nb_id)
        assert nb_id is not None

        await client.rename_notebook(nb_id, "E2E Test Renamed")

        deleted = await client.delete_notebook(nb_id)
        assert deleted is not None
        created_notebooks.remove(nb_id)

    @pytest.mark.asyncio
    async def test_get_summary(self, client, test_notebook_id):
        summary = await client.get_summary(test_notebook_id)
        assert summary is not None

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, client, test_notebook_id):
        history = await client.get_conversation_history(test_notebook_id)
        assert history is not None


@requires_auth
@pytest.mark.e2e
class TestNotebookQuery:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_query_notebook(self, client, test_notebook_id):
        result = await client.query(test_notebook_id, "What is this notebook about?")
        assert "answer" in result
        assert "conversation_id" in result
