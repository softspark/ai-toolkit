#!/usr/bin/env bash
# ai-toolkit-statusline.sh — comprehensive Claude Code status line.
#
# Renders one line combining: cwd, git state, context-window %, real session
# tokens (from JSONL), and the model name. Cost-estimate segment is opt-in via
# AI_TOOLKIT_STATUSLINE_SHOW_COST=1 — off by default to avoid alarming numbers.
#
# Wire-up: ai-toolkit installer adds this as default `statusLine` in
# ~/.claude/settings.json. Manual config:
#     {
#       "statusLine": {
#         "type": "command",
#         "command": "bash ~/.softspark/ai-toolkit/hooks/ai-toolkit-statusline.sh"
#       }
#     }
#
# Env vars (all optional):
#   AI_TOOLKIT_DIR                  — toolkit install location (auto-detected)
#   AI_TOOLKIT_STATUSLINE_DISABLE   — "1" silences output entirely
#   AI_TOOLKIT_STATUSLINE_BASELINE  — JSON baseline for trend arrow
#   AI_TOOLKIT_STATUSLINE_NO_COLOR  — "1" disables ANSI colors
#   AI_TOOLKIT_STATUSLINE_NO_TOKENS — "1" hides token segment
#   AI_TOOLKIT_STATUSLINE_NO_GIT    — "1" hides git segment
#   AI_TOOLKIT_STATUSLINE_SHOW_COST — "1" appends model-aware cost estimate
#
# Performance: ~200ms cold, scales with session length (JSONL line count).
# Soft-fails any segment whose data is missing.

set -u

[ "${AI_TOOLKIT_STATUSLINE_DISABLE:-0}" = "1" ] && exit 0

# ── Toolkit dir auto-detect ─────────────────────────────────────────────────
# Resolution order (first one that has session_token_stats.py wins):
#   1. AI_TOOLKIT_DIR env var (explicit override)
#   2. ~/.softspark/ai-toolkit/ — installer copies hook runtime scripts here
#   3. npm global root @softspark/ai-toolkit — works post-publish
#   4. Walk up from this script — dev fallback when running from source repo
TOOLKIT_DIR="${AI_TOOLKIT_DIR:-}"

_have_runtime() { [ -f "$1/scripts/session_token_stats.py" ]; }

if [ -z "$TOOLKIT_DIR" ] && _have_runtime "$HOME/.softspark/ai-toolkit"; then
    TOOLKIT_DIR="$HOME/.softspark/ai-toolkit"
fi
if [ -z "$TOOLKIT_DIR" ]; then
    NPM_ROOT="$(npm root -g 2>/dev/null)"
    if [ -n "$NPM_ROOT" ] && _have_runtime "$NPM_ROOT/@softspark/ai-toolkit"; then
        TOOLKIT_DIR="$NPM_ROOT/@softspark/ai-toolkit"
    fi
fi
if [ -z "$TOOLKIT_DIR" ] || ! _have_runtime "$TOOLKIT_DIR"; then
    CAND="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
    if [ -n "$CAND" ] && _have_runtime "$CAND"; then
        TOOLKIT_DIR="$CAND"
    fi
fi

# ── Colors ───────────────────────────────────────────────────────────────────
if [ "${AI_TOOLKIT_STATUSLINE_NO_COLOR:-0}" = "1" ] || [ ! -t 1 ]; then
    C_RESET="" C_GREEN="" C_CYAN="" C_BLUE="" C_RED="" C_YELLOW="" C_MAGENTA="" C_DIM=""
else
    C_RESET=$'\033[0m'
    C_GREEN=$'\033[1;32m'
    C_CYAN=$'\033[0;36m'
    C_BLUE=$'\033[1;34m'
    C_RED=$'\033[0;31m'
    C_YELLOW=$'\033[0;33m'
    C_MAGENTA=$'\033[0;35m'
    C_DIM=$'\033[2m'
fi

# ── Parse stdin from Claude Code in a single python3 invocation ─────────────
# 4 separate `python3 -c` calls spent ~200ms on subprocess startup. One call
# extracts every field we need and emits a tab-separated record we can read
# back into shell vars in a single `IFS=$'\t' read` — keeps total cold start
# under ~100ms on typical hardware.
INPUT="$(cat 2>/dev/null || true)"
PARSED="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
def get(d, path):
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
        if d is None:
            return ""
    return d if d is not None else ""
try:
    d = json.loads(sys.stdin.read() or "{}")
except Exception:
    d = {}
cwd = get(d, "cwd")
model = get(d, "model.display_name") or get(d, "model.id")
ctx = get(d, "context_window.used_percentage")
sid = get(d, "session_id")
print(f"{cwd}\t{model}\t{ctx}\t{sid}")
' 2>/dev/null)"

IFS=$'\t' read -r CWD MODEL_NAME CTX_USED SESSION_ID <<< "$PARSED"
[ -z "$CWD" ] && CWD="$PWD"

