#!/bin/bash

# Usage: ./scripts/bump_version.sh [major|minor|patch]

VERSION_FILE="version.txt"
CURRENT_VERSION=$(cat $VERSION_FILE)

# Split version into components
MAJOR=$(echo $CURRENT_VERSION | cut -d. -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d. -f2)
PATCH=$(echo $CURRENT_VERSION | cut -d. -f3)

# Increment based on argument
case "$1" in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    ;;
  *)
    echo "Usage: $0 [major|minor|patch]"
    exit 1
    ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo "$NEW_VERSION" > $VERSION_FILE
echo "Version bumped from $CURRENT_VERSION to $NEW_VERSION"

# Optionally, create git tag
echo "Create git tag? (y/n)"
read RESPONSE
if [ "$RESPONSE" = "y" ]; then
  git add $VERSION_FILE
  git commit -m "Bump version to $NEW_VERSION"
  git tag -a "v$NEW_VERSION" -m "Version $NEW_VERSION"
  echo "Tag created. Push with: git push && git push --tags"
fi