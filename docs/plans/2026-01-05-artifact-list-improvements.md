# Artifact List Command Improvements

**Date:** 2026-01-05
**Status:** Design Approved

## Overview

Improve the `artifact list` command to match CLI conventions and provide more useful information.

## Current Issues

1. `artifact list` requires `notebook_id` as a positional argument, unlike all other commands which use `-n/--notebook` option with context fallback
2. Table doesn't display artifact type, even though the data is available
3. Creation time is not shown

## Design

### 1. Command Signature Change

**Current:**
```python
@artifact.command("list")
@click.argument("notebook_id")
@click.option("--type", ...)
def artifact_list(ctx, notebook_id, artifact_type):
```

**New:**
```python
@artifact.command("list")
@click.option("-n", "--notebook", "notebook_id", default=None,
              help="Notebook ID (uses current if not set)")
@click.option("--type", ...)
def artifact_list(ctx, notebook_id, artifact_type):
    nb_id = require_notebook(notebook_id)  # Fallback to context
```

**Usage Examples:**
- `notebooklm artifact list` - uses context
- `notebooklm artifact list -n nb_123` - explicit notebook
- `notebooklm artifact list --type video` - filter by type with context

### 2. Type Display Mapping

Map artifact type IDs to human-readable names with emojis:

```python
ARTIFACT_TYPE_DISPLAY = {
    1: "🎵 Audio Overview",
    2: "📄 Briefing Doc",
    3: "🎥 Video Overview",
    4: "📝 Quiz",           # Also used for flashcards
    5: "🧠 Mind Map",
    6: "📊 Report",
    7: "🖼️ Infographic",
    8: "🎞️ Slide Deck",
    9: "📋 Data Table",
}
```

### 3. Table Structure

**New Columns:**
- ID (existing)
- **Type** (new)
- Title (existing)
- Status (existing)
- **Created** (new)

**Implementation:**
```python
table = Table(title=f"Artifacts in {notebook_id}")
table.add_column("ID", style="cyan")
table.add_column("Type")
table.add_column("Title", style="green")
table.add_column("Status", style="yellow")
table.add_column("Created", style="dim")

for art in artifacts:
    if isinstance(art, list) and len(art) > 0:
        # Artifact structure: [id, title, type, created_at, status, ...]
        art_id = str(art[0] or "-")
        title = str(art[1] if len(art) > 1 else "-")
        type_id = art[2] if len(art) > 2 else None
        created_at_ms = art[3] if len(art) > 3 else None
        status_code = art[4] if len(art) > 4 else None

        # Format type
        type_display = ARTIFACT_TYPE_DISPLAY.get(type_id, f"Unknown ({type_id})")

        # Format timestamp
        if created_at_ms:
            created = datetime.fromtimestamp(created_at_ms / 1000).strftime("%Y-%m-%d %H:%M")
        else:
            created = "-"

        # Format status
        status = "completed" if status_code == 3 else "processing" if status_code == 1 else str(status_code)

        table.add_row(art_id, type_display, title, status, created)
```

### 4. Edge Cases

1. **Unknown type ID**: Display "Unknown (ID: X)" if type not in mapping
2. **Missing fields**: Use "-" for any missing data
3. **Filter behavior**: Type column still shows when using `--type` filter (confirms filter worked)
4. **Empty list**: Existing "No artifacts found" message remains

### 5. Example Output

```
Artifacts in nb_abc123
┌─────────┬──────────────────────┬─────────────────┬───────────┬─────────────────┐
│ ID      │ Type                 │ Title           │ Status    │ Created         │
├─────────┼──────────────────────┼─────────────────┼───────────┼─────────────────┤
│ art_123 │ 🎵 Audio Overview    │ Chapter 1       │ completed │ 2026-01-05 14:30│
│ art_124 │ 🎥 Video Overview    │ Introduction    │ processing│ 2026-01-05 15:15│
│ art_125 │ 🖼️ Infographic      │ Summary Stats   │ completed │ 2026-01-04 09:20│
└─────────┴──────────────────────┴─────────────────┴───────────┴─────────────────┘
```

## Implementation Notes

- Location: `src/notebooklm/notebooklm_cli.py` lines 899-958
- Add `ARTIFACT_TYPE_DISPLAY` constant near top of file or in `rpc/types.py`
- Import `datetime` if not already imported
- Ensure existing tests are updated for new signature
- Add new test cases for type display and timestamp formatting

## Benefits

1. **Consistency**: Matches command signature pattern used throughout CLI
2. **Usability**: Default context behavior reduces typing
3. **Information**: Type and creation time help identify and sort artifacts
4. **Visual**: Emojis make types instantly recognizable
