"""CLI interface for NotebookLM automation.

Command structure:
  notebooklm login                    # Authenticate
  notebooklm use <notebook_id>        # Set current notebook context
  notebooklm status                   # Show current context
  notebooklm list                     # List notebooks
  notebooklm create <title>           # Create notebook
  notebooklm ask <question>           # Ask the current notebook a question

  notebooklm source <command>         # Source operations
  notebooklm artifact <command>       # Artifact management
  notebooklm generate <type>          # Generate content
  notebooklm download <type>          # Download content
  notebooklm note <command>           # Note operations

LLM-friendly design:
  # Set context once, then use simple commands
  notebooklm use nb123
  notebooklm generate video "a funny explainer for kids"
  notebooklm generate audio "deep dive focusing on chapter 3"
  notebooklm ask "what are the key themes?"
"""

import json
from pathlib import Path

import click
from rich.table import Table

from . import __version__
from .auth import (
    AuthTokens,
    load_auth_from_storage,
    fetch_tokens,
    DEFAULT_STORAGE_PATH,
)
from .client import NotebookLMClient
from .types import ChatMode

# Import command groups from cli package
from .cli import (
    source,
    artifact,
    generate,
    download,
    note,
)

# Import helpers
from .cli.helpers import (
    console,
    run_async,
    get_client,
    CONTEXT_FILE,
    BROWSER_PROFILE_DIR,
    get_current_notebook,
    set_current_notebook,
    clear_context,
    get_current_conversation,
    set_current_conversation,
    require_notebook,
    with_client,
    json_output_response,
    # Re-exported for backward compatibility with tests
    get_artifact_type_display,
    detect_source_type,
    ARTIFACT_TYPE_DISPLAY,
    ARTIFACT_TYPE_MAP,
)


# =============================================================================
# MAIN CLI GROUP
# =============================================================================


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
    """NotebookLM automation CLI.

    \b
    Quick start:
      notebooklm login              # Authenticate first
      notebooklm list               # List your notebooks
      notebooklm create "My Notes"  # Create a notebook
      notebooklm ask "Hi"           # Ask the current notebook a question

    \b
    Command groups:
      source     Source management (add, list, delete, refresh)
      artifact   Artifact management (list, get, delete, export)
      generate   Generate content (audio, video, quiz, slides, etc.)
      download   Download generated content
      note       Note management (create, list, edit, delete)
    """
    ctx.ensure_object(dict)
    ctx.obj["storage_path"] = Path(storage) if storage else None


# Register command groups
cli.add_command(source)
cli.add_command(artifact)
cli.add_command(generate)
cli.add_command(download)
cli.add_command(note)


# =============================================================================
# AUTHENTICATION & CONTEXT COMMANDS
# =============================================================================


