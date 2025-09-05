#!/bin/bash

# Define the remote repository URL
REMOTE_URL="https://github.com/herbbetz/betzBirdiary.git"

# Generate a commit message based on the current date and time
COMMIT_MESSAGE=$(date +"%y%m%d-%H%M")"-betzUbuntu"

# Navigate into the local repository directory
# Replace with the actual path to your repository if it's not the current directory
# cd /path/to/your/betzBirdiary

# Stage all changes
git add -A

# Check if there are any changes to commit
if ! git diff-index --quiet HEAD --; then
    # Commit the changes with the generated message
    git commit -m "$COMMIT_MESSAGE"

    # Push the changes to the 'main' branch on GitHub
    git push origin main

    echo "Successfully pushed changes to $REMOTE_URL"
else
    echo "No changes to commit. Local repository is up to date with the remote."
fi
