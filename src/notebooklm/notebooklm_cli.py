"""CLI interface for NotebookLM automation.

Command structure:
  notebooklm login                    # Authenticate
  notebooklm use <notebook_id>        # Set current notebook context
  notebooklm status                   # Show current context
  notebooklm list                     # List notebooks (shortcut)
  notebooklm create <title>           # Create notebook (shortcut)
  notebooklm ask <question>           # Ask the current notebook a question

  notebooklm notebook <command>       # Notebook operations
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
from datetime import datetime
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
from .types import (
    Notebook,
    Source,
    Artifact,
    Note,
    ChatMode,
    AudioFormat,
    AudioLength,
    VideoFormat,
    VideoStyle,
    QuizQuantity,
    QuizDifficulty,
    InfographicOrientation,
    InfographicDetail,
    SlideDeckFormat,
    SlideDeckLength,
    ReportFormat,
)

# Import helpers from cli package (these are re-exported for backward compatibility)
from .cli.helpers import (
    console,
    run_async,
    get_client,
    get_auth_tokens,
    CONTEXT_FILE,
    BROWSER_PROFILE_DIR,
    get_current_notebook,
    set_current_notebook,
    clear_context,
    get_current_conversation,
    set_current_conversation,
    require_notebook,
    handle_error,
    handle_auth_error,
    with_client,
    json_output_response,
    json_error_response,
    ARTIFACT_TYPE_DISPLAY,
    ARTIFACT_TYPE_MAP,
    get_artifact_type_display,
    detect_source_type,
    get_source_type_display,
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
      notebook   Notebook management (list, create, delete, rename, share)
      source     Source management (add, list, delete, refresh)
      artifact   Artifact management (list, get, delete, export)
      generate   Generate content (audio, video, quiz, slides, etc.)
      download   Download generated content
      note       Note management (create, list, edit, delete)
    """
    ctx.ensure_object(dict)
    ctx.obj["storage_path"] = Path(storage) if storage else None


# =============================================================================
# TOP-LEVEL CONVENIENCE COMMANDS
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
        owner_status = "👤 Owner" if nb.is_owner else "👥 Shared"
        table.add_row(nb.id, nb.title, owner_status, created)

        console.print(table)

    except FileNotFoundError:
        # Allow setting context even without auth (might be used later)
        set_current_notebook(notebook_id)
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Owner")
        table.add_column("Created", style="dim")
        table.add_row(notebook_id, "-", "-", "-")
        console.print(table)
    except Exception as e:
        # Still set context even if we can't verify the notebook
        set_current_notebook(notebook_id)
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Owner")
        table.add_column("Created", style="dim")
        table.add_row(notebook_id, f"⚠️  {str(e)}", "-", "-")
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


@cli.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def list_notebooks_shortcut(ctx, json_output, client_auth):
    """List all notebooks (shortcut for 'notebook list')."""
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
                owner_status = "👤 Owner" if nb.is_owner else "👥 Shared"
                table.add_row(nb.id, nb.title, owner_status, created)

            console.print(table)

    return _run()


@cli.command("create")
@click.argument("title")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def create_notebook_shortcut(ctx, title, json_output, client_auth):
    """Create a new notebook (shortcut for 'notebook create')."""
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            notebook = await client.notebooks.create(title)

            if json_output:
                data = {
                    "notebook": {
                        "id": notebook.id,
                        "title": notebook.title,
                        "created_at": notebook.created_at.isoformat()
                        if notebook.created_at
                        else None,
                    }
                }
                json_output_response(data)
                return

            console.print(
                f"[green]Created notebook:[/green] {notebook.id} - {notebook.title}"
            )

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
def ask_shortcut(ctx, question, notebook_id, conversation_id, new_conversation, client_auth):
    """Ask a notebook a question (shortcut for 'notebook ask').

    By default, continues the last conversation. Use --new to start fresh.

    \b
    Example:
      notebooklm ask "what are the main themes?"    # Auto-continues last conversation
      notebooklm ask --new "start fresh question"   # Force new conversation
      notebooklm ask -c <id> "continue this one"    # Continue specific conversation
    """
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            # Determine conversation_id to use
            effective_conv_id = None
            if new_conversation:
                # Force new conversation
                effective_conv_id = None
                console.print("[dim]Starting new conversation...[/dim]")
            elif conversation_id:
                # User specified a conversation ID
                effective_conv_id = conversation_id
            else:
                # Try to auto-continue: check context first, then history
                effective_conv_id = get_current_conversation()
                if not effective_conv_id:
                    # Query history to get the last conversation
                    try:
                        history = await client.chat.get_history(nb_id, limit=1)
                        # Parse: [[['conv_id'], ...]]
                        if history and history[0]:
                            last_conv = history[0][-1]  # Get last conversation
                            effective_conv_id = (
                                last_conv[0]
                                if isinstance(last_conv, list)
                                else str(last_conv)
                            )
                            console.print(
                                f"[dim]Continuing conversation {effective_conv_id[:8]}...[/dim]"
                            )
                    except Exception:
                        # History fetch failed, start new conversation
                        pass

            result = await client.chat.ask(
                nb_id, question, conversation_id=effective_conv_id
            )

            # Save conversation_id to context for future asks
            if result.get("conversation_id"):
                set_current_conversation(result["conversation_id"])

            console.print(f"[bold cyan]Answer:[/bold cyan]")
            console.print(result["answer"])
            if result.get("is_follow_up"):
                console.print(
                    f"\n[dim]Conversation: {result['conversation_id']} (turn {result.get('turn_number', '?')})[/dim]"
                )
            else:
                console.print(f"\n[dim]New conversation: {result['conversation_id']}[/dim]")

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
@click.option("--clear", is_flag=True, help="Clear local conversation cache")
@with_client
def history_shortcut(ctx, notebook_id, limit, clear, client_auth):
    """View conversation history or clear local cache (shortcut for 'notebook history').

    \b
    Example:
      notebooklm history                  # Show history for current notebook
      notebooklm history --limit 5        # Show last 5 messages
      notebooklm history --clear          # Clear local cache
    """
    async def _run():
        async with NotebookLMClient(client_auth) as client:
            if clear:
                # Clear local cache (no notebook required)
                result = client.chat.clear_cache()
                if result:
                    console.print("[green]Local conversation cache cleared[/green]")
                else:
                    console.print("[yellow]No cache to clear[/yellow]")
                return

            # Get history from server
            nb_id = require_notebook(notebook_id)
            history = await client.chat.get_history(nb_id, limit=limit)

            if history:
                console.print(f"[bold cyan]Conversation History:[/bold cyan]")
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
                            f"\n[dim]Note: Only conversation IDs available. Use 'notebooklm ask -c <id>' to continue.[/dim]"
                        )
                    else:
                        console.print("[yellow]No conversations found[/yellow]")
                except (IndexError, TypeError):
                    # Fallback: show raw data if parsing fails
                    console.print(history)
            else:
                console.print("[yellow]No conversation history[/yellow]")

    return _run()


# =============================================================================
# NOTEBOOK GROUP
# =============================================================================


@cli.group()
def notebook():
    """Notebook management commands.

    \b
    Commands:
      list       List all notebooks
      create     Create a new notebook
      delete     Delete a notebook
      rename     Rename a notebook
      share      Share a notebook
      ask        Ask a question
      summary    Get notebook summary
      analytics  Get notebook analytics
      history    Get conversation history
    """
    pass


@notebook.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def notebook_list(ctx, json_output):
    """List all notebooks."""
    ctx.invoke(list_notebooks_shortcut, json_output=json_output)


@notebook.command("create")
@click.argument("title")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def notebook_create(ctx, title, json_output):
    """Create a new notebook."""
    ctx.invoke(create_notebook_shortcut, title=title, json_output=json_output)


@notebook.command("delete")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@with_client
def notebook_delete(ctx, notebook_id, yes, client_auth):
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