@cli.command("login")
@click.option(
    "--storage",
    type=click.Path(),
    default=None,
    help=f"Where to save storage_state.json (default: {DEFAULT_STORAGE_PATH})",
)
def login(storage):
    """Log in to NotebookLM via browser.

    Opens a browser window for Google login. After logging in,
    press ENTER in the terminal to save authentication.
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
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    console.print("[yellow]Opening browser for Google login...[/yellow]")
    console.print(f"[dim]Using persistent profile: {BROWSER_PROFILE_DIR}[/dim]")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"],
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://notebooklm.google.com/")

        console.print("\n[bold green]Instructions:[/bold green]")
        console.print("1. Complete the Google login in the browser window")
        console.print("2. Wait until you see the NotebookLM homepage")
        console.print("3. Press [bold]ENTER[/bold] here to save and close\n")

        input("[Press ENTER when logged in] ")

        current_url = page.url
        if "notebooklm.google.com" not in current_url:
            console.print(f"[yellow]Warning: Current URL is {current_url}[/yellow]")
            if not click.confirm("Save authentication anyway?"):
                context.close()
                raise SystemExit(1)

        context.storage_state(path=str(storage_path))
        context.close()

    console.print(f"\n[green]Authentication saved to:[/green] {storage_path}")


@cli.command("use")
@click.argument("notebook_id")
@click.pass_context
def use_notebook(ctx, notebook_id):
    """Set the current notebook context.

    Once set, all commands will use this notebook by default.
    You can still override by passing --notebook explicitly.

    \b
    Example:
      notebooklm use nb123
      notebooklm ask "what is this about?"   # Uses nb123
      notebooklm generate video "a fun explainer"  # Uses nb123
    """
    try:
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _get():
            async with NotebookLMClient(auth) as client:
                return await client.notebooks.get(notebook_id)

        nb = run_async(_get())

        created_str = nb.created_at.strftime("%Y-%m-%d") if nb.created_at else None
        set_current_notebook(notebook_id, nb.title, nb.is_owner, created_str)

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Owner")
        table.add_column("Created", style="dim")

        created = created_str or "-"
        owner_status = "Owner" if nb.is_owner else "Shared"
        table.add_row(nb.id, nb.title, owner_status, created)

        console.print(table)

    except FileNotFoundError:
        set_current_notebook(notebook_id)
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Owner")
        table.add_column("Created", style="dim")
        table.add_row(notebook_id, "-", "-", "-")
        console.print(table)
    except Exception as e:
        set_current_notebook(notebook_id)
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Owner")
        table.add_column("Created", style="dim")
        table.add_row(notebook_id, f"Warning: {str(e)}", "-", "-")
        console.print(table)


@cli.command("status")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def status(json_output):
    """Show current context (active notebook and conversation)."""
    notebook_id = get_current_notebook()
    if notebook_id:
        try:
            data = json.loads(CONTEXT_FILE.read_text())
            title = data.get("title", "-")
            is_owner = data.get("is_owner", True)
            created_at = data.get("created_at", "-")
            conversation_id = data.get("conversation_id")

            if json_output:
                json_data = {
                    "has_context": True,
                    "notebook": {
                        "id": notebook_id,
                        "title": title if title != "-" else None,
                        "is_owner": is_owner,
                    },
                    "conversation_id": conversation_id,
                }
                json_output_response(json_data)
                return

            table = Table(title="Current Context")
            table.add_column("Property", style="dim")
            table.add_column("Value", style="cyan")

            table.add_row("Notebook ID", notebook_id)
            table.add_row("Title", str(title))
            owner_status = "Owner" if is_owner else "Shared"
            table.add_row("Ownership", owner_status)
            table.add_row("Created", created_at)
            if conversation_id:
                table.add_row("Conversation", conversation_id)
            else:
                table.add_row(
                    "Conversation", "[dim]None (will auto-select on next ask)[/dim]"
                )
            console.print(table)
        except (json.JSONDecodeError, IOError):
            if json_output:
                json_data = {
                    "has_context": True,
                    "notebook": {
                        "id": notebook_id,
                        "title": None,
                        "is_owner": None,
                    },
                    "conversation_id": None,
                }
                json_output_response(json_data)
                return

            table = Table(title="Current Context")
            table.add_column("Property", style="dim")
            table.add_column("Value", style="cyan")
            table.add_row("Notebook ID", notebook_id)
            table.add_row("Title", "-")
            table.add_row("Ownership", "-")
            table.add_row("Created", "-")
            table.add_row("Conversation", "[dim]None[/dim]")
            console.print(table)
    else:
        if json_output:
            json_data = {
                "has_context": False,
                "notebook": None,
                "conversation_id": None,
            }
            json_output_response(json_data)
            return

        console.print(
            "[yellow]No notebook selected. Use 'notebooklm use <id>' to set one.[/yellow]"
        )


@cli.command("clear")
def clear_cmd():
    """Clear current notebook context."""
    clear_context()
    console.print("[green]Context cleared[/green]")


# =============================================================================
# NOTEBOOK COMMANDS (promoted from notebook subcommand)
# =============================================================================


@cli.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def list_cmd(ctx, json_output, client_auth):
    """List all notebooks."""
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            notebooks = await client.notebooks.list()

            if json_output:
                data = {
                    "notebooks": [
                        {
                            "index": i,
                            "id": nb.id,
                            "title": nb.title,
                            "is_owner": nb.is_owner,
                            "created_at": nb.created_at.isoformat()
                            if nb.created_at
                            else None,
                        }
                        for i, nb in enumerate(notebooks, 1)
                    ],
                    "count": len(notebooks),
                }
                json_output_response(data)
                return

            table = Table(title="Notebooks")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Owner")
            table.add_column("Created", style="dim")

            for nb in notebooks:
                created = nb.created_at.strftime("%Y-%m-%d") if nb.created_at else "-"
                owner_status = "Owner" if nb.is_owner else "Shared"
                table.add_row(nb.id, nb.title, owner_status, created)

            console.print(table)

    return _run()


@cli.command("create")
@click.argument("title")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def create_cmd(ctx, title, json_output, client_auth):
    """Create a new notebook."""
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            nb = await client.notebooks.create(title)

            if json_output:
                data = {
                    "notebook": {
                        "id": nb.id,
                        "title": nb.title,
                        "created_at": nb.created_at.isoformat()
                        if nb.created_at
                        else None,
                    }
                }
                json_output_response(data)
                return

            console.print(f"[green]Created notebook:[/green] {nb.id} - {nb.title}")

    return _run()


@cli.command("delete")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@with_client
def delete_cmd(ctx, notebook_id, yes, client_auth):
    """Delete a notebook."""
    notebook_id = require_notebook(notebook_id)
    if not yes and not click.confirm(f"Delete notebook {notebook_id}?"):
        return

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            success = await client.notebooks.delete(notebook_id)
            if success:
                console.print(f"[green]Deleted notebook:[/green] {notebook_id}")
                # Clear context if we deleted the current notebook
                if get_current_notebook() == notebook_id:
                    clear_context()
                    console.print("[dim]Cleared current notebook context[/dim]")
            else:
                console.print("[yellow]Delete may have failed[/yellow]")

    return _run()


@cli.command("rename")
@click.argument("new_title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def rename_cmd(ctx, new_title, notebook_id, client_auth):
    """Rename a notebook."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            await client.notebooks.rename(notebook_id, new_title)
            console.print(f"[green]Renamed notebook:[/green] {notebook_id}")
            console.print(f"[bold]New title:[/bold] {new_title}")

    return _run()


