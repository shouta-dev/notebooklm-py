"""E2E test fixtures and configuration."""

import os
import pytest
import httpx
from typing import AsyncGenerator

from notebooklm.auth import (
    load_auth_from_storage,
    extract_csrf_from_html,
    extract_session_id_from_html,
    DEFAULT_STORAGE_PATH,
    AuthTokens,
)
from notebooklm import NotebookLMClient


def has_auth() -> bool:
    try:
        load_auth_from_storage()
        return True
    except (FileNotFoundError, ValueError):
        return False


requires_auth = pytest.mark.skipif(
    not has_auth(),
    reason=f"Requires authentication at {DEFAULT_STORAGE_PATH}",
)


@pytest.fixture
def auth_cookies():
    return load_auth_from_storage()


@pytest.fixture
async def auth_tokens(auth_cookies) -> AuthTokens:
    cookie_header = "; ".join(f"{k}={v}" for k, v in auth_cookies.items())
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            "https://notebooklm.google.com/",
            headers={"Cookie": cookie_header},
            follow_redirects=True,
        )
        resp.raise_for_status()
        csrf = extract_csrf_from_html(resp.text)
        session_id = extract_session_id_from_html(resp.text)
    return AuthTokens(cookies=auth_cookies, csrf_token=csrf, session_id=session_id)


@pytest.fixture
async def client(auth_tokens) -> AsyncGenerator[NotebookLMClient, None]:
    async with NotebookLMClient(auth_tokens) as c:
        yield c


@pytest.fixture
def test_notebook_id():
    """Get notebook ID from env var or use default test notebook."""
    return os.environ.get(
        "NOTEBOOKLM_TEST_NOTEBOOK_ID", "834ddae2-5396-4d9a-8ed4-1ae01b674603"
    )


@pytest.fixture
def created_notebooks():
    notebooks = []
    yield notebooks


@pytest.fixture
async def cleanup_notebooks(created_notebooks, auth_tokens):
    yield
    if created_notebooks:
        async with NotebookLMClient(auth_tokens) as client:
            for nb_id in created_notebooks:
                try:
                    await client.notebooks.delete(nb_id)
                except Exception:
                    pass


@pytest.fixture
def created_sources():
    sources = []
    yield sources


@pytest.fixture
async def cleanup_sources(created_sources, test_notebook_id, auth_tokens):
    yield
    if created_sources:
        async with NotebookLMClient(auth_tokens) as client:
            for src_id in created_sources:
                try:
                    await client.sources.delete(test_notebook_id, src_id)
                except Exception:
                    pass


@pytest.fixture
def created_artifacts():
    artifacts = []
    yield artifacts


@pytest.fixture
async def cleanup_artifacts(created_artifacts, test_notebook_id, auth_tokens):
    yield
    if created_artifacts:
        async with NotebookLMClient(auth_tokens) as client:
            for art_id in created_artifacts:
                try:
                    await client.artifacts.delete(test_notebook_id, art_id)
                except Exception:
                    pass


# =============================================================================
# Golden Notebook Fixtures (for read-only and mutation tests)
# =============================================================================


@pytest.fixture(scope="session")
def golden_notebook_id():
    """Get golden notebook ID from env var.

    The golden notebook should be pre-seeded with:
    - Sources: Web URL, YouTube video, pasted text
    - Artifacts: Audio, Video, Quiz, Flashcards, Slide Deck, Mind Map

    Set NOTEBOOKLM_GOLDEN_NOTEBOOK_ID env var before running tests.
    """
    nb_id = os.environ.get("NOTEBOOKLM_GOLDEN_NOTEBOOK_ID")
    if not nb_id:
        pytest.skip("Golden notebook not configured (set NOTEBOOKLM_GOLDEN_NOTEBOOK_ID)")
    return nb_id


@pytest.fixture(scope="session")
async def golden_client(auth_tokens) -> AsyncGenerator[NotebookLMClient, None]:
    """Session-scoped client for golden notebook tests.

    Use this for read-only tests that don't modify state.
    """
    async with NotebookLMClient(auth_tokens) as c:
        yield c


@pytest.fixture
async def temp_notebook(client, created_notebooks, cleanup_notebooks):
    """Create a temporary notebook that auto-deletes after test.

    Use for CRUD tests that need isolated state.
    """
    from uuid import uuid4
    notebook = await client.notebooks.create(f"Test-{uuid4().hex[:8]}")
    created_notebooks.append(notebook.id)
    return notebook


@pytest.fixture(scope="session")
async def generation_notebook(auth_tokens) -> AsyncGenerator:
    """Session-scoped notebook for slow generation tests.

    Created once per test session with a source added.
    Cleaned up at session end.
    """
    from uuid import uuid4

    async with NotebookLMClient(auth_tokens) as client:
        notebook = await client.notebooks.create(f"GenTest-{uuid4().hex[:8]}")
        # Add a source so generation works
        await client.sources.add_text(
            notebook.id,
            "This is test content for artifact generation. "
            "It contains enough text to generate various artifacts like "
            "audio overviews, quizzes, and summaries."
        )
        yield notebook
        # Cleanup
        try:
            await client.notebooks.delete(notebook.id)
        except Exception:
            pass
