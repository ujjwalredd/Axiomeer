#!/bin/bash
# Automated SDK Publishing Script for PyPI

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          Axiomeer SDK Publishing Script                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Navigate to SDK directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$SCRIPT_DIR/../sdk/python"
cd "$SDK_DIR"

# Check version
VERSION=$(grep "version = " pyproject.toml | head -1 | cut -d'"' -f2)
echo "Publishing version: $VERSION"
echo

# Step 1: Clean previous builds
echo "1. Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info axiomeer.egg-info
echo "   ✓ Cleaned"
echo

# Step 2: Run linter (optional)
echo "2. Running code checks..."
if command -v black &> /dev/null; then
    black axiomeer/ --check || true
fi
echo "   ✓ Code checked"
echo

# Step 3: Build package
echo "3. Building package..."
if ! python3 -m build; then
    echo "   ✗ Build failed"
    echo
    echo "Install build tools: pip install --upgrade build twine"
    exit 1
fi
echo "   ✓ Built"
echo

# Step 4: Check with twine
echo "4. Checking package..."
if ! python3 -m twine check dist/*; then
    echo "   ✗ Package check failed"
    exit 1
fi
echo "   ✓ Package valid"
echo

# Step 5: Show package contents
echo "5. Package contents:"
echo "   Files:"
ls -lh dist/
echo
echo "   Wheel contents:"
unzip -l dist/*.whl | head -20
echo

# Step 6: Ask which repository
echo "6. Select publishing target:"
echo "   1) TestPyPI (test.pypi.org) - For testing"
echo "   2) PyPI (pypi.org) - Production"
echo "   3) Cancel"
echo
read -p "   Enter choice (1/2/3): " REPO_CHOICE

case $REPO_CHOICE in
    1)
        REPO="testpypi"
        REPO_URL="https://test.pypi.org/project/axiomeer/$VERSION/"
        ;;
    2)
        REPO="pypi"
        REPO_URL="https://pypi.org/project/axiomeer/$VERSION/"
        ;;
    3)
        echo "   Publishing cancelled"
        exit 0
        ;;
    *)
        echo "   Invalid choice"
        exit 1
        ;;
esac

echo
echo "   Target: $REPO"
echo "   Version: $VERSION"
echo

# Step 7: Final confirmation
read -p "   Confirm publish? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "   Publishing cancelled"
    exit 0
fi
echo

# Step 8: Upload
echo "7. Uploading to $REPO..."
if [ "$REPO" = "testpypi" ]; then
    python3 -m twine upload --repository testpypi dist/*
else
    python3 -m twine upload dist/*
fi
echo "   ✓ Published"
echo

# Step 9: Show success
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ✅ Successfully published to $REPO!                "
echo "╚════════════════════════════════════════════════════════════╝"
echo
echo "View at: $REPO_URL"
echo
if [ "$REPO" = "testpypi" ]; then
    echo "Install with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ axiomeer"
else
    echo "Install with:"
    echo "  pip install axiomeer"
fi
echo
echo "Verify with:"
echo "  python3 -c 'import axiomeer; print(axiomeer.__version__)'"
echo