# ── Segment: prompt + dir ────────────────────────────────────────────────────
DIR_BASENAME="$(basename "$CWD" 2>/dev/null || echo '~')"
SEG_PROMPT="${C_GREEN}\xe2\x9e\x9c${C_RESET}  ${C_CYAN}${DIR_BASENAME}${C_RESET}"

# ── Segment: git ────────────────────────────────────────────────────────────
SEG_GIT=""
if [ "${AI_TOOLKIT_STATUSLINE_NO_GIT:-0}" != "1" ] && \
   git -C "$CWD" rev-parse --git-dir >/dev/null 2>&1; then
    BRANCH="$(git -C "$CWD" -c core.fsmonitor=false symbolic-ref --short HEAD 2>/dev/null)"
    if [ -n "$BRANCH" ]; then
        DIRTY=""
        if git -C "$CWD" -c core.fsmonitor=false status --porcelain 2>/dev/null | grep -q .; then
            DIRTY=" ${C_RED}\xe2\x9c\x97${C_RESET}"
        fi
        SEG_GIT=" ${C_BLUE}git:(${C_RED}${BRANCH}${C_BLUE})${C_RESET}${DIRTY}"
    fi
fi

# ── Segment: context window ──────────────────────────────────────────────────
SEG_CTX=""
if [ -n "$CTX_USED" ]; then
    CTX_INT="$(printf '%.0f' "$CTX_USED" 2>/dev/null || echo "$CTX_USED")"
    SEG_CTX=" ${C_YELLOW}ctx:${CTX_INT}%${C_RESET}"
fi

# ── Segment: tokens + cost ───────────────────────────────────────────────────
SEG_TOKENS=""
if [ "${AI_TOOLKIT_STATUSLINE_NO_TOKENS:-0}" != "1" ]; then
    STATS_SCRIPT="$TOOLKIT_DIR/scripts/session_token_stats.py"
    if [ -f "$STATS_SCRIPT" ]; then
        ARGS=(--cwd "$CWD" --json)
        STATS_JSON="$(python3 "$STATS_SCRIPT" "${ARGS[@]}" 2>/dev/null || true)"
        if [ -n "$STATS_JSON" ]; then
            SEG_TOKENS="$(printf '%s' "$STATS_JSON" | python3 -c "
import json, os, sys
try:
    d = json.loads(sys.stdin.read())
    t = d.get('totals', {})
    total = t.get('total', 0)
    if total <= 0:
        sys.exit(0)
    if total >= 1000:
        rendered = f'{total/1000:.1f}k'
    else:
        rendered = str(total)

    model = '${MODEL_NAME}'.lower()
    if 'opus' in model:
        rate_in, rate_out = 15.0, 75.0
    elif 'sonnet' in model:
        rate_in, rate_out = 3.0, 15.0
    elif 'haiku' in model:
        rate_in, rate_out = 0.80, 4.0
    else:
        rate_in, rate_out = 5.0, 25.0

    cost_input = (t.get('input', 0) / 1_000_000) * rate_in
    cost_output = (t.get('output', 0) / 1_000_000) * rate_out
    cost_cache_w = (t.get('cache_create', 0) / 1_000_000) * rate_in * 1.25
    cost_cache_r = (t.get('cache_read', 0) / 1_000_000) * rate_in * 0.10
    cost = cost_input + cost_output + cost_cache_w + cost_cache_r

    baseline_path = os.environ.get('AI_TOOLKIT_STATUSLINE_BASELINE', '')
    trend = ''
    if baseline_path and os.path.isfile(baseline_path):
        try:
            with open(baseline_path) as f:
                bl = json.load(f).get('total', 0)
            if bl > 0:
                delta = (total - bl) / bl
                arrow = '↓' if delta < 0 else '↑' if delta > 0 else ''
                if arrow:
                    trend = f' {arrow}{abs(delta)*100:.0f}%'
        except Exception:
            pass

    print(f'{rendered}|{cost:.2f}|{trend}')
except Exception:
    sys.exit(0)
" 2>/dev/null)"
            if [ -n "$SEG_TOKENS" ]; then
                IFS='|' read -r TOK_RENDERED TOK_COST TOK_TREND <<< "$SEG_TOKENS"
                SEG_TOKENS=" ${C_DIM}tok:${C_RESET}${TOK_RENDERED}${TOK_TREND}"
                if [ "${AI_TOOLKIT_STATUSLINE_SHOW_COST:-0}" = "1" ]; then
                    SEG_TOKENS+=" ${C_DIM}\$${C_RESET}${TOK_COST}"
                fi
            fi
        fi
    fi
fi

# ── Segment: model ───────────────────────────────────────────────────────────
SEG_MODEL=""
if [ -n "$MODEL_NAME" ]; then
    SEG_MODEL=" ${C_MAGENTA}${MODEL_NAME}${C_RESET}"
fi

# ── Render ───────────────────────────────────────────────────────────────────
printf "%b%b%b%b%b\n" \
    "$SEG_PROMPT" \
    "${SEG_GIT:-}" \
    "${SEG_CTX:-}" \
    "${SEG_TOKENS:-}" \
    "${SEG_MODEL:-}"