@notebook.command("rename")
@click.argument("new_title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def notebook_rename(ctx, new_title, notebook_id, client_auth):
    """Rename a notebook."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            await client.notebooks.rename(notebook_id, new_title)
            console.print(f"[green]Renamed notebook:[/green] {notebook_id}")
            console.print(f"[bold]New title:[/bold] {new_title}")

    return _run()


@notebook.command("share")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def notebook_share(ctx, notebook_id, client_auth):
    """Configure notebook sharing."""
    notebook_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.notebooks.share(notebook_id)
            if result:
                console.print(f"[green]Sharing configured[/green]")
                console.print(result)
            else:
                console.print("[yellow]No sharing info returned[/yellow]")

    return _run()


@notebook.command("summary")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--topics", is_flag=True, help="Include suggested topics")
@with_client
def notebook_summary(ctx, notebook_id, topics, client_auth):
    """Get notebook summary with AI-generated insights.

    \b
    Examples:
      notebooklm notebook summary              # Summary only
      notebooklm notebook summary --topics     # With suggested topics
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


@notebook.command("analytics")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def notebook_analytics(ctx, notebook_id, client_auth):
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


@notebook.command("history")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--limit", "-l", default=20, help="Number of messages")
@click.option("--clear", is_flag=True, help="Clear local conversation cache")
@click.pass_context
def notebook_history(ctx, notebook_id, limit, clear):
    """Get conversation history or clear local cache.

    \b
    Example:
      notebooklm notebook history              # Show history for current notebook
      notebooklm notebook history -n nb123     # Show history for specific notebook
      notebooklm notebook history --clear      # Clear local cache
    """
    ctx.invoke(history_shortcut, notebook_id=notebook_id, limit=limit, clear=clear)


@notebook.command("ask")
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
@click.pass_context
def notebook_ask(ctx, question, notebook_id, conversation_id, new_conversation):
    """Ask a notebook a question."""
    ctx.invoke(
        ask_shortcut,
        notebook_id=notebook_id,
        question=question,
        conversation_id=conversation_id,
        new_conversation=new_conversation,
    )


@notebook.command("configure")
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
def notebook_configure(ctx, notebook_id, chat_mode, persona, response_length, client_auth):
    """Configure chat persona and response settings.

    \b
    Modes:
      default        General purpose (default behavior)
      learning-guide Educational focus with learning-oriented responses
      concise        Brief, to-the-point responses
      detailed       Verbose, comprehensive responses

    \b
    Examples:
      notebooklm notebook configure --mode learning-guide
      notebooklm notebook configure --persona "Act as a chemistry tutor"
      notebooklm notebook configure --mode detailed --response-length longer
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


@notebook.command("research")
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
def notebook_research(ctx, query, notebook_id, source, mode, import_all, client_auth):
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

            # Poll for completion
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


@notebook.command("featured")
@click.option("--limit", "-n", default=20, help="Number of notebooks")
@with_client
def notebook_featured(ctx, limit, client_auth):
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


# =============================================================================
# SOURCE GROUP
# =============================================================================


@cli.group()
def source():
    """Source management commands.

    \b
    Commands:
      list      List sources in a notebook
      add       Add a source (url, text, file, youtube)
      get       Get source details
      delete    Delete a source
      rename    Rename a source
      refresh   Refresh a URL/Drive source
    """
    pass


@source.command("list")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def source_list(ctx, notebook_id, json_output, client_auth):
    """List all sources in a notebook."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            sources = await client.sources.list(nb_id)
            nb = None
            if json_output:
                nb = await client.notebooks.get(nb_id)

            if json_output:
                data = {
                    "notebook_id": nb_id,
                    "notebook_title": nb.title if nb else None,
                    "sources": [
                        {
                            "index": i,
                            "id": src.id,
                            "title": src.title,
                            "type": src.source_type,
                            "url": src.url,
                            "created_at": src.created_at.isoformat()
                            if src.created_at
                            else None,
                        }
                        for i, src in enumerate(sources, 1)
                    ],
                    "count": len(sources),
                }
                json_output_response(data)
                return

            table = Table(title=f"Sources in {nb_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Type")
            table.add_column("Created", style="dim")

            for src in sources:
                type_display = get_source_type_display(src.source_type)
                created = (
                    src.created_at.strftime("%Y-%m-%d %H:%M") if src.created_at else "-"
                )
                table.add_row(src.id, src.title or "-", type_display, created)

            console.print(table)

    return _run()


@source.command("add")
@click.argument("content")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--type",
    "source_type",
    type=click.Choice(["url", "text", "file", "youtube"]),
    default=None,
    help="Source type (auto-detected if not specified)",
)
@click.option("--title", help="Title for text sources")
@click.option("--mime-type", help="MIME type for file sources")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def source_add(ctx, content, notebook_id, source_type, title, mime_type, json_output, client_auth):
    """Add a source to a notebook.

    \b
    Source type is auto-detected:
      - URLs (http/https) → url or youtube
      - Existing files (.txt, .md) → text
      - Other content → text (inline)
      - Use --type to override

    \b
    Examples:
      source add https://example.com              # URL
      source add ./doc.md                         # File content as text
      source add https://youtube.com/...          # YouTube video
      source add "My notes here"                  # Inline text
      source add "My notes" --title "Research"   # Text with custom title
    """
    nb_id = require_notebook(notebook_id)

    # Auto-detect source type if not specified
    detected_type = source_type
    file_content = None  # For text-based files
    file_title = title

    if detected_type is None:
        if content.startswith(("http://", "https://")):
            # Check for YouTube URLs
            if "youtube.com" in content or "youtu.be" in content:
                detected_type = "youtube"
            else:
                detected_type = "url"
        elif Path(content).exists():
            file_path = Path(content)
            suffix = file_path.suffix.lower()
            # Text-based files: read content and add as text (workaround for broken file upload RPC)
            if suffix in (".txt", ".md", ".markdown", ".rst", ".text"):
                detected_type = "text"
                file_content = file_path.read_text()
                file_title = title or file_path.name
            else:
                detected_type = "file"
        else:
            # Not a URL, not a file → treat as inline text content
            detected_type = "text"
            file_title = title or "Pasted Text"

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            if detected_type == "url":
                source = await client.sources.add_url(nb_id, content)
            elif detected_type == "youtube":
                source = await client.sources.add_url(nb_id, content)
            elif detected_type == "text":
                # Use file_content if we read from a file, otherwise use content directly
                text_content = file_content if file_content is not None else content
                text_title = file_title or "Untitled"
                source = await client.sources.add_text(nb_id, text_title, text_content)
            elif detected_type == "file":
                source = await client.sources.add_file(nb_id, content, mime_type)

            if json_output:
                data = {
                    "source": {
                        "id": source.id,
                        "title": source.title,
                        "type": source.source_type,
                        "url": source.url,
                    }
                }
                json_output_response(data)
                return

            console.print(f"[green]Added source:[/green] {source.id}")

    if not json_output:
        with console.status(f"Adding {detected_type} source..."):
            return _run()
    return _run()


