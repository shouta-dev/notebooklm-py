"""CLI interface for NotebookLM automation."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .auth import (
    AuthTokens,
    load_auth_from_storage,
    fetch_tokens,
    DEFAULT_STORAGE_PATH,
)
from .api_client import NotebookLMClient
from .services import NotebookService, SourceService, ArtifactService
from .rpc import (
    AudioFormat,
    AudioLength,
    VideoFormat,
    VideoStyle,
    QuizQuantity,
    QuizDifficulty,
    InfographicOrientation,
    InfographicDetail,
    SlidesFormat,
    SlidesLength,
)

console = Console()

# Persistent browser profile directory
BROWSER_PROFILE_DIR = Path.home() / ".notebooklm" / "browser_profile"


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


@click.group()
@click.version_option(version=__version__, prog_name="NotebookLM CLI")
@click.option(
    "--storage",
    type=click.Path(exists=False),
    default=None,
    help=f"Path to storage_state.json (default: {DEFAULT_STORAGE_PATH})",
)
@click.pass_context
def cli(ctx, storage):
    """NotebookLM automation CLI."""
    ctx.ensure_object(dict)
    ctx.obj["storage_path"] = Path(storage) if storage else None


def get_client(ctx) -> tuple[dict, str, str]:
    """Get auth components from context."""
    storage_path = ctx.obj.get("storage_path")
    cookies = load_auth_from_storage(storage_path)
    csrf, session_id = run_async(fetch_tokens(cookies))
    return cookies, csrf, session_id


@cli.command("login")
@click.option(
    "--storage",
    type=click.Path(),
    default=None,
    help=f"Where to save storage_state.json (default: {DEFAULT_STORAGE_PATH})",
)
def login(storage):
    """Log in to NotebookLM via browser and save authentication.

    Opens a browser window for you to log in to your Google account.
    After successful login, press ENTER in the terminal to save and close.

    Uses a persistent browser profile to avoid Google bot detection.

    Requires: pip install notebooklm[browser]
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        console.print(
            "[red]Playwright not installed. Run:[/red]\n"
            "  pip install notebooklm[browser]\n"
            "  playwright install chromium"
        )
        raise SystemExit(1)

    storage_path = Path(storage) if storage else DEFAULT_STORAGE_PATH
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    # Create persistent browser profile directory
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    console.print("[yellow]Opening browser for Google login...[/yellow]")
    console.print(f"[dim]Using persistent profile: {BROWSER_PROFILE_DIR}[/dim]")

    with sync_playwright() as p:
        # Use persistent context to avoid Google bot detection
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()

        # Navigate to NotebookLM
        page.goto("https://notebooklm.google.com/")

        console.print("\n[bold green]Instructions:[/bold green]")
        console.print("1. Complete the Google login in the browser window")
        console.print(
            "2. Wait until you see the NotebookLM homepage (list of notebooks)"
        )
        console.print(
            "3. Press [bold]ENTER[/bold] here to save authentication and close browser\n"
        )

        # Wait for user to press Enter
        input("[Press ENTER when logged in and on NotebookLM page] ")

        # Verify we're on NotebookLM
        current_url = page.url
        if "notebooklm.google.com" not in current_url:
            console.print(f"[yellow]Warning: Current URL is {current_url}[/yellow]")
            console.print(
                "[yellow]Make sure you're logged in to NotebookLM before continuing.[/yellow]"
            )
            if not click.confirm("Save authentication anyway?"):
                context.close()
                raise SystemExit(1)

        # Save storage state
        context.storage_state(path=str(storage_path))
        context.close()

    console.print(f"\n[green]Authentication saved to:[/green] {storage_path}")
    console.print("\n[dim]You can now use other commands like:[/dim]")
    console.print("  notebooklm list")
    console.print('  notebooklm create "My Notebook"')


