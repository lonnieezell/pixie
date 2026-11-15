#!/usr/bin/env bash
# Human-in-the-loop reproduction loop.
# Copy this file, edit the steps below, and run it.
# The agent prepares the script; the user runs it, because it reads from the
# keyboard and the agent's Bash tool is not interactive.
#
# Usage (this file is in the diagnose skill's scripts/ folder, not the repo):
#   cp <diagnose skill folder>/scripts/hitl-loop.sh <scratch folder>/hitl.sh
#   Edit the steps in that copy. Then ask the user to type: ! bash <that path>
#   The `!` prefix runs it in the user's session, so its output lands in the conversation.
#
# Two helpers:
#   step "<instruction>"          → show instruction, wait for Enter
#   capture VAR "<question>"      → show question, read response into VAR
#
# At the end, every captured value is printed as KEY=VALUE for the agent to
# parse. Captures are listed automatically, so only edit the steps.
#
# `capture` reads one line. For a long error, ask for its key line.
#
# `capture` prints its value back to the terminal, where the agent reads it,
# so capture observations, and leave signing in to the user as a `step`.
#
# Adapted from mattpocock/skills (MIT). See THIRD_PARTY_NOTICES.md.

set -euo pipefail

CAPTURED=()

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [Enter when done] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
  CAPTURED+=("$var")
}

# --- edit below ---------------------------------------------------------

step "Open the app at http://localhost:3000 and sign in."

capture ERRORED "Click the 'Export' button. Did it throw an error? (y/n)"

capture ERROR_MSG "Paste the key line of the error message (or 'none'):"

# --- edit above ---------------------------------------------------------

printf '\n--- Captured ---\n'
for var in "${CAPTURED[@]+"${CAPTURED[@]}"}"; do
  printf '%s=%s\n' "$var" "${!var}"
done
