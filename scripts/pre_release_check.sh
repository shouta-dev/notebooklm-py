#!/bin/bash
# Pre-release checks for notebooklm-client
set -e

echo "🔍 Running pre-release checks..."
echo ""

# Type checking
echo "📝 Checking types with mypy..."
mypy src/notebooklm || { echo "❌ Type errors found"; exit 1; }
echo "✅ Types OK"
echo ""

# Unit tests
echo "🧪 Running unit tests..."
pytest tests/unit -q || { echo "❌ Unit tests failed"; exit 1; }
echo "✅ Unit tests passed"
echo ""

# Integration tests
echo "🔗 Running integration tests..."
pytest tests/integration -q || { echo "❌ Integration tests failed"; exit 1; }
echo "✅ Integration tests passed"
echo ""

# Coverage check
echo "📊 Checking test coverage..."
coverage run -m pytest tests/unit tests/integration -q
coverage report --fail-under=70 || { echo "❌ Coverage below 70%"; exit 1; }
echo "✅ Coverage OK"
echo ""

# Check GitHub URLs
echo "🔗 Verifying GitHub URLs..."
if grep -q "notebooklm-clinet" pyproject.toml; then
    echo "❌ ERROR: Found 'clinet' typo in pyproject.toml"
    exit 1
fi
echo "✅ URLs OK"
echo ""

# Build check
echo "📦 Building package..."
hatch build || { echo "❌ Build failed"; exit 1; }
echo "✅ Build OK"
echo ""

echo "🎉 All pre-release checks passed!"
echo "Ready to release. Run: hatch publish"
