#!/bin/bash
# scripts/release.sh - Prepares a new version for release

set -e

VERSION=$(grep "version =" pyproject.toml | sed -E 's/version = "(.*)"/\1/')
TAG="v$VERSION"

echo "Current version detected: $VERSION"

# 1. Update status and checks
echo "Verifying project state..."
grep -q "($TAG)" STATUS.md || (echo "Error: STATUS.md not updated for $TAG"; exit 1)
grep -q "## \[$VERSION\]" CHANGELOG.md || (echo "Error: CHANGELOG.md not updated for $VERSION"; exit 1)

# 2. Run tests before release
echo "Running tests..."
pytest

# 3. Clean and build for local verification
echo "Building package..."
rm -rf dist/
python3 -m build
twine check dist/*

# 4. Git operations
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Tag $TAG already exists. Skip tagging."
else
    echo "Tagging version $TAG..."
    git tag -a "$TAG" -m "Release $TAG"
    echo "Release tag $TAG created. Run 'git push --tags' to trigger GitHub Action."
fi

echo "Done. Local verification passed."
