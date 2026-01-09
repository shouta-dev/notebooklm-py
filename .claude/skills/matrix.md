---
name: matrix
description: Run tests across multiple Python versions using Docker containers
---

# Multi-Version Test Runner

Run the test suite across Python 3.10-3.14 using Docker containers in parallel.

## Quick Start

```bash
./dev/test-versions.sh
```

## Usage Examples

```bash
# Run all versions (3.10, 3.11, 3.12, 3.13, 3.14)
./dev/test-versions.sh

# Run specific versions only
./dev/test-versions.sh 3.12 3.13

# Include readonly e2e tests (requires auth)
./dev/test-versions.sh -r

# Pass pytest arguments (after --)
./dev/test-versions.sh -- -k test_encoder -v

# Combine options
./dev/test-versions.sh -r 3.12 -- -k test_encoder
```

## When to Use

- Before committing changes that might affect Python version compatibility
- When testing syntax or feature compatibility across versions
- To validate all supported Python versions pass locally before CI

## Requirements

- Docker must be running
- First run pulls Python images (~50MB each)
- Subsequent runs use cached pip packages for speed (~30s per version)

## Output

Shows pass/fail status for each Python version with test summary.
On failure, displays last 30 lines of output for debugging.

## Cache Management

To clear pip cache volumes:
```bash
docker volume ls | grep notebooklm-pip-cache | xargs docker volume rm
```
