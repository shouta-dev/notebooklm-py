"""E2E test fixtures and configuration."""

import os
import warnings
import pytest
import httpx
from typing import AsyncGenerator

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on shell environment

from notebooklm.auth import (
    load_auth_from_storage,
    extract_csrf_from_html,
    extract_session_id_from_html,
    DEFAULT_STORAGE_PATH,
    AuthTokens,
)
from notebooklm import NotebookLMClient


# =============================================================================
# Constants
# =============================================================================

# Delay constants for rate limiting and polling
RATE_LIMIT_DELAY = 3.0  # Delay after tests to avoid rate limits
SOURCE_PROCESSING_DELAY = 2.0  # Delay for source processing
POLL_INTERVAL = 2.0  # Interval between poll attempts
POLL_TIMEOUT = 60.0  # Max time to wait for operations


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


# =============================================================================
# Auth Fixtures (session-scoped for efficiency)
# =============================================================================


@pytest.fixture(scope="session")
def auth_cookies() -> dict[str, str]:
    """Load auth cookies from storage (session-scoped)."""
    return load_auth_from_storage()


@pytest.fixture(scope="session")
def auth_tokens(auth_cookies) -> AuthTokens:
    """Fetch auth tokens synchronously (session-scoped)."""
    import asyncio

    async def _fetch_tokens():
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

    return asyncio.run(_fetch_tokens())


@pytest.fixture
async def client(auth_tokens) -> AsyncGenerator[NotebookLMClient, None]:
    async with NotebookLMClient(auth_tokens) as c:
        yield c


@pytest.fixture
def test_notebook_id():
    """Get notebook ID from NOTEBOOKLM_TEST_NOTEBOOK_ID env var.

    This env var is REQUIRED for E2E tests. You must create your own
    test notebook with sources and artifacts. See docs/contributing/testing.md.
    """
    notebook_id = os.environ.get("NOTEBOOKLM_TEST_NOTEBOOK_ID")
    if not notebook_id:
        pytest.exit(
            "\n\nERROR: NOTEBOOKLM_TEST_NOTEBOOK_ID environment variable is not set.\n\n"
            "E2E tests require YOUR OWN test notebook with content.\n\n"
            "Setup instructions:\n"
            "  1. Create a notebook at https://notebooklm.google.com\n"
            "  2. Add sources (text, URL, PDF, etc.)\n"
            "  3. Generate some artifacts (audio, quiz, etc.)\n"
            "  4. Copy notebook ID from URL and run:\n"
            "     export NOTEBOOKLM_TEST_NOTEBOOK_ID='your-notebook-id'\n\n"
            "See docs/contributing/testing.md for details.\n",
            returncode=1,
        )
    return notebook_id


@pytest.fixture
def created_notebooks():
    notebooks = []
    yield notebooks


@pytest.fixture
async def cleanup_notebooks(created_notebooks, auth_tokens):
    """Cleanup created notebooks after test."""
    yield
    if created_notebooks:
        async with NotebookLMClient(auth_tokens) as client:
            for nb_id in created_notebooks:
                try:
                    await client.notebooks.delete(nb_id)
                except Exception as e:
                    warnings.warn(f"Failed to cleanup notebook {nb_id}: {e}")


@pytest.fixture
def created_sources():
    sources = []
    yield sources


@pytest.fixture
async def cleanup_sources(created_sources, test_notebook_id, auth_tokens):
    """Cleanup created sources after test."""
    yield
    if created_sources:
        async with NotebookLMClient(auth_tokens) as client:
            for src_id in created_sources:
                try:
                    await client.sources.delete(test_notebook_id, src_id)
                except Exception as e:
                    warnings.warn(f"Failed to cleanup source {src_id}: {e}")


@pytest.fixture
def created_artifacts():
    artifacts = []
    yield artifacts


@pytest.fixture
async def cleanup_artifacts(created_artifacts, test_notebook_id, auth_tokens):
    """Cleanup created artifacts after test."""
    yield
    if created_artifacts:
        async with NotebookLMClient(auth_tokens) as client:
            for art_id in created_artifacts:
                try:
                    await client.artifacts.delete(test_notebook_id, art_id)
                except Exception as e:
                    warnings.warn(f"Failed to cleanup artifact {art_id}: {e}")


# =============================================================================
# Notebook Fixtures
# =============================================================================


@pytest.fixture
async def temp_notebook(client, created_notebooks, cleanup_notebooks):
    """Create a temporary notebook that auto-deletes after test.

    Use for CRUD tests that need isolated state.
    """
    from uuid import uuid4
    notebook = await client.notebooks.create(f"Test-{uuid4().hex[:8]}")
    created_notebooks.append(notebook.id)
    return notebook


# =============================================================================
# Test Infrastructure Fixtures (for tiered testing)
# =============================================================================


@pytest.fixture(scope="session")
async def generation_notebook(auth_tokens) -> AsyncGenerator:
    """Session-scoped notebook with content for generation tests.

    Creates a single notebook at session start with test content.
    Shared across all generation tests to avoid repeated setup.
    Cleaned up at session end.

    Use for: artifact generation (audio, video, quiz, etc.)
    Do NOT use for: CRUD tests (use temp_notebook instead)
    """
    import asyncio
    from uuid import uuid4

    async with NotebookLMClient(auth_tokens) as client:
        notebook = await client.notebooks.create(f"GenTest-{uuid4().hex[:8]}")

        # Add a text source so the notebook has content for operations
        await client.sources.add_text(
            notebook.id,
            title="Test Content",
            content=(
                "This is comprehensive test content for E2E testing. "
                "It covers various topics including artificial intelligence, "
                "machine learning, data science, and software engineering. "
                "The content is designed to be substantial enough for "
                "generating artifacts like audio overviews, quizzes, "
                "flashcards, reports, and other NotebookLM features."
            ),
        )

        # Delay to ensure source is processed
        await asyncio.sleep(SOURCE_PROCESSING_DELAY)

        yield notebook

        # Cleanup at session end
        try:
            await client.notebooks.delete(notebook.id)
        except Exception as e:
            warnings.warn(f"Failed to cleanup generation_notebook {notebook.id}: {e}")


@pytest.fixture
async def rate_limit_aware() -> AsyncGenerator[None, None]:
    """Add delay after test to avoid rate limiting.

    Use this fixture in generation tests to add breathing room
    between API calls. Yields before test, sleeps after.
    """
    import asyncio

    yield  # Run the test

    # Add delay after test to avoid rate limits
    await asyncio.sleep(RATE_LIMIT_DELAY)