@cli.command("list")
@click.pass_context
def list_notebooks(ctx):
    """List all notebooks."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _list():
            async with NotebookLMClient(auth) as client:
                service = NotebookService(client)
                return await service.list()

        notebooks = run_async(_list())

        table = Table(title="Notebooks")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Created", style="dim")

        for nb in notebooks:
            created = nb.created_at.strftime("%Y-%m-%d") if nb.created_at else "-"
            table.add_row(nb.id, nb.title, created)

        console.print(table)

    except FileNotFoundError:
        console.print(f"[red]Auth not found. Run 'notebooklm login' first.[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("create")
@click.argument("title")
@click.pass_context
def create_notebook(ctx, title):
    """Create a new notebook."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _create():
            async with NotebookLMClient(auth) as client:
                service = NotebookService(client)
                return await service.create(title)

        notebook = run_async(_create())
        console.print(
            f"[green]Created notebook:[/green] {notebook.id} - {notebook.title}"
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("add-url")
@click.argument("notebook_id")
@click.argument("url")
@click.pass_context
def add_url(ctx, notebook_id, url):
    """Add a URL source to a notebook."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _add():
            async with NotebookLMClient(auth) as client:
                service = SourceService(client)
                return await service.add_url(notebook_id, url)

        source = run_async(_add())
        console.print(f"[green]Added source:[/green] {source.id}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("add-text")
@click.argument("notebook_id")
@click.argument("title")
@click.argument("content")
@click.pass_context
def add_text(ctx, notebook_id, title, content):
    """Add text content as a source."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _add():
            async with NotebookLMClient(auth) as client:
                service = SourceService(client)
                return await service.add_text(notebook_id, title, content)

        source = run_async(_add())
        console.print(f"[green]Added source:[/green] {source.id}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("add-file")
@click.argument("notebook_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--mime-type", help="MIME type (auto-detected if not specified)")
@click.pass_context
def add_file(ctx, notebook_id, file_path, mime_type):
    """Add a file source to a notebook (PDF, TXT, MD, DOCX, etc.)."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _add():
            async with NotebookLMClient(auth) as client:
                service = SourceService(client)
                return await service.add_file(notebook_id, file_path, mime_type)

        with console.status(f"Uploading {file_path}..."):
            source = run_async(_add())
        console.print(f"[green]Added file as source:[/green] {source.id}")
        console.print(f"[dim]Title: {source.title}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("audio")
@click.argument("notebook_id")
@click.option("-i", "--instructions", help="Instructions for AI hosts")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_audio(ctx, notebook_id, instructions, wait):
    """Generate audio overview (podcast)."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _generate():
            async with NotebookLMClient(auth) as client:
                service = ArtifactService(client)
                status = await service.generate_audio(
                    notebook_id, host_instructions=instructions
                )

                if wait:
                    console.print(
                        f"[yellow]Generating audio...[/yellow] Task: {status.task_id}"
                    )
                    status = await service.wait_for_completion(
                        notebook_id, status.task_id, poll_interval=10.0
                    )

                return status

        status = run_async(_generate())

        if status.is_complete:
            console.print(f"[green]Audio ready:[/green] {status.url}")
        elif status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(
                f"[yellow]Status:[/yellow] {status.status} (task: {status.task_id})"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("slides")
@click.argument("notebook_id")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_slides(ctx, notebook_id, wait):
    """Generate slide deck."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _generate():
            async with NotebookLMClient(auth) as client:
                service = ArtifactService(client)
                status = await service.generate_slides(notebook_id)

                if wait:
                    console.print(
                        f"[yellow]Generating slides...[/yellow] Task: {status.task_id}"
                    )
                    status = await service.wait_for_completion(
                        notebook_id, status.task_id, poll_interval=10.0
                    )

                return status

        status = run_async(_generate())

        if status.is_complete:
            console.print(f"[green]Slides ready:[/green] {status.url}")
        elif status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Status:[/yellow] {status.status}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("delete")
@click.argument("notebook_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_notebook(ctx, notebook_id, yes):
    """Delete a notebook."""
    if not yes:
        if not click.confirm(f"Delete notebook {notebook_id}?"):
            return

    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _delete():
            async with NotebookLMClient(auth) as client:
                service = NotebookService(client)
                return await service.delete(notebook_id)

        success = run_async(_delete())

        if success:
            console.print(f"[green]Deleted notebook:[/green] {notebook_id}")
        else:
            console.print(f"[yellow]Delete may have failed[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("rename")
@click.argument("notebook_id")
@click.argument("new_title")
@click.pass_context
def rename_notebook(ctx, notebook_id, new_title):
    """Rename a notebook."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _rename():
            async with NotebookLMClient(auth) as client:
                return await client.rename_notebook(notebook_id, new_title)

        run_async(_rename())
        console.print(f"[green]Renamed notebook:[/green] {notebook_id} -> {new_title}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("query")
@click.argument("notebook_id")
@click.argument("query_text")
@click.option("--conversation-id", default=None, help="Continue a conversation")
@click.pass_context
def query_notebook(ctx, notebook_id, query_text, conversation_id):
    """Query a notebook (chat)."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _query():
            async with NotebookLMClient(auth) as client:
                return await client.query(
                    notebook_id, query_text, conversation_id=conversation_id
                )

        result = run_async(_query())

        console.print(f"[bold cyan]Answer:[/bold cyan]")
        console.print(result["answer"])
        console.print(f"\n[dim]Conversation ID: {result['conversation_id']}[/dim]")
        console.print(f"[dim]Turn: {result['turn_number']}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("research")
@click.argument("notebook_id")
@click.argument("query")
@click.option(
    "--source", type=click.Choice(["web", "drive"]), default="web", help="Source type"
)
@click.option(
    "--mode", type=click.Choice(["fast", "deep"]), default="fast", help="Research mode"
)
@click.option("--import-all", is_flag=True, help="Import all found sources")
@click.pass_context
def research(ctx, notebook_id, query, source, mode, import_all):
    """Start a research session."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _research():
            async with NotebookLMClient(auth) as client:
                # Start research
                console.print(
                    f"[yellow]Starting {mode} research on {source}...[/yellow]"
                )
                result = await client.start_research(notebook_id, query, source, mode)
                if not result:
                    return None, None

                task_id = result["task_id"]
                console.print(f"[dim]Task ID: {task_id}[/dim]")

                # Poll for completion
                import time

                for _ in range(60):  # Max 5 minutes
                    status = await client.poll_research(notebook_id)
                    if status.get("status") == "completed":
                        return task_id, status
                    elif status.get("status") == "no_research":
                        return None, None
                    time.sleep(5)

                return task_id, {"status": "timeout"}

        task_id, status = run_async(_research())

        if not status or not isinstance(status, dict):
            console.print("[red]Research failed to start[/red]")
            raise SystemExit(1)

        if status.get("status") == "completed":
            sources = status.get("sources", [])
            console.print(f"\n[green]Found {len(sources)} sources:[/green]")
            if isinstance(sources, list):
                for i, src in enumerate(sources, 1):
                    if isinstance(src, dict):
                        console.print(f"  {i}. {src.get('title', 'Untitled')}")
                        if src.get("url"):
                            console.print(f"     [dim]{src['url']}[/dim]")

            if import_all and sources and task_id and isinstance(sources, list):

                async def _import():
                    async with NotebookLMClient(auth) as client:
                        return await client.import_research_sources(
                            notebook_id, task_id, sources
                        )

                imported = run_async(_import())
                console.print(f"\n[green]Imported {len(imported)} sources[/green]")
        else:
            console.print(f"[yellow]Status: {status.get('status', 'unknown')}[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# ==================== SOURCE OPERATIONS ====================


@cli.command("add-youtube")
@click.argument("notebook_id")
@click.argument("youtube_url")
@click.pass_context
def add_youtube(ctx, notebook_id, youtube_url):
    """Add a YouTube video source (with transcript extraction)."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _add():
            async with NotebookLMClient(auth) as client:
                service = SourceService(client)
                # add_url automatically detects YouTube and uses the right API
                return await service.add_url(notebook_id, youtube_url)

        source = run_async(_add())
        console.print(f"[green]Added YouTube source:[/green] {source.id}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("delete-source")
@click.argument("notebook_id")
@click.argument("source_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete_source(ctx, notebook_id, source_id, yes):
    """Delete a source from a notebook."""
    if not yes:
        if not click.confirm(f"Delete source {source_id}?"):
            return

    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _delete():
            async with NotebookLMClient(auth) as client:
                service = SourceService(client)
                return await service.delete(notebook_id, source_id)

        success = run_async(_delete())

        if success:
            console.print(f"[green]Deleted source:[/green] {source_id}")
        else:
            console.print(f"[yellow]Delete may have failed[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("rename-source")
@click.argument("notebook_id")
@click.argument("source_id")
@click.argument("new_title")
@click.pass_context
def rename_source(ctx, notebook_id, source_id, new_title):
    """Rename a source."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _rename():
            async with NotebookLMClient(auth) as client:
                return await client.rename_source(notebook_id, source_id, new_title)

        run_async(_rename())
        console.print(f"[green]Renamed source:[/green] {source_id} -> {new_title}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("list-sources")
@click.argument("notebook_id")
@click.pass_context
def list_sources(ctx, notebook_id):
    """List all sources in a notebook."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _list():
            async with NotebookLMClient(auth) as client:
                notebook = await client.get_notebook(notebook_id)
                # Extract sources from notebook data
                sources = []
                if notebook and isinstance(notebook, list) and len(notebook) > 0:
                    nb_info = notebook[0]
                    if isinstance(nb_info, list) and len(nb_info) > 1:
                        sources_list = nb_info[1]
                        if isinstance(sources_list, list):
                            for src in sources_list:
                                if isinstance(src, list) and len(src) > 0:
                                    src_id = (
                                        src[0][0]
                                        if isinstance(src[0], list)
                                        else src[0]
                                    )
                                    src_title = src[1] if len(src) > 1 else "Untitled"
                                    sources.append({"id": src_id, "title": src_title})
                return sources

        sources = run_async(_list())

        table = Table(title=f"Sources in Notebook {notebook_id}")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")

        for src in sources:
            table.add_row(src["id"], src["title"])

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# ==================== ARTIFACT GENERATION ====================


@cli.command("generate-video")
@click.argument("notebook_id")
@click.option(
    "--format",
    type=click.Choice(["explainer", "brief"]),
    default="explainer",
    help="Video format",
)
@click.option(
    "--style",
    type=click.Choice(
        [
            "auto",
            "classic",
            "whiteboard",
            "kawaii",
            "anime",
            "watercolor",
            "retro-print",
            "heritage",
            "paper-craft",
        ]
    ),
    default="auto",
    help="Visual style",
)
@click.option("-i", "--instructions", help="Custom instructions")
@click.option("--language", default="en", help="Language code")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_video(ctx, notebook_id, format, style, instructions, language, wait):
    """Generate video overview."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        # Map CLI strings to enums
        format_map = {"explainer": VideoFormat.EXPLAINER, "brief": VideoFormat.BRIEF}
        style_map = {
            "auto": VideoStyle.AUTO_SELECT,
            "classic": VideoStyle.CLASSIC,
            "whiteboard": VideoStyle.WHITEBOARD,
            "kawaii": VideoStyle.KAWAII,
            "anime": VideoStyle.ANIME,
            "watercolor": VideoStyle.WATERCOLOR,
            "retro-print": VideoStyle.RETRO_PRINT,
            "heritage": VideoStyle.HERITAGE,
            "paper-craft": VideoStyle.PAPER_CRAFT,
        }

        async def _generate():
            async with NotebookLMClient(auth) as client:
                result = await client.generate_video(
                    notebook_id,
                    language=language,
                    instructions=instructions,
                    video_format=format_map[format],
                    video_style=style_map[style],
                )

                if not result:
                    return None

                task_id = result[0] if isinstance(result, list) else None

                if wait and task_id:
                    console.print(
                        f"[yellow]Generating video...[/yellow] Task: {task_id}"
                    )
                    service = ArtifactService(client)
                    status = await service.wait_for_completion(
                        notebook_id, task_id, poll_interval=10.0, timeout=600.0
                    )
                    return status
                return {"task_id": task_id, "status": "pending"}

        status = run_async(_generate())

        if not status:
            console.print("[red]Video generation failed to start[/red]")
            raise SystemExit(1)

        if isinstance(status, dict):
            task_id = status.get("task_id")
            console.print(f"[yellow]Video generation started:[/yellow] Task {task_id}")
        elif hasattr(status, "is_complete") and status.is_complete:
            console.print(f"[green]Video ready:[/green] {status.url}")
        elif hasattr(status, "is_failed") and status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Video generation started[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("generate-quiz")
@click.argument("notebook_id")
@click.option(
    "--quantity",
    type=click.Choice(["fewer", "standard", "more"]),
    default="standard",
    help="Number of questions",
)
@click.option(
    "--difficulty",
    type=click.Choice(["easy", "medium", "hard"]),
    default="medium",
    help="Difficulty level",
)
@click.option("-i", "--instructions", help="Custom instructions")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_quiz(ctx, notebook_id, quantity, difficulty, instructions, wait):
    """Generate quiz from notebook content."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        # Map CLI strings to enums
        quantity_map = {
            "fewer": QuizQuantity.FEWER,
            "standard": QuizQuantity.STANDARD,
            "more": QuizQuantity.MORE,
        }
        difficulty_map = {
            "easy": QuizDifficulty.EASY,
            "medium": QuizDifficulty.MEDIUM,
            "hard": QuizDifficulty.HARD,
        }

        async def _generate():
            async with NotebookLMClient(auth) as client:
                result = await client.generate_quiz(
                    notebook_id,
                    instructions=instructions,
                    quantity=quantity_map[quantity],
                    difficulty=difficulty_map[difficulty],
                )

                task_id = result[0] if isinstance(result, list) else None

                if wait and task_id:
                    console.print(
                        f"[yellow]Generating quiz...[/yellow] Task: {task_id}"
                    )
                    service = ArtifactService(client)
                    status = await service.wait_for_completion(
                        notebook_id, task_id, poll_interval=5.0
                    )
                    return status
                return {"task_id": task_id}

        status = run_async(_generate())

        if isinstance(status, dict):
            task_id = status.get("task_id")
            console.print(f"[yellow]Quiz generation started:[/yellow] Task {task_id}")
        elif hasattr(status, "is_complete") and status.is_complete:
            console.print(f"[green]Quiz ready[/green]")
        elif hasattr(status, "is_failed") and status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Quiz generation started[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("generate-flashcards")
@click.argument("notebook_id")
@click.option(
    "--quantity",
    type=click.Choice(["fewer", "standard", "more"]),
    default="standard",
    help="Number of cards",
)
@click.option(
    "--difficulty",
    type=click.Choice(["easy", "medium", "hard"]),
    default="medium",
    help="Difficulty level",
)
@click.option("-i", "--instructions", help="Custom instructions")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_flashcards(ctx, notebook_id, quantity, difficulty, instructions, wait):
    """Generate flashcards from notebook content."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        quantity_map = {
            "fewer": QuizQuantity.FEWER,
            "standard": QuizQuantity.STANDARD,
            "more": QuizQuantity.MORE,
        }
        difficulty_map = {
            "easy": QuizDifficulty.EASY,
            "medium": QuizDifficulty.MEDIUM,
            "hard": QuizDifficulty.HARD,
        }

        async def _generate():
            async with NotebookLMClient(auth) as client:
                result = await client.generate_flashcards(
                    notebook_id,
                    instructions=instructions,
                    quantity=quantity_map[quantity],
                    difficulty=difficulty_map[difficulty],
                )

                task_id = result[0] if isinstance(result, list) else None

                if wait and task_id:
                    console.print(
                        f"[yellow]Generating flashcards...[/yellow] Task: {task_id}"
                    )
                    service = ArtifactService(client)
                    status = await service.wait_for_completion(
                        notebook_id, task_id, poll_interval=5.0
                    )
                    return status
                return {"task_id": task_id}

        status = run_async(_generate())

        if isinstance(status, dict):
            task_id = status.get("task_id")
            console.print(
                f"[yellow]Flashcards generation started:[/yellow] Task {task_id}"
            )
        elif hasattr(status, "is_complete") and status.is_complete:
            console.print(f"[green]Flashcards ready[/green]")
        elif hasattr(status, "is_failed") and status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Flashcards generation started[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("generate-infographic")
@click.argument("notebook_id")
@click.option(
    "--orientation",
    type=click.Choice(["landscape", "portrait", "square"]),
    default="landscape",
    help="Orientation",
)
@click.option(
    "--detail",
    type=click.Choice(["concise", "standard", "detailed"]),
    default="standard",
    help="Detail level",
)
@click.option("-i", "--instructions", help="Custom instructions")
@click.option("--language", default="en", help="Language code")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_infographic(
    ctx, notebook_id, orientation, detail, instructions, language, wait
):
    """Generate infographic from notebook content."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        orientation_map = {
            "landscape": InfographicOrientation.LANDSCAPE,
            "portrait": InfographicOrientation.PORTRAIT,
            "square": InfographicOrientation.SQUARE,
        }
        detail_map = {
            "concise": InfographicDetail.CONCISE,
            "standard": InfographicDetail.STANDARD,
            "detailed": InfographicDetail.DETAILED,
        }

        async def _generate():
            async with NotebookLMClient(auth) as client:
                result = await client.generate_infographic(
                    notebook_id,
                    language=language,
                    instructions=instructions,
                    orientation=orientation_map[orientation],
                    detail_level=detail_map[detail],
                )

                task_id = result[0] if isinstance(result, list) and result else None

                if wait and task_id:
                    console.print(
                        f"[yellow]Generating infographic...[/yellow] Task: {task_id}"
                    )
                    service = ArtifactService(client)
                    status = await service.wait_for_completion(
                        notebook_id, task_id, poll_interval=5.0
                    )
                    return status
                return {"task_id": task_id}

        status = run_async(_generate())

        if isinstance(status, dict):
            task_id = status.get("task_id")
            console.print(
                f"[yellow]Infographic generation started:[/yellow] Task {task_id}"
            )
        elif hasattr(status, "is_complete") and status.is_complete:
            console.print(f"[green]Infographic ready[/green]")
        elif hasattr(status, "is_failed") and status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Infographic generation started[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("generate-data-table")
@click.argument("notebook_id")
@click.option(
    "-i",
    "--instructions",
    required=True,
    help="Instructions describing table structure",
)
@click.option("--language", default="en", help="Language code")
@click.option("--wait/--no-wait", default=True, help="Wait for completion")
@click.pass_context
def generate_data_table(ctx, notebook_id, instructions, language, wait):
    """Generate data table from notebook content."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _generate():
            async with NotebookLMClient(auth) as client:
                result = await client.generate_data_table(
                    notebook_id,
                    language=language,
                    instructions=instructions,
                )

                task_id = result[0] if isinstance(result, list) and result else None

                if wait and task_id:
                    console.print(
                        f"[yellow]Generating data table...[/yellow] Task: {task_id}"
                    )
                    service = ArtifactService(client)
                    status = await service.wait_for_completion(
                        notebook_id, task_id, poll_interval=5.0
                    )
                    return status
                return {"task_id": task_id}

        status = run_async(_generate())

        if isinstance(status, dict):
            task_id = status.get("task_id")
            console.print(
                f"[yellow]Data table generation started:[/yellow] Task {task_id}"
            )
        elif hasattr(status, "is_complete") and status.is_complete:
            console.print(f"[green]Data table ready[/green]")
        elif hasattr(status, "is_failed") and status.is_failed:
            console.print(f"[red]Generation failed:[/red] {status.error}")
        else:
            console.print(f"[yellow]Data table generation started[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# ==================== DOWNLOAD OPERATIONS ====================


@cli.command("download-audio")
@click.argument("notebook_id")
@click.argument("output_path", type=click.Path())
@click.option("--artifact-id", help="Specific audio artifact ID (optional)")
@click.pass_context
def download_audio(ctx, notebook_id, output_path, artifact_id):
    """Download audio overview to file."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _download():
            async with NotebookLMClient(auth) as client:
                return await client.download_audio(
                    notebook_id, output_path, artifact_id=artifact_id
                )

        with console.status(f"Downloading audio to {output_path}..."):
            result_path = run_async(_download())

        console.print(f"[green]Audio saved to:[/green] {result_path}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("download-video")
@click.argument("notebook_id")
@click.argument("output_path", type=click.Path())
@click.option("--artifact-id", help="Specific video artifact ID (optional)")
@click.pass_context
def download_video(ctx, notebook_id, output_path, artifact_id):
    """Download video overview to file."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _download():
            async with NotebookLMClient(auth) as client:
                return await client.download_video(
                    notebook_id, output_path, artifact_id=artifact_id
                )

        with console.status(f"Downloading video to {output_path}..."):
            result_path = run_async(_download())

        console.print(f"[green]Video saved to:[/green] {result_path}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("download-infographic")
@click.argument("notebook_id")
@click.argument("output_path", type=click.Path())
@click.option("--artifact-id", help="Specific infographic artifact ID (optional)")
@click.pass_context
def download_infographic(ctx, notebook_id, output_path, artifact_id):
    """Download infographic image to file."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _download():
            async with NotebookLMClient(auth) as client:
                return await client.download_infographic(
                    notebook_id, output_path, artifact_id=artifact_id
                )

        with console.status(f"Downloading infographic to {output_path}..."):
            result_path = run_async(_download())

        console.print(f"[green]Infographic saved to:[/green] {result_path}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("download-slides")
@click.argument("notebook_id")
@click.argument("output_dir", type=click.Path())
@click.option("--artifact-id", help="Specific slide deck artifact ID (optional)")
@click.pass_context
def download_slides(ctx, notebook_id, output_dir, artifact_id):
    """Download slide deck images to directory."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _download():
            async with NotebookLMClient(auth) as client:
                return await client.download_slide_deck(
                    notebook_id, output_dir, artifact_id=artifact_id
                )

        with console.status(f"Downloading slides to {output_dir}..."):
            paths = run_async(_download())

        console.print(f"[green]Downloaded {len(paths)} slides to:[/green] {output_dir}")
        for i, path in enumerate(paths, 1):
            console.print(f"  {i}. {path}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


# ==================== OTHER OPERATIONS ====================


@cli.command("get-summary")
@click.argument("notebook_id")
@click.pass_context
def get_summary(ctx, notebook_id):
    """Get notebook summary/briefing doc."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _get():
            async with NotebookLMClient(auth) as client:
                return await client.get_summary(notebook_id)

        summary = run_async(_get())

        # Try to extract readable text from the response
        if summary and isinstance(summary, list):
            # Navigate the nested structure to find the summary text
            console.print("[bold cyan]Summary:[/bold cyan]")
            console.print(summary)
        else:
            console.print("[yellow]No summary available[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@cli.command("get-conversation-history")
@click.argument("notebook_id")
@click.option("--limit", default=20, help="Number of messages to retrieve")
@click.pass_context
def get_conversation_history(ctx, notebook_id, limit):
    """Get chat conversation history."""
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _get():
            async with NotebookLMClient(auth) as client:
                return await client.get_conversation_history(notebook_id, limit=limit)

        history = run_async(_get())

        console.print(f"[bold cyan]Conversation History (last {limit}):[/bold cyan]")
        if history:
            console.print(history)
        else:
            console.print("[yellow]No conversation history found[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


def main():
    cli()


if __name__ == "__main__":
    main()