@cli.command("share")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def share_cmd(ctx, notebook_id, client_auth):
    """Configure notebook sharing."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.notebooks.share(notebook_id)
            if result:
                console.print("[green]Sharing configured[/green]")
                console.print(result)
            else:
                console.print("[yellow]No sharing info returned[/yellow]")

    return _run()


@cli.command("summary")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--topics", is_flag=True, help="Include suggested topics")
@with_client
def summary_cmd(ctx, notebook_id, topics, client_auth):
    """Get notebook summary with AI-generated insights.

    \b
    Examples:
      notebooklm summary              # Summary only
      notebooklm summary --topics     # With suggested topics
    """
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            description = await client.notebooks.get_description(notebook_id)
            if description and description.summary:
                console.print("[bold cyan]Summary:[/bold cyan]")
                console.print(description.summary)

                if topics and description.suggested_topics:
                    console.print("\n[bold cyan]Suggested Topics:[/bold cyan]")
                    for i, topic in enumerate(description.suggested_topics, 1):
                        console.print(f"  {i}. {topic.question}")
            else:
                console.print("[yellow]No summary available[/yellow]")

    return _run()


@cli.command("analytics")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def analytics_cmd(ctx, notebook_id, client_auth):
    """Get notebook analytics."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            analytics = await client.notebooks.get_analytics(notebook_id)
            if analytics:
                console.print("[bold cyan]Analytics:[/bold cyan]")
                console.print(analytics)
            else:
                console.print("[yellow]No analytics available[/yellow]")

    return _run()