@source.command("get")
@click.argument("source_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def source_get(ctx, source_id, notebook_id, client_auth):
    """Get source details."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            source = await client.sources.get(nb_id, source_id)
            if source:
                console.print(f"[bold cyan]Source:[/bold cyan] {source.id}")
                console.print(f"[bold]Title:[/bold] {source.title}")
                console.print(
                    f"[bold]Type:[/bold] {get_source_type_display(source.source_type)}"
                )
                if source.url:
                    console.print(f"[bold]URL:[/bold] {source.url}")
                if source.created_at:
                    console.print(
                        f"[bold]Created:[/bold] {source.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
            else:
                console.print("[yellow]Source not found[/yellow]")

    return _run()


@source.command("delete")
@click.argument("source_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@with_client
def source_delete(ctx, source_id, notebook_id, yes, client_auth):
    """Delete a source."""
    if not yes and not click.confirm(f"Delete source {source_id}?"):
        return

    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            success = await client.sources.delete(nb_id, source_id)
            if success:
                console.print(f"[green]Deleted source:[/green] {source_id}")
            else:
                console.print("[yellow]Delete may have failed[/yellow]")

    return _run()


@source.command("rename")
@click.argument("source_id")
@click.argument("new_title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def source_rename(ctx, source_id, new_title, notebook_id, client_auth):
    """Rename a source."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            source = await client.sources.rename(nb_id, source_id, new_title)
            console.print(f"[green]Renamed source:[/green] {source.id}")
            console.print(f"[bold]New title:[/bold] {source.title}")

    return _run()


@source.command("refresh")
@click.argument("source_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def source_refresh(ctx, source_id, notebook_id, client_auth):
    """Refresh a URL/Drive source."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            with console.status("Refreshing source..."):
                source = await client.sources.refresh(nb_id, source_id)

            if source:
                console.print(f"[green]Source refreshed:[/green] {source.id}")
                console.print(f"[bold]Title:[/bold] {source.title}")
            else:
                console.print("[yellow]Refresh returned no result[/yellow]")

    return _run()


@source.command("add-drive")
@click.argument("file_id")
@click.argument("title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--mime-type",
    type=click.Choice(["google-doc", "google-slides", "google-sheets", "pdf"]),
    default="google-doc",
    help="Document type (default: google-doc)",
)
@with_client
def source_add_drive(ctx, file_id, title, notebook_id, mime_type, client_auth):
    """Add a Google Drive document as a source."""
    from .rpc import DriveMimeType

    nb_id = require_notebook(notebook_id)
    mime_map = {
        "google-doc": DriveMimeType.GOOGLE_DOC.value,
        "google-slides": DriveMimeType.GOOGLE_SLIDES.value,
        "google-sheets": DriveMimeType.GOOGLE_SHEETS.value,
        "pdf": DriveMimeType.PDF.value,
    }
    mime = mime_map[mime_type]

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            with console.status("Adding Drive source..."):
                source = await client.sources.add_drive(nb_id, file_id, title, mime)

            console.print(f"[green]Added Drive source:[/green] {source.id}")
            console.print(f"[bold]Title:[/bold] {source.title}")

    return _run()


# =============================================================================
# ARTIFACT GROUP
# =============================================================================


@cli.group()
def artifact():
    """Artifact management commands.

    \b
    Commands:
      list      List all artifacts (or by type)
      get       Get artifact details
      rename    Rename an artifact
      delete    Delete an artifact
      export    Export to Google Docs/Sheets
      poll      Poll generation status
    """
    pass


@artifact.command("list")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--type",
    "artifact_type",
    type=click.Choice(
        [
            "all",
            "video",
            "slide-deck",
            "quiz",
            "flashcard",
            "infographic",
            "data-table",
            "mind-map",
            "report",
        ]
    ),
    default="all",
    help="Filter by type",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def artifact_list(ctx, notebook_id, artifact_type, json_output, client_auth):
    """List artifacts in a notebook."""
    nb_id = require_notebook(notebook_id)
    type_filter = (
        None if artifact_type == "all" else ARTIFACT_TYPE_MAP.get(artifact_type)
    )

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            artifacts = await client.artifacts.list(nb_id, artifact_type=type_filter)

            # Also fetch mind maps (stored separately with notes)
            if type_filter is None or type_filter == 5:
                mind_maps = await client.notes.list_mind_maps(nb_id)
                for mm in mind_maps:
                    if isinstance(mm, list) and len(mm) > 0:
                        mm_id = mm[0] if len(mm) > 0 else ""
                        title = "Mind Map"
                        if (
                            len(mm) > 1
                            and isinstance(mm[1], list)
                            and len(mm[1]) > 4
                        ):
                            title = mm[1][4] or "Mind Map"
                        mm_artifact = Artifact(
                            id=str(mm_id),
                            title=str(title),
                            artifact_type=5,
                            status=3,
                            created_at=None,
                            variant=None,
                        )
                        artifacts.append(mm_artifact)

            nb = None
            if json_output:
                nb = await client.notebooks.get(nb_id)

            if json_output:
                def _get_status_str(art):
                    if art.is_completed:
                        return "completed"
                    elif art.is_processing:
                        return "processing"
                    return str(art.status)

                data = {
                    "notebook_id": nb_id,
                    "notebook_title": nb.title if nb else None,
                    "artifacts": [
                        {
                            "index": i,
                            "id": art.id,
                            "title": art.title,
                            "type": get_artifact_type_display(
                                art.artifact_type, art.variant, art.report_subtype
                            ).split(" ", 1)[-1],
                            "type_id": art.artifact_type,
                            "status": _get_status_str(art),
                            "status_id": art.status,
                            "created_at": art.created_at.isoformat()
                            if art.created_at
                            else None,
                        }
                        for i, art in enumerate(artifacts, 1)
                    ],
                    "count": len(artifacts),
                }
                json_output_response(data)
                return

            if not artifacts:
                console.print(f"[yellow]No {artifact_type} artifacts found[/yellow]")
                return

            table = Table(title=f"Artifacts in {nb_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Type")
            table.add_column("Created", style="dim")
            table.add_column("Status", style="yellow")

            for art in artifacts:
                type_display = get_artifact_type_display(
                    art.artifact_type, art.variant, art.report_subtype
                )
                created = (
                    art.created_at.strftime("%Y-%m-%d %H:%M") if art.created_at else "-"
                )
                status = (
                    "completed"
                    if art.is_completed
                    else "processing"
                    if art.is_processing
                    else str(art.status)
                )
                table.add_row(art.id, art.title, type_display, created, status)

            console.print(table)

    return _run()


@artifact.command("get")
@click.argument("artifact_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def artifact_get(ctx, artifact_id, notebook_id, client_auth):
    """Get artifact details."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            artifact = await client.artifacts.get(nb_id, artifact_id)
            if artifact:
                console.print(f"[bold cyan]Artifact:[/bold cyan] {artifact.id}")
                console.print(f"[bold]Title:[/bold] {artifact.title}")
                console.print(
                    f"[bold]Type:[/bold] {get_artifact_type_display(artifact.artifact_type, artifact.variant, artifact.report_subtype)}"
                )
                console.print(
                    f"[bold]Status:[/bold] {'completed' if artifact.is_completed else 'processing' if artifact.is_processing else str(artifact.status)}"
                )
                if artifact.created_at:
                    console.print(
                        f"[bold]Created:[/bold] {artifact.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
            else:
                console.print("[yellow]Artifact not found[/yellow]")

    return _run()


@artifact.command("rename")
@click.argument("artifact_id")
@click.argument("new_title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def artifact_rename(ctx, artifact_id, new_title, notebook_id, client_auth):
    """Rename an artifact."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            # Check if this is a mind map (stored with notes, not artifacts)
            mind_maps = await client.notes.list_mind_maps(nb_id)
            for mm in mind_maps:
                if mm[0] == artifact_id:
                    raise click.ClickException("Mind maps cannot be renamed")

            artifact = await client.artifacts.rename(nb_id, artifact_id, new_title)
            console.print(f"[green]Renamed artifact:[/green] {artifact.id}")
            console.print(f"[bold]New title:[/bold] {artifact.title}")

    return _run()


@artifact.command("delete")
@click.argument("artifact_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@with_client
def artifact_delete(ctx, artifact_id, notebook_id, yes, client_auth):
    """Delete an artifact."""
    if not yes and not click.confirm(f"Delete artifact {artifact_id}?"):
        return

    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            # Check if this is a mind map (stored with notes)
            mind_maps = await client.notes.list_mind_maps(nb_id)
            for mm in mind_maps:
                if mm[0] == artifact_id:
                    await client.notes.delete(nb_id, artifact_id)
                    console.print(f"[yellow]Cleared mind map:[/yellow] {artifact_id}")
                    console.print(
                        "[dim]Note: Mind maps are cleared, not removed. Google may garbage collect them later.[/dim]"
                    )
                    return

            await client.artifacts.delete(nb_id, artifact_id)
            console.print(f"[green]Deleted artifact:[/green] {artifact_id}")

    return _run()


@artifact.command("export")
@click.argument("artifact_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--title", required=True, help="Title for exported document")
@click.option(
    "--type", "export_type", type=click.Choice(["docs", "sheets"]), default="docs"
)
@with_client
def artifact_export(ctx, artifact_id, notebook_id, title, export_type, client_auth):
    """Export artifact to Google Docs/Sheets."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            artifact = await client.artifacts.get(nb_id, artifact_id)
            content = str(artifact) if artifact else ""
            result = await client.artifacts.export(
                nb_id, artifact_id, content, title, export_type
            )
            if result:
                console.print(f"[green]Exported to Google {export_type.title()}[/green]")
                console.print(result)
            else:
                console.print("[yellow]Export may have failed[/yellow]")

    return _run()


@artifact.command("poll")
@click.argument("task_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def artifact_poll(ctx, task_id, notebook_id, client_auth):
    """Poll generation status."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            status = await client.artifacts.poll_status(nb_id, task_id)
            console.print("[bold cyan]Task Status:[/bold cyan]")
            console.print(status)

    return _run()


@artifact.command("suggestions")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--source", "source_ids", multiple=True, help="Limit to specific sources")
@click.option("--json", "json_output", is_flag=True, help="Output JSON format")
@with_client
def artifact_suggestions(ctx, notebook_id, source_ids, json_output, client_auth):
    """Get AI-suggested report topics based on notebook content."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            ids = list(source_ids) if source_ids else None
            suggestions = await client.artifacts.suggest_reports(nb_id, ids)

            if not suggestions:
                console.print("[yellow]No suggestions available[/yellow]")
                return

            if json_output:
                data = [
                    {"title": s.title, "description": s.description, "prompt": s.prompt}
                    for s in suggestions
                ]
                console.print(json.dumps(data, indent=2))
                return

            table = Table(title="Suggested Reports")
            table.add_column("#", style="dim")
            table.add_column("Title", style="green")
            table.add_column("Description")

            for i, suggestion in enumerate(suggestions, 1):
                table.add_row(str(i), suggestion.title, suggestion.description)

            console.print(table)
            console.print(
                '\n[dim]Use the prompt with: notebooklm generate report "<prompt>"[/dim]'
            )

    return _run()


# =============================================================================
# GENERATE GROUP
# =============================================================================


@cli.group()
def generate():
    """Generate content from notebook.

    \b
    LLM-friendly design: Describe what you want in natural language.

    \b
    Examples:
      notebooklm use nb123
      notebooklm generate video "a funny explainer for kids age 5"
      notebooklm generate audio "deep dive focusing on chapter 3"
      notebooklm generate quiz "focus on vocabulary terms"

    \b
    Types:
      audio        Audio overview (podcast)
      video        Video overview
      slide-deck   Slide deck
      quiz         Quiz
      flashcards   Flashcards
      infographic  Infographic
      data-table   Data table
      mind-map     Mind map
      report       Report (briefing-doc, study-guide, blog-post, custom)
    """
    pass


@generate.command("audio")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--format",
    "audio_format",
    type=click.Choice(["deep-dive", "brief", "critique", "debate"]),
    default="deep-dive",
)
@click.option(
    "--length",
    "audio_length",
    type=click.Choice(["short", "default", "long"]),
    default="default",
)
@click.option("--language", default="en")
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def generate_audio(
    ctx,
    description,
    notebook_id,
    audio_format,
    audio_length,
    language,
    wait,
    json_output,
    client_auth,
):
    """Generate audio overview (podcast).

    \b
    Example:
      notebooklm generate audio "deep dive focusing on key themes"
      notebooklm generate audio "make it funny and casual" --format debate
    """
    nb_id = require_notebook(notebook_id)
    format_map = {
        "deep-dive": AudioFormat.DEEP_DIVE,
        "brief": AudioFormat.BRIEF,
        "critique": AudioFormat.CRITIQUE,
        "debate": AudioFormat.DEBATE,
    }
    length_map = {
        "short": AudioLength.SHORT,
        "default": AudioLength.DEFAULT,
        "long": AudioLength.LONG,
    }

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_audio(
                nb_id,
                language=language,
                instructions=description or None,
                audio_format=format_map[audio_format],
                audio_length=length_map[audio_length],
            )

            if not result:
                if json_output:
                    json_error_response("GENERATION_FAILED", "Audio generation failed")
                else:
                    console.print("[red]Audio generation failed[/red]")
                return

            if wait:
                if not json_output:
                    console.print(
                        f"[yellow]Generating audio...[/yellow] Task: {result.get('artifact_id')}"
                    )
                status = await client.artifacts.wait_for_completion(
                    nb_id, result["artifact_id"], poll_interval=10.0
                )
            else:
                status = result

            if json_output:
                if hasattr(status, "is_complete") and status.is_complete:
                    data = {
                        "artifact_id": status.artifact_id
                        if hasattr(status, "artifact_id")
                        else None,
                        "status": "completed",
                        "url": status.url,
                    }
                    json_output_response(data)
                elif hasattr(status, "is_failed") and status.is_failed:
                    json_error_response(
                        "GENERATION_FAILED", status.error or "Audio generation failed"
                    )
                else:
                    artifact_id = (
                        status.get("artifact_id") if isinstance(status, dict) else None
                    )
                    json_output_response({"artifact_id": artifact_id, "status": "pending"})
            else:
                if hasattr(status, "is_complete") and status.is_complete:
                    console.print(f"[green]Audio ready:[/green] {status.url}")
                elif hasattr(status, "is_failed") and status.is_failed:
                    console.print(f"[red]Failed:[/red] {status.error}")
                else:
                    console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("video")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--format",
    "video_format",
    type=click.Choice(["explainer", "brief"]),
    default="explainer",
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
)
@click.option("--language", default="en")
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@with_client
def generate_video(
    ctx, description, notebook_id, video_format, style, language, wait, json_output, client_auth
):
    """Generate video overview.

    \b
    Example:
      notebooklm generate video "a funny explainer for kids age 5"
      notebooklm generate video "professional presentation" --style classic
      notebooklm generate video --style kawaii
    """
    nb_id = require_notebook(notebook_id)
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

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_video(
                nb_id,
                language=language,
                instructions=description or None,
                video_format=format_map[video_format],
                video_style=style_map[style],
            )

            if not result:
                if json_output:
                    json_error_response("GENERATION_FAILED", "Video generation failed")
                else:
                    console.print("[red]Video generation failed[/red]")
                return

            if wait and result.get("artifact_id"):
                if not json_output:
                    console.print(
                        f"[yellow]Generating video...[/yellow] Task: {result.get('artifact_id')}"
                    )
                status = await client.artifacts.wait_for_completion(
                    nb_id, result["artifact_id"], poll_interval=10.0, timeout=600.0
                )
            else:
                status = result

            if json_output:
                if hasattr(status, "is_complete") and status.is_complete:
                    data = {
                        "artifact_id": status.artifact_id
                        if hasattr(status, "artifact_id")
                        else None,
                        "status": "completed",
                        "url": status.url,
                    }
                    json_output_response(data)
                elif hasattr(status, "is_failed") and status.is_failed:
                    json_error_response(
                        "GENERATION_FAILED", status.error or "Video generation failed"
                    )
                else:
                    artifact_id = (
                        status.get("artifact_id") if isinstance(status, dict) else None
                    )
                    json_output_response({"artifact_id": artifact_id, "status": "pending"})
            else:
                if hasattr(status, "is_complete") and status.is_complete:
                    console.print(f"[green]Video ready:[/green] {status.url}")
                elif hasattr(status, "is_failed") and status.is_failed:
                    console.print(f"[red]Failed:[/red] {status.error}")
                else:
                    console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("slide-deck")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--format",
    "deck_format",
    type=click.Choice(["detailed", "presenter"]),
    default="detailed",
)
@click.option(
    "--length",
    "deck_length",
    type=click.Choice(["default", "short"]),
    default="default",
)
@click.option("--language", default="en")
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_slide_deck(
    ctx, description, notebook_id, deck_format, deck_length, language, wait, client_auth
):
    """Generate slide deck.

    \b
    Example:
      notebooklm generate slide-deck "include speaker notes"
      notebooklm generate slide-deck "executive summary" --format presenter --length short
    """
    nb_id = require_notebook(notebook_id)
    format_map = {
        "detailed": SlideDeckFormat.DETAILED_DECK,
        "presenter": SlideDeckFormat.PRESENTER_SLIDES,
    }
    length_map = {
        "default": SlideDeckLength.DEFAULT,
        "short": SlideDeckLength.SHORT,
    }

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_slide_deck(
                nb_id,
                language=language,
                instructions=description or None,
                slide_deck_format=format_map[deck_format],
                slide_deck_length=length_map[deck_length],
            )

            if not result:
                console.print("[red]Slide deck generation failed[/red]")
                return

            if wait and result.get("artifact_id"):
                console.print(
                    f"[yellow]Generating slide deck...[/yellow] Task: {result.get('artifact_id')}"
                )
                status = await client.artifacts.wait_for_completion(
                    nb_id, result["artifact_id"], poll_interval=10.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print(f"[green]Slide deck ready:[/green] {status.url}")
            else:
                console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("quiz")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--quantity", type=click.Choice(["fewer", "standard", "more"]), default="standard"
)
@click.option(
    "--difficulty", type=click.Choice(["easy", "medium", "hard"]), default="medium"
)
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_quiz(ctx, description, notebook_id, quantity, difficulty, wait, client_auth):
    """Generate quiz.

    \b
    Example:
      notebooklm generate quiz "focus on vocabulary terms"
      notebooklm generate quiz "test key concepts" --difficulty hard --quantity more
    """
    nb_id = require_notebook(notebook_id)
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

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_quiz(
                nb_id,
                instructions=description or None,
                quantity=quantity_map[quantity],
                difficulty=difficulty_map[difficulty],
            )

            if not result:
                console.print(
                    "[red]Quiz generation failed (Google may be rate limiting)[/red]"
                )
                return

            task_id = result.get("artifact_id") or (
                result[0] if isinstance(result, list) else None
            )
            if wait and task_id:
                console.print("[yellow]Generating quiz...[/yellow]")
                status = await client.artifacts.wait_for_completion(
                    nb_id, task_id, poll_interval=5.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print("[green]Quiz ready[/green]")
            elif hasattr(status, "is_failed") and status.is_failed:
                console.print(f"[red]Failed:[/red] {status.error}")
            else:
                console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("flashcards")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--quantity", type=click.Choice(["fewer", "standard", "more"]), default="standard"
)
@click.option(
    "--difficulty", type=click.Choice(["easy", "medium", "hard"]), default="medium"
)
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_flashcards(ctx, description, notebook_id, quantity, difficulty, wait, client_auth):
    """Generate flashcards.

    \b
    Example:
      notebooklm generate flashcards "vocabulary terms only"
      notebooklm generate flashcards --quantity more --difficulty easy
    """
    nb_id = require_notebook(notebook_id)
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

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_flashcards(
                nb_id,
                instructions=description or None,
                quantity=quantity_map[quantity],
                difficulty=difficulty_map[difficulty],
            )

            if not result:
                console.print(
                    "[red]Flashcard generation failed (Google may be rate limiting)[/red]"
                )
                return

            task_id = result.get("artifact_id") or (
                result[0] if isinstance(result, list) else None
            )
            if wait and task_id:
                console.print("[yellow]Generating flashcards...[/yellow]")
                status = await client.artifacts.wait_for_completion(
                    nb_id, task_id, poll_interval=5.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print("[green]Flashcards ready[/green]")
            elif hasattr(status, "is_failed") and status.is_failed:
                console.print(f"[red]Failed:[/red] {status.error}")
            else:
                console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("infographic")
@click.argument("description", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--orientation",
    type=click.Choice(["landscape", "portrait", "square"]),
    default="landscape",
)
@click.option(
    "--detail",
    type=click.Choice(["concise", "standard", "detailed"]),
    default="standard",
)
@click.option("--language", default="en")
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_infographic(
    ctx, description, notebook_id, orientation, detail, language, wait, client_auth
):
    """Generate infographic.

    \b
    Example:
      notebooklm generate infographic "include statistics and key findings"
      notebooklm generate infographic --orientation portrait --detail detailed
    """
    nb_id = require_notebook(notebook_id)
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

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_infographic(
                nb_id,
                language=language,
                instructions=description or None,
                orientation=orientation_map[orientation],
                detail_level=detail_map[detail],
            )

            if not result:
                console.print(
                    "[red]Infographic generation failed (Google may be rate limiting)[/red]"
                )
                return

            task_id = result.get("artifact_id") or (
                result[0] if isinstance(result, list) else None
            )
            if wait and task_id:
                console.print("[yellow]Generating infographic...[/yellow]")
                status = await client.artifacts.wait_for_completion(
                    nb_id, task_id, poll_interval=5.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print("[green]Infographic ready[/green]")
            elif hasattr(status, "is_failed") and status.is_failed:
                console.print(f"[red]Failed:[/red] {status.error}")
            else:
                console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("data-table")
@click.argument("description")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--language", default="en")
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_data_table(ctx, description, notebook_id, language, wait, client_auth):
    """Generate data table.

    \b
    Example:
      notebooklm generate data-table "comparison of key concepts"
      notebooklm generate data-table "timeline of events"
    """
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_data_table(
                nb_id, language=language, instructions=description
            )

            if not result:
                console.print(
                    "[red]Data table generation failed (Google may be rate limiting)[/red]"
                )
                return

            task_id = result.get("artifact_id") or (
                result[0] if isinstance(result, list) else None
            )
            if wait and task_id:
                console.print("[yellow]Generating data table...[/yellow]")
                status = await client.artifacts.wait_for_completion(
                    nb_id, task_id, poll_interval=5.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print("[green]Data table ready[/green]")
            elif hasattr(status, "is_failed") and status.is_failed:
                console.print(f"[red]Failed:[/red] {status.error}")
            else:
                console.print(f"[yellow]Started:[/yellow] {status}")

    return _run()


@generate.command("mind-map")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def generate_mind_map(ctx, notebook_id, client_auth):
    """Generate mind map."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            with console.status("Generating mind map..."):
                result = await client.artifacts.generate_mind_map(nb_id)

            if result:
                console.print("[green]Mind map generated:[/green]")
                if isinstance(result, dict):
                    console.print(f"  Note ID: {result.get('note_id', '-')}")
                    mind_map = result.get("mind_map", {})
                    if isinstance(mind_map, dict):
                        console.print(f"  Root: {mind_map.get('name', '-')}")
                        console.print(
                            f"  Children: {len(mind_map.get('children', []))} nodes"
                        )
                else:
                    console.print(result)
            else:
                console.print("[yellow]No result[/yellow]")

    return _run()


@generate.command("report")
@click.argument("description", default="", required=False)
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["briefing-doc", "study-guide", "blog-post", "custom"]),
    default="briefing-doc",
    help="Report format (default: briefing-doc)",
)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option(
    "--wait/--no-wait", default=False, help="Wait for completion (default: no-wait)"
)
@with_client
def generate_report_cmd(ctx, description, report_format, notebook_id, wait, client_auth):
    """Generate a report (briefing doc, study guide, blog post, or custom).

    \b
    Examples:
      notebooklm generate report                              # briefing-doc (default)
      notebooklm generate report --format study-guide         # study guide
      notebooklm generate report --format blog-post           # blog post
      notebooklm generate report "Create a white paper..."    # custom report
      notebooklm generate report --format blog-post "Focus on key insights"
    """
    nb_id = require_notebook(notebook_id)

    # Smart detection: if description provided without explicit format change, treat as custom
    actual_format = report_format
    custom_prompt = None
    if description:
        if report_format == "briefing-doc":
            actual_format = "custom"
            custom_prompt = description
        else:
            custom_prompt = description

    format_map = {
        "briefing-doc": ReportFormat.BRIEFING_DOC,
        "study-guide": ReportFormat.STUDY_GUIDE,
        "blog-post": ReportFormat.BLOG_POST,
        "custom": ReportFormat.CUSTOM,
    }
    report_format_enum = format_map[actual_format]

    format_display = {
        "briefing-doc": "briefing document",
        "study-guide": "study guide",
        "blog-post": "blog post",
        "custom": "custom report",
    }[actual_format]

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.artifacts.generate_report(
                nb_id,
                report_format=report_format_enum,
                custom_prompt=custom_prompt,
            )

            if not result:
                console.print(
                    "[red]Report generation failed (Google may be rate limiting)[/red]"
                )
                return

            task_id = result.get("artifact_id")
            if wait and task_id:
                console.print(f"[yellow]Generating {format_display}...[/yellow]")
                status = await client.artifacts.wait_for_completion(
                    nb_id, task_id, poll_interval=5.0
                )
            else:
                status = result

            if hasattr(status, "is_complete") and status.is_complete:
                console.print(f"[green]{format_display.title()} ready[/green]")
            elif hasattr(status, "is_failed") and status.is_failed:
                console.print(f"[red]Failed:[/red] {status.error}")
            else:
                artifact_id = (
                    status.get("artifact_id") if isinstance(status, dict) else None
                )
                console.print(f"[yellow]Started:[/yellow] {artifact_id or status}")

    return _run()


# =============================================================================
# DOWNLOAD GROUP
# =============================================================================


@cli.group()
def download():
    """Download generated content.

    \b
    Types:
      audio        Download audio file
      video        Download video file
      slide-deck   Download slide deck images
      infographic  Download infographic image
    """
    pass


async def _download_artifacts_generic(
    ctx,
    artifact_type_name: str,
    artifact_type_id: int,
    file_extension: str,
    default_output_dir: str,
    output_path: str | None,
    notebook: str | None,
    latest: bool,
    earliest: bool,
    download_all: bool,
    name: str | None,
    artifact_id: str | None,
    json_output: bool,
    dry_run: bool,
    force: bool,
    no_clobber: bool,
) -> dict:
    """
    Generic artifact download implementation.

    Handles all artifact types (audio, video, infographic, slide-deck)
    with the same logic, only varying by extension and type filters.

    Args:
        ctx: Click context
        artifact_type_name: Human-readable type name ("audio", "video", etc.)
        artifact_type_id: RPC type ID (1=audio, 3=video, 7=infographic, 8=slide-deck)
        file_extension: File extension (".mp3", ".mp4", ".png", "" for directories)
        default_output_dir: Default output directory for --all flag
        output_path: User-specified output path
        notebook: Notebook ID
        latest: Download latest artifact
        earliest: Download earliest artifact
        download_all: Download all artifacts
        name: Filter by artifact title
        artifact_id: Select by exact artifact ID
        json_output: Output JSON instead of text
        dry_run: Preview without downloading
        force: Overwrite existing files/directories
        no_clobber: Skip if file/directory exists

    Returns:
        Result dictionary with operation details
    """
    from .download_helpers import select_artifact, artifact_title_to_filename
    from pathlib import Path
    from typing import Any

    # Validate conflicting flags
    if force and no_clobber:
        raise click.UsageError("Cannot specify both --force and --no-clobber")
    if latest and earliest:
        raise click.UsageError("Cannot specify both --latest and --earliest")
    if download_all and artifact_id:
        raise click.UsageError("Cannot specify both --all and --artifact-id")

    # Is it a directory type (slide-deck)?
    is_directory_type = file_extension == ""

    # Get notebook and auth
    nb_id = require_notebook(notebook)
    storage_path = ctx.obj.get("storage_path") if ctx.obj else None
    cookies = load_auth_from_storage(storage_path)
    csrf, session_id = await fetch_tokens(cookies)
    auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

    async def _download() -> dict[str, Any]:
        async with NotebookLMClient(auth) as client:
            # Setup download method dispatch
            download_methods = {
                "audio": client.download_audio,
                "video": client.download_video,
                "infographic": client.download_infographic,
                "slide-deck": client.download_slide_deck,
            }
            download_fn = download_methods.get(artifact_type_name)
            if not download_fn:
                raise ValueError(f"Unknown artifact type: {artifact_type_name}")

            # Fetch artifacts
            all_artifacts = await client.artifacts.list(nb_id)

            # Filter by type and status=3 (completed)
            # Artifact structure: [id, title, type, created_at, status, ...]
            type_artifacts_raw = [
                a
                for a in all_artifacts
                if isinstance(a, list)
                and len(a) > 4
                and a[2] == artifact_type_id
                and a[4] == 3
            ]

            if not type_artifacts_raw:
                return {
                    "error": f"No completed {artifact_type_name} artifacts found",
                    "suggestion": f"Generate one with: notebooklm generate {artifact_type_name}",
                }

            # Convert to dict format
            type_artifacts = [
                {
                    "id": a[0],
                    "title": a[1],
                    "created_at": a[3] if len(a) > 3 else 0,
                }
                for a in type_artifacts_raw
            ]

            # Helper for file/dir conflict resolution
            def _resolve_conflict(path: Path) -> tuple[Path | None, dict | None]:
                if not path.exists():
                    return path, None

                if no_clobber:
                    entity_type = "directory" if is_directory_type else "file"
                    return None, {
                        "status": "skipped",
                        "reason": f"{entity_type} exists",
                        "path": str(path),
                    }

                if not force:
                    # Auto-rename
                    counter = 2
                    if is_directory_type:
                        base_name = path.name
                        parent = path.parent
                        while path.exists():
                            path = parent / f"{base_name} ({counter})"
                            counter += 1
                    else:
                        base_name = path.stem
                        parent = path.parent
                        ext = path.suffix
                        while path.exists():
                            path = parent / f"{base_name} ({counter}){ext}"
                            counter += 1

                return path, None

            # Handle --all flag
            if download_all:
                output_dir = (
                    Path(output_path) if output_path else Path(default_output_dir)
                )

                if dry_run:
                    return {
                        "dry_run": True,
                        "operation": "download_all",
                        "count": len(type_artifacts),
                        "output_dir": str(output_dir),
                        "artifacts": [
                            {
                                "id": a["id"],
                                "title": a["title"],
                                "filename": artifact_title_to_filename(
                                    a["title"],
                                    file_extension if not is_directory_type else "",
                                    set(),
                                ),
                            }
                            for a in type_artifacts
                        ],
                    }

                output_dir.mkdir(parents=True, exist_ok=True)

                results = []
                existing_names = set()
                total = len(type_artifacts)

                for i, artifact in enumerate(type_artifacts, 1):
                    # Progress indicator
                    if not json_output:
                        console.print(
                            f"[dim]Downloading {i}/{total}:[/dim] {artifact['title']}"
                        )

                    # Generate safe name
                    item_name = artifact_title_to_filename(
                        artifact["title"],
                        file_extension if not is_directory_type else "",
                        existing_names,
                    )
                    existing_names.add(item_name)
                    item_path = output_dir / item_name

                    # Resolve conflicts
                    resolved_path, skip_info = _resolve_conflict(item_path)
                    if skip_info:
                        results.append(
                            {
                                "id": artifact["id"],
                                "title": artifact["title"],
                                "filename": item_name,
                                **skip_info,
                            }
                        )
                        continue

                    # Update if auto-renamed
                    item_path = resolved_path
                    item_name = item_path.name

                    # Download
                    try:
                        # For directory types, create the directory first
                        if is_directory_type:
                            item_path.mkdir(parents=True, exist_ok=True)

                        # Download using dispatch
                        await download_fn(
                            nb_id, str(item_path), artifact_id=artifact["id"]
                        )

                        results.append(
                            {
                                "id": artifact["id"],
                                "title": artifact["title"],
                                "filename": item_name,
                                "path": str(item_path),
                                "status": "downloaded",
                            }
                        )
                    except Exception as e:
                        results.append(
                            {
                                "id": artifact["id"],
                                "title": artifact["title"],
                                "filename": item_name,
                                "status": "failed",
                                "error": str(e),
                            }
                        )

                return {
                    "operation": "download_all",
                    "output_dir": str(output_dir),
                    "total": total,
                    "results": results,
                }

            # Single artifact selection
            try:
                selected, reason = select_artifact(
                    type_artifacts,
                    latest=latest,
                    earliest=earliest,
                    name=name,
                    artifact_id=artifact_id,
                )
            except ValueError as e:
                return {"error": str(e)}

            # Determine output path
            if not output_path:
                safe_name = artifact_title_to_filename(
                    selected["title"],
                    file_extension if not is_directory_type else "",
                    set(),
                )
                final_path = Path.cwd() / safe_name
            else:
                final_path = Path(output_path)

            # Dry run
            if dry_run:
                return {
                    "dry_run": True,
                    "operation": "download_single",
                    "artifact": {
                        "id": selected["id"],
                        "title": selected["title"],
                        "selection_reason": reason,
                    },
                    "output_path": str(final_path),
                }

            # Resolve conflicts
            resolved_path, skip_error = _resolve_conflict(final_path)
            if skip_error:
                entity_type = "Directory" if is_directory_type else "File"
                return {
                    "error": f"{entity_type} exists: {final_path}",
                    "artifact": selected,
                    "suggestion": "Use --force to overwrite or choose a different path",
                }

            final_path = resolved_path

            # Download
            try:
                # For directory types, create the directory first
                if is_directory_type:
                    final_path.mkdir(parents=True, exist_ok=True)

                # Download using dispatch
                result_path = await download_fn(
                    nb_id, str(final_path), artifact_id=selected["id"]
                )

                return {
                    "operation": "download_single",
                    "artifact": {
                        "id": selected["id"],
                        "title": selected["title"],
                        "selection_reason": reason,
                    },
                    "output_path": result_path or str(final_path),
                    "status": "downloaded",
                }
            except Exception as e:
                return {"error": str(e), "artifact": selected}

    return await _download()


def _display_download_result(result: dict, artifact_type: str):
    """Display download results in user-friendly format."""
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        if "suggestion" in result:
            console.print(f"[dim]{result['suggestion']}[/dim]")
        return

    # Dry run
    if result.get("dry_run"):
        if result["operation"] == "download_all":
            console.print(
                f"[yellow]DRY RUN:[/yellow] Would download {result['count']} {artifact_type} files to: {result['output_dir']}"
            )
            console.print("\n[bold]Preview:[/bold]")
            for art in result["artifacts"]:
                console.print(f"  {art['filename']} <- {art['title']}")
        else:
            console.print(f"[yellow]DRY RUN:[/yellow] Would download:")
            console.print(f"  Artifact: {result['artifact']['title']}")
            console.print(f"  Reason: {result['artifact']['selection_reason']}")
            console.print(f"  Output: {result['output_path']}")
        return

    # Download all results
    if result.get("operation") == "download_all":
        downloaded = [r for r in result["results"] if r.get("status") == "downloaded"]
        skipped = [r for r in result["results"] if r.get("status") == "skipped"]
        failed = [r for r in result["results"] if r.get("status") == "failed"]

        console.print(
            f"[bold]Downloaded {len(downloaded)}/{result['total']} {artifact_type} files to:[/bold] {result['output_dir']}"
        )

        if downloaded:
            console.print("\n[green]Downloaded:[/green]")
            for r in downloaded:
                console.print(f"  {r['filename']} <- {r['title']}")

        if skipped:
            console.print("\n[yellow]Skipped:[/yellow]")
            for r in skipped:
                console.print(f"  {r['filename']} ({r.get('reason', 'unknown')})")

        if failed:
            console.print("\n[red]Failed:[/red]")
            for r in failed:
                console.print(f"  {r['filename']}: {r.get('error', 'unknown error')}")

    # Single download
    else:
        console.print(
            f"[green]{artifact_type.capitalize()} saved to:[/green] {result['output_path']}"
        )
        console.print(
            f"[dim]Artifact: {result['artifact']['title']} ({result['artifact']['selection_reason']})[/dim]"
        )


@download.command("audio")
@click.argument("output_path", required=False, type=click.Path())
@click.option("-n", "--notebook", help="Notebook ID (uses current context if not set)")
@click.option("--latest", is_flag=True, default=True, help="Download latest (default)")
@click.option("--earliest", is_flag=True, help="Download earliest")
@click.option("--all", "download_all", is_flag=True, help="Download all artifacts")
@click.option("--name", help="Filter by artifact title (fuzzy match)")
@click.option("--artifact-id", help="Select by exact artifact ID")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of text")
@click.option("--dry-run", is_flag=True, help="Preview without downloading")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-clobber", is_flag=True, help="Skip if file exists")
@click.pass_context
def download_audio(
    ctx,
    output_path,
    notebook,
    latest,
    earliest,
    download_all,
    name,
    artifact_id,
    json_output,
    dry_run,
    force,
    no_clobber,
):
    """Download audio overview(s) to file.

    \b
    Examples:
      # Download latest audio to default filename
      notebooklm download audio

      # Download to specific path
      notebooklm download audio my-podcast.mp3

      # Download all audio files to directory
      notebooklm download audio --all ./audio/

      # Download specific artifact by name
      notebooklm download audio --name "chapter 3"

      # Preview without downloading
      notebooklm download audio --all --dry-run
    """
    try:
        result = run_async(
            _download_artifacts_generic(
                ctx=ctx,
                artifact_type_name="audio",
                artifact_type_id=1,
                file_extension=".mp3",
                default_output_dir="./audio",
                output_path=output_path,
                notebook=notebook,
                latest=latest,
                earliest=earliest,
                download_all=download_all,
                name=name,
                artifact_id=artifact_id,
                json_output=json_output,
                dry_run=dry_run,
                force=force,
                no_clobber=no_clobber,
            )
        )

        if json_output:
            console.print(json.dumps(result, indent=2))
            return

        if "error" in result:
            _display_download_result(result, "audio")
            raise SystemExit(1)

        _display_download_result(result, "audio")

    except Exception as e:
        handle_error(e)


@download.command("video")
@click.argument("output_path", required=False, type=click.Path())
@click.option("-n", "--notebook", help="Notebook ID (uses current context if not set)")
@click.option("--latest", is_flag=True, default=True, help="Download latest (default)")
@click.option("--earliest", is_flag=True, help="Download earliest")
@click.option("--all", "download_all", is_flag=True, help="Download all artifacts")
@click.option("--name", help="Filter by artifact title (fuzzy match)")
@click.option("--artifact-id", help="Select by exact artifact ID")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of text")
@click.option("--dry-run", is_flag=True, help="Preview without downloading")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-clobber", is_flag=True, help="Skip if file exists")
@click.pass_context
def download_video(
    ctx,
    output_path,
    notebook,
    latest,
    earliest,
    download_all,
    name,
    artifact_id,
    json_output,
    dry_run,
    force,
    no_clobber,
):
    """Download video overview(s) to file.

    \b
    Examples:
      # Download latest video to default filename
      notebooklm download video

      # Download to specific path
      notebooklm download video my-video.mp4

      # Download all video files to directory
      notebooklm download video --all ./video/

      # Download specific artifact by name
      notebooklm download video --name "chapter 3"

      # Preview without downloading
      notebooklm download video --all --dry-run
    """
    try:
        result = run_async(
            _download_artifacts_generic(
                ctx=ctx,
                artifact_type_name="video",
                artifact_type_id=3,
                file_extension=".mp4",
                default_output_dir="./video",
                output_path=output_path,
                notebook=notebook,
                latest=latest,
                earliest=earliest,
                download_all=download_all,
                name=name,
                artifact_id=artifact_id,
                json_output=json_output,
                dry_run=dry_run,
                force=force,
                no_clobber=no_clobber,
            )
        )

        if json_output:
            console.print(json.dumps(result, indent=2))
            return

        if "error" in result:
            _display_download_result(result, "video")
            raise SystemExit(1)

        _display_download_result(result, "video")

    except Exception as e:
        handle_error(e)


@download.command("slide-deck")
@click.argument("output_path", required=False, type=click.Path())
@click.option("-n", "--notebook", help="Notebook ID (uses current context if not set)")
@click.option("--latest", is_flag=True, default=True, help="Download latest (default)")
@click.option("--earliest", is_flag=True, help="Download earliest")
@click.option("--all", "download_all", is_flag=True, help="Download all artifacts")
@click.option("--name", help="Filter by artifact title (fuzzy match)")
@click.option("--artifact-id", help="Select by exact artifact ID")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of text")
@click.option("--dry-run", is_flag=True, help="Preview without downloading")
@click.option("--force", is_flag=True, help="Overwrite existing directories")
@click.option("--no-clobber", is_flag=True, help="Skip if directory exists")
@click.pass_context
def download_slide_deck(
    ctx,
    output_path,
    notebook,
    latest,
    earliest,
    download_all,
    name,
    artifact_id,
    json_output,
    dry_run,
    force,
    no_clobber,
):
    """Download slide deck(s) to directories.

    \b
    Examples:
      # Download latest slide deck to default directory
      notebooklm download slide-deck

      # Download to specific directory
      notebooklm download slide-deck ./my-slides/

      # Download all slide decks to parent directory
      notebooklm download slide-deck --all ./slide-deck/

      # Download specific artifact by name
      notebooklm download slide-deck --name "chapter 3"

      # Preview without downloading
      notebooklm download slide-deck --all --dry-run
    """
    try:
        result = run_async(
            _download_artifacts_generic(
                ctx=ctx,
                artifact_type_name="slide-deck",
                artifact_type_id=8,
                file_extension="",  # Empty string for directory type
                default_output_dir="./slide-deck",
                output_path=output_path,
                notebook=notebook,
                latest=latest,
                earliest=earliest,
                download_all=download_all,
                name=name,
                artifact_id=artifact_id,
                json_output=json_output,
                dry_run=dry_run,
                force=force,
                no_clobber=no_clobber,
            )
        )

        if json_output:
            console.print(json.dumps(result, indent=2))
            return

        if "error" in result:
            _display_download_result(result, "slide-deck")
            raise SystemExit(1)

        _display_download_result(result, "slide-deck")

    except Exception as e:
        handle_error(e)


@download.command("infographic")
@click.argument("output_path", required=False, type=click.Path())
@click.option("-n", "--notebook", help="Notebook ID (uses current context if not set)")
@click.option("--latest", is_flag=True, default=True, help="Download latest (default)")
@click.option("--earliest", is_flag=True, help="Download earliest")
@click.option("--all", "download_all", is_flag=True, help="Download all artifacts")
@click.option("--name", help="Filter by artifact title (fuzzy match)")
@click.option("--artifact-id", help="Select by exact artifact ID")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of text")
@click.option("--dry-run", is_flag=True, help="Preview without downloading")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-clobber", is_flag=True, help="Skip if file exists")
@click.pass_context
def download_infographic(
    ctx,
    output_path,
    notebook,
    latest,
    earliest,
    download_all,
    name,
    artifact_id,
    json_output,
    dry_run,
    force,
    no_clobber,
):
    """Download infographic(s) to file.

    \b
    Examples:
      # Download latest infographic to default filename
      notebooklm download infographic

      # Download to specific path
      notebooklm download infographic my-infographic.png

      # Download all infographic files to directory
      notebooklm download infographic --all ./infographic/

      # Download specific artifact by name
      notebooklm download infographic --name "chapter 3"

      # Preview without downloading
      notebooklm download infographic --all --dry-run
    """
    try:
        result = run_async(
            _download_artifacts_generic(
                ctx=ctx,
                artifact_type_name="infographic",
                artifact_type_id=7,
                file_extension=".png",
                default_output_dir="./infographic",
                output_path=output_path,
                notebook=notebook,
                latest=latest,
                earliest=earliest,
                download_all=download_all,
                name=name,
                artifact_id=artifact_id,
                json_output=json_output,
                dry_run=dry_run,
                force=force,
                no_clobber=no_clobber,
            )
        )

        if json_output:
            console.print(json.dumps(result, indent=2))
            return

        if "error" in result:
            _display_download_result(result, "infographic")
            raise SystemExit(1)

        _display_download_result(result, "infographic")

    except Exception as e:
        handle_error(e)


# =============================================================================
# NOTE GROUP
# =============================================================================


@cli.group()
def note():
    """Note management commands.

    \b
    Commands:
      list    List all notes
      create  Create a new note
      get     Get note content
      save    Update note content
      delete  Delete a note
    """
    pass


def _parse_note(n: list) -> tuple[str, str, str]:
    """Parse note structure and return (note_id, title, content).

    GET_NOTES structure: [note_id, [note_id, content, metadata, None, title]]
    - n[0] = note ID
    - n[1][1] = content (or n[1] if string - old format)
    - n[1][4] = title
    """
    note_id = str(n[0]) if len(n) > 0 and n[0] else "-"
    content = ""
    title = "Untitled"

    if len(n) > 1:
        if isinstance(n[1], str):
            # Old format: [note_id, content]
            content = n[1]
        elif isinstance(n[1], list):
            # New format: [note_id, [note_id, content, metadata, None, title]]
            inner = n[1]
            if len(inner) > 1 and isinstance(inner[1], str):
                content = inner[1]
            if len(inner) > 4 and isinstance(inner[4], str):
                title = inner[4]

    return note_id, title, content


@note.command("list")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def note_list(ctx, notebook_id, client_auth):
    """List all notes in a notebook."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            notes = await client.notes.list(nb_id)

            if not notes:
                console.print("[yellow]No notes found[/yellow]")
                return

            table = Table(title=f"Notes in {nb_id}")
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="green")
            table.add_column("Preview", style="dim", max_width=50)

            for n in notes:
                if isinstance(n, list) and len(n) > 0:
                    note_id, title, content = _parse_note(n)
                    preview = content[:50]
                    table.add_row(
                        note_id, title, preview + "..." if len(content) > 50 else preview
                    )

            console.print(table)

    return _run()


@note.command("create")
@click.argument("content", default="", required=False)
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("-t", "--title", default="New Note", help="Note title")
@with_client
def note_create(ctx, content, notebook_id, title, client_auth):
    """Create a new note.

    \b
    Examples:
      notebooklm note create                        # Empty note with default title
      notebooklm note create "My note content"     # Note with content
      notebooklm note create "Content" -t "Title"  # Note with title and content
    """
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            result = await client.notes.create(nb_id, title, content)

            if result:
                console.print("[green]Note created[/green]")
                console.print(result)
            else:
                console.print("[yellow]Creation may have failed[/yellow]")

    return _run()


@note.command("get")
@click.argument("note_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def note_get(ctx, note_id, notebook_id, client_auth):
    """Get note content."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            n = await client.notes.get(nb_id, note_id)

            if n:
                if isinstance(n, list) and len(n) > 0:
                    nid, title, content = _parse_note(n)
                    console.print(f"[bold cyan]ID:[/bold cyan] {nid}")
                    console.print(f"[bold cyan]Title:[/bold cyan] {title}")
                    console.print(f"[bold cyan]Content:[/bold cyan]\n{content}")
                else:
                    console.print(n)
            else:
                console.print("[yellow]Note not found[/yellow]")

    return _run()


@note.command("save")
@click.argument("note_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--title", help="New title")
@click.option("--content", help="New content")
@with_client
def note_save(ctx, note_id, notebook_id, title, content, client_auth):
    """Update note content."""
    if not title and not content:
        console.print("[yellow]Provide --title and/or --content[/yellow]")
        return

    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            await client.notes.update(nb_id, note_id, content=content, title=title)
            console.print(f"[green]Note updated:[/green] {note_id}")

    return _run()


@note.command("rename")
@click.argument("note_id")
@click.argument("new_title")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@with_client
def note_rename(ctx, note_id, new_title, notebook_id, client_auth):
    """Rename a note."""
    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            # Get current note to preserve content
            note = await client.notes.get(nb_id, note_id)
            if not note:
                console.print("[yellow]Note not found[/yellow]")
                return

            # Extract content from note structure
            content = ""
            if len(note) > 1 and isinstance(note[1], list):
                inner = note[1]
                if len(inner) > 1 and isinstance(inner[1], str):
                    content = inner[1]

            await client.notes.update(nb_id, note_id, content=content, title=new_title)
            console.print(f"[green]Note renamed:[/green] {new_title}")

    return _run()


@note.command("delete")
@click.argument("note_id")
@click.option(
    "-n",
    "--notebook",
    "notebook_id",
    default=None,
    help="Notebook ID (uses current if not set)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@with_client
def note_delete(ctx, note_id, notebook_id, yes, client_auth):
    """Delete a note."""
    if not yes and not click.confirm(f"Delete note {note_id}?"):
        return

    nb_id = require_notebook(notebook_id)

    async def _run():
        async with NotebookLMClient(client_auth) as client:
            await client.notes.delete(nb_id, note_id)
            console.print(f"[green]Deleted note:[/green] {note_id}")

    return _run()


# =============================================================================
# MISC GROUP (guidebooks, share-audio)
# =============================================================================


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
