#!/bin/bash

# Commit hashes for specific versions
FISH_SHELL_COMMIT="2f6dd97"
TMUX_COMMIT="d217ba3"

# Function to get the primary branch (main or master)
get_primary_branch() {
    if git show-ref --verify --quiet refs/remotes/origin/main; then
        echo "main"
    elif git show-ref --verify --quiet refs/remotes/origin/master; then
        echo "master"
    else
        # Fallback to checking local branches
        if git show-ref --verify --quiet refs/heads/main; then
            echo "main"
        elif git show-ref --verify --quiet refs/heads/master; then
            echo "master"
        else
            echo "main" # Default fallback
        fi
    fi
}

# Function to update existing repo or clone new one
update_or_clone_repo() {
    local repo_url="$1"
    local dir_name="$2"
    local commit_hash="$3"

    if [ -d "$dir_name" ]; then
        (
            cd "$dir_name" || exit
            primary_branch=$(get_primary_branch)
            git checkout "$primary_branch"
            git pull
            git checkout "$commit_hash"
        )
    else
        (
            git clone "$repo_url" "$dir_name"
            cd "$dir_name" || exit
            git checkout "$commit_hash"
        )
    fi
}

mkdir -p ~/dev/others/base16/templates
cd ~/dev/others/base16/templates || exit

update_or_clone_repo "https://github.com/tomyun/base16-fish.git" "fish-shell" "$FISH_SHELL_COMMIT"
update_or_clone_repo "https://github.com/tinted-theming/base16-tmux.git" "tmux" "$TMUX_COMMIT"
