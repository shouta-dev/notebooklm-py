# Contributing to notebooklm-py

## For Human Contributors

### Getting Started

```bash
# Install in development mode
pip install -e ".[all]"
playwright install chromium

# Run tests
pytest
```

### Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Ensure tests pass: `pytest`
4. Submit a PR with a description of changes

---

## Documentation Rules for AI Agents

**IMPORTANT:** All AI agents (Claude, Gemini, etc.) must follow these rules when working in this repository.

### File Creation Rules

1. **No Root Rule** - Never create `.md` files in the repository root unless explicitly instructed by the user.

2. **Modify, Don't Fork** - Edit existing files; never create `FILE_v2.md`, `FILE_REFERENCE.md`, or `FILE_updated.md` duplicates.

3. **Scratchpad Protocol** - All analysis, investigation logs, and intermediate work go in `docs/scratch/` with date prefix: `YYYY-MM-DD-<context>.md`

4. **Consolidation First** - Before creating new docs, search for existing related docs and update them instead.

### Protected Sections

Some sections within files are critical and must not be modified without explicit user approval.

**Inline markers** (source of truth):
```markdown
<!-- PROTECTED: Do not modify without approval -->
## Critical Section Title
Content that should not be changed by agents...
<!-- END PROTECTED -->
```

For code files:
```python
# PROTECTED: Do not modify without approval
class RPCMethod(Enum):
    ...
# END PROTECTED
```

**Rule:** Never modify content between `PROTECTED` and `END PROTECTED` markers unless explicitly instructed by the user.

### Plan/Design Lifecycle

1. **Design docs** (`docs/designs/`) - Document the "why" behind major decisions; kept permanently. Format: `<feature-name>.md` (no date prefix).

2. **Implementation plans** - Tactical step-by-step plans; delete after task completion.

3. **Scratch files** (`docs/scratch/`) - Temporary work; periodically cleaned up. Format: `YYYY-MM-DD-<context>.md`

### Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Root GitHub files | `UPPERCASE.md` | `README.md`, `CONTRIBUTING.md` |
| Agent files | `UPPERCASE.md` | `CLAUDE.md`, `AGENTS.md` |
| All docs/ files | `lowercase-kebab.md` | `getting-started.md`, `cli-reference.md` |
| Design docs | `lowercase-kebab.md` | `documentation-refresh.md` |
| Scratch files | `YYYY-MM-DD-context.md` | `2026-01-06-debug-auth.md` |

### Status Headers

All documentation files should include status metadata:

```markdown
**Status:** Active | Deprecated
**Last Updated:** YYYY-MM-DD
```

Agents should ignore files marked `Deprecated`.

### Information Management

1. **Link, Don't Copy** - Reference README.md sections instead of repeating commands. Prevents drift between docs.

2. **Scoped Instructions** - See `docs/README.md` for folder-specific documentation rules.

---

## Documentation Structure

```
docs/
├── README.md              # Folder-specific rules
├── getting-started.md     # Installation and first workflow
├── cli-reference.md       # CLI command reference
├── python-api.md          # Python API reference
├── configuration.md       # Storage and settings
├── troubleshooting.md     # Common issues and solutions
├── examples/              # Runnable example scripts
├── contributing/          # Contributor guides
│   ├── architecture.md    # Code structure
│   ├── debugging.md       # Network capture guide
│   ├── testing.md         # Running tests
│   └── rpc-protocol.md    # RPC protocol reference
├── reference/
│   └── internals/         # Reverse engineering notes
├── designs/               # Approved design docs (permanent)
│   └── <feature-name>.md
└── scratch/               # Temporary agent work (disposable)
    └── YYYY-MM-DD-context.md
```
