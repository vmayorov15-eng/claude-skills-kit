#!/bin/bash
# Claude Code status line
# Reads the session JSON on stdin (see https://code.claude.com/docs/en/statusline)
# and prints one line: model | context usage | cwd | git branch

input=$(cat)

# --- Model -------------------------------------------------------------
model=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "unknown"')

# --- Context window usage ----------------------------------------------
used_pct=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')
total_tokens=$(printf '%s' "$input" | jq -r '.context_window.total_input_tokens // empty')
window_size=$(printf '%s' "$input" | jq -r '.context_window.context_window_size // empty')

if [ -n "$used_pct" ]; then
    ctx=$(printf '%.0f%%' "$used_pct")
    if [ -n "$total_tokens" ] && [ -n "$window_size" ]; then
        ctx="${ctx} (${total_tokens}/${window_size})"
    fi
elif [ -n "$total_tokens" ] && [ -n "$window_size" ]; then
    ctx="${total_tokens}/${window_size} tokens"
else
    ctx="n/a"
fi

# --- Working directory (short form) -------------------------------------
cwd=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // ""')
if [ -n "$cwd" ]; then
    short_dir="${cwd/#$HOME/~}"
else
    short_dir="?"
fi

# --- Git branch (skip optional locks so we never block/write) -----------
branch=""
if [ -n "$cwd" ] && git -C "$cwd" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
    if [ -z "$branch" ]; then
        branch=$(git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
    fi
fi

# --- Colors (dimmed, since the status line renders dim in-terminal) -----
DIM=$'\033[2m'
RESET=$'\033[0m'
CYAN=$'\033[36m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'
GREEN=$'\033[32m'

line="${DIM}${CYAN}${model}${RESET}"
line="${line} ${DIM}|${RESET} ${DIM}${YELLOW}${ctx}${RESET}"
line="${line} ${DIM}|${RESET} ${DIM}${BLUE}${short_dir}${RESET}"
if [ -n "$branch" ]; then
    line="${line} ${DIM}|${RESET} ${DIM}${GREEN}${branch}${RESET}"
fi

printf '%s\n' "$line"
