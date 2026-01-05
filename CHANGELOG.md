# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-05

### Added
- Initial release of `notebooklm-client` - unofficial Python client for Google NotebookLM
- Full notebook CRUD operations (create, list, rename, delete)
- Source management:
  - Add URL sources (with YouTube transcript support)
  - Add text sources
  - Add file sources (PDF, TXT, MD, DOCX) via native upload
  - Delete sources
  - Rename sources
- Studio artifact generation:
  - Audio overviews (podcasts) with 4 formats and 3 lengths
  - Video overviews with 9 visual styles
  - Quizzes and flashcards
  - Infographics, slide decks, and data tables
  - Study guides, briefing docs, and reports
- Query/chat interface with conversation history support
- Research agents (Fast and Deep modes)
- Artifact downloads (audio, video, infographics, slides)
- CLI with 27 commands
- Comprehensive documentation (API, RPC, examples)
- 96 unit tests (100% passing)
- E2E tests for all major features

### Fixed
- Audio overview instructions parameter now properly supported at RPC position [6][1][0]
- Quiz and flashcard distinction via title-based filtering
- Package renamed from `notebooklm-automation` to `notebooklm`
- CLI module renamed from `cli.py` to `notebooklm_cli.py`
- Removed orphaned `cli_query.py` file

### API Changes
- Renamed collection methods to use `list_*` pattern (e.g., `get_quizzes()` → `list_quizzes()`)
- Split `get_notes()` into `list_notes()` and `list_mind_maps()`
- Added `get_artifact(notebook_id, artifact_id)` for single-item retrieval
- Old methods kept as deprecated wrappers with warnings

### Known Issues
- Quiz and flashcard generation returns `None` (may require further RPC investigation)
- RPC method IDs may change without notice (reverse-engineered API)
- Both quiz and flashcard use type 4 internally, distinguished by title

[0.1.0]: https://github.com/teng-lin/notion-notebooklm/releases/tag/v0.1.0