@cli.command("history")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--limit", "-l", default=20, help="Number of messages")
@click.option("--clear", "clear_cache", is_flag=True, help="Clear local conversation cache")
@with_client
def history_cmd(ctx, notebook_id, limit, clear_cache, client_auth):
    """Get conversation history or clear local cache.

    \b
    Example:
      notebooklm history              # Show history for current notebook
      notebooklm history -n nb123     # Show history for specific notebook
      notebooklm history --clear      # Clear local cache
    """
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            if clear_cache:
                result = client.chat.clear_cache()
                if result:
                    console.print("[green]Local conversation cache cleared[/green]")
                else:
                    console.print("[yellow]No cache to clear[/yellow]")
                return

            nb_id = require_notebook(notebook_id)
            history = await client.chat.get_history(nb_id, limit=limit)

            if history:
                console.print("[bold cyan]Conversation History:[/bold cyan]")
                try:
                    conversations = history[0] if history else []
                    if conversations:
                        table = Table()
                        table.add_column("#", style="dim")
                        table.add_column("Conversation ID", style="cyan")
                        for i, conv in enumerate(conversations, 1):
                            conv_id = (
                                conv[0] if isinstance(conv, list) and conv else str(conv)
                            )
                            table.add_row(str(i), conv_id)
                        console.print(table)
                        console.print(
                            "\n[dim]Note: Only conversation IDs available. Use 'notebooklm ask -c <id>' to continue.[/dim]"
                        )
                    else:
                        console.print("[yellow]No conversations found[/yellow]")
                except (IndexError, TypeError):
                    console.print(history)
            else:
                console.print("[yellow]No conversation history[/yellow]")

    return _run()


@cli.command("ask")
@click.argument("question")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--conversation-id", "-c", default=None, help="Continue a specific conversation"
)
@click.option(
    "--new", "new_conversation", is_flag=True, help="Start a new conversation"
)
@with_client
def ask_cmd(ctx, question, notebook_id, conversation_id, new_conversation, client_auth):
    """Ask a notebook a question.

    By default, continues the last conversation. Use --new to start fresh.

    \b
    Example:
      notebooklm ask "what are the main themes?"
      notebooklm ask --new "start fresh question"
      notebooklm ask -c <id> "continue this one"
    """
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            effective_conv_id = None
            if new_conversation:
                effective_conv_id = None
                console.print("[dim]Starting new conversation...[/dim]")
            elif conversation_id:
                effective_conv_id = conversation_id
            else:
                effective_conv_id = get_current_conversation()
                if not effective_conv_id:
                    try:
                        history = await client.chat.get_history(nb_id, limit=1)
                        if history and history[0]:
                            last_conv = history[0][-1]
                            effective_conv_id = (
                                last_conv[0]
                                if isinstance(last_conv, list)
                                else str(last_conv)
                            )
                            console.print(
                                f"[dim]Continuing conversation {effective_conv_id[:8]}...[/dim]"
                            )
                    except Exception:
                        pass

            result = await client.chat.ask(
                nb_id, question, conversation_id=effective_conv_id
            )

            if result.get("conversation_id"):
                set_current_conversation(result["conversation_id"])

            console.print("[bold cyan]Answer:[/bold cyan]")
            console.print(result["answer"])
            if result.get("is_follow_up"):
                console.print(
                    f"\n[dim]Conversation: {result['conversation_id']} (turn {result.get('turn_number', '?')})[/dim]"
                )
            else:
                console.print(f"\n[dim]New conversation: {result['conversation_id']}[/dim]")

    return _run()


