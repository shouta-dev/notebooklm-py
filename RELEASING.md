# Releasing notebooklm-client

## Pre-Release Checklist

### Code Quality
- [ ] `mypy src/notebooklm` - 0 errors
- [ ] `pytest tests/unit tests/integration -v` - 100% pass
- [ ] `coverage report` - >= 70% coverage (target: 80%)
- [ ] No TODO/FIXME in critical paths

### Packaging
- [ ] Version bumped in `pyproject.toml`
- [ ] Version bumped in `src/notebooklm/__init__.py`
- [ ] CHANGELOG.md updated with release date
- [ ] GitHub URLs correct (not "clinet")
- [ ] License file present

### Documentation
- [ ] README examples work copy-paste
- [ ] CLI help text accurate (`notebooklm --help`)
- [ ] Python API docs match actual signatures

### Manual Testing
- [ ] `pip install .` succeeds
- [ ] `notebooklm login` opens browser
- [ ] `notebooklm list` shows notebooks
- [ ] `notebooklm create "Test"` succeeds
- [ ] `notebooklm source add <url>` succeeds
- [ ] `notebooklm ask "question"` returns answer

### PyPI Publishing
1. Test on TestPyPI first:
   ```bash
   hatch build
   hatch publish -r test
   ```
2. Verify at https://test.pypi.org/project/notebooklm-client/
3. Publish to PyPI:
   ```bash
   hatch publish
   ```

## Version Bumping

1. Update version in `pyproject.toml`
2. Update version in `src/notebooklm/__init__.py`
3. Update CHANGELOG.md
4. Commit: `git commit -m "chore: bump version to X.Y.Z"`
5. Tag: `git tag vX.Y.Z`
6. Push: `git push && git push --tags`
