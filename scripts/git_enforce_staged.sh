#!/bin/sh
# Abort commit if there are unstaged changes in the working tree.

# List files that differ between working tree and index
unstaged="$(git diff --name-only)"

if [ -n "$unstaged" ]; then
    echo "ERROR: Unstaged changes detected:"
    echo "$unstaged"
    echo
    echo "Please stage (or stash) all changes before committing."
    exit 1
fi

exit 0