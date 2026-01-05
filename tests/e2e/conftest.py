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
from notebooklm.api_client import NotebookLMClient


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
                    await client.delete_notebook(nb_id)
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
                    await client.delete_source(test_notebook_id, src_id)
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
                    await client.delete_studio_content(test_notebook_id, art_id)
                except Exception:
                    pass