@cli.command("configure")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--mode",
    "chat_mode",
    type=click.Choice(["default", "learning-guide", "concise", "detailed"]),
    default=None,
    help="Predefined chat mode",
)
@click.option(
    "--persona", default=None, help="Custom persona prompt (up to 10,000 chars)"
)
@click.option(
    "--response-length",
    type=click.Choice(["default", "longer", "shorter"]),
    default=None,
    help="Response verbosity",
)
@with_client
def configure_cmd(ctx, notebook_id, chat_mode, persona, response_length, client_auth):
    """Configure chat persona and response settings.

    \b
    Modes:
      default        General purpose (default behavior)
      learning-guide Educational focus with learning-oriented responses
      concise        Brief, to-the-point responses
      detailed       Verbose, comprehensive responses

    \b
    Examples:
      notebooklm configure --mode learning-guide
      notebooklm configure --persona "Act as a chemistry tutor"
      notebooklm configure --mode detailed --response-length longer
    """
    nb_id = require_notebook(notebook_id)

    async def _run():
        from .rpc import ChatGoal, ChatResponseLength

        async with NotebookLMClient(client_auth) as client:
            if chat_mode:
                mode_map = {
                    "default": ChatMode.DEFAULT,
                    "learning-guide": ChatMode.LEARNING_GUIDE,
                    "concise": ChatMode.CONCISE,
                    "detailed": ChatMode.DETAILED,
                }
                await client.chat.set_mode(nb_id, mode_map[chat_mode])
                console.print(f"[green]Chat mode set to: {chat_mode}[/green]")
                return

            goal = ChatGoal.CUSTOM if persona else None
            length = None
            if response_length:
                length_map = {
                    "default": ChatResponseLength.DEFAULT,
                    "longer": ChatResponseLength.LONGER,
                    "shorter": ChatResponseLength.SHORTER,
                }
                length = length_map[response_length]

            await client.chat.configure(
                nb_id, goal=goal, response_length=length, custom_prompt=persona
            )

            parts = []
            if persona:
                parts.append(
                    f'persona: "{persona[:50]}..."'
                    if len(persona) > 50
                    else f'persona: "{persona}"'
                )
            if response_length:
                parts.append(f"response length: {response_length}")
            result = (
                f"Chat configured: {', '.join(parts)}"
                if parts
                else "Chat configured (no changes)"
            )
            console.print(f"[green]{result}[/green]")

    return _run()


@cli.command("research")
@click.argument("query")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--source", type=click.Choice(["web", "drive"]), default="web")
@click.option("--mode", type=click.Choice(["fast", "deep"]), default="fast")
@click.option("--import-all", is_flag=True, help="Import all found sources")
@with_client
def research_cmd(ctx, query, notebook_id, source, mode, import_all, client_auth):
    """Start a research session."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        import time

        async with NotebookLMClient(client_auth) as client:
            console.print(
                f"[yellow]Starting {mode} research on {source}...[/yellow]"
            )
            result = await client.research.start(notebook_id, query, source, mode)
            if not result:
                console.print("[red]Research failed to start[/red]")
                raise SystemExit(1)

            task_id = result["task_id"]
            console.print(f"[dim]Task ID: {task_id}[/dim]")

            status = None
            for _ in range(60):
                status = await client.research.poll(notebook_id)
                if status.get("status") == "completed":
                    break
                elif status.get("status") == "no_research":
                    console.print("[red]Research failed to start[/red]")
                    raise SystemExit(1)
                time.sleep(5)
            else:
                status = {"status": "timeout"}

            if status.get("status") == "completed":
                sources = status.get("sources", [])
                console.print(f"\n[green]Found {len(sources)} sources[/green]")

                if import_all and sources and task_id:
                    imported = await client.research.import_sources(
                        notebook_id, task_id, sources
                    )
                    console.print(f"[green]Imported {len(imported)} sources[/green]")
            else:
                console.print(f"[yellow]Status: {status.get('status', 'unknown')}[/yellow]")

    return _run()


@cli.command("featured")
@click.option("--limit", "-n", default=20, help="Number of notebooks")
@with_client
def featured_cmd(ctx, limit, client_auth):
    """List featured/public notebooks."""
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            projects = await client.notebooks.list_featured(page_size=limit)

            if not projects:
                console.print("[yellow]No featured notebooks found[/yellow]")
                return

            table = Table(title="Featured Notebooks")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")

            for proj in projects:
                if isinstance(proj, list) and len(proj) > 0:
                    table.add_row(
                        str(proj[0] or "-"), str(proj[1] if len(proj) > 1 else "-")
                    )

            console.print(table)

    return _run()


@cli.command("share-audio")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--public/--private", default=False, help="Make audio public or private")
@with_client
def share_audio_cmd(ctx, notebook_id, public, client_auth):
    """Share or unshare audio overview."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.share_audio(nb_id, public=public)

            if result:
                status = "public" if public else "private"
                console.print(f"[green]Audio is now {status}[/green]")
                console.print(result)
            else:
                console.print("[yellow]Share returned no result[/yellow]")

    return _run()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    cli()


if __name__ == "__main__":
    main()
