#!/usr/bin/env bash
# ai-toolkit-statusline.sh — comprehensive Claude Code status line.
#
# Renders one line. Left side: cwd, git, ctx%, i/o token split.
# Right side (right-aligned): effort level, model name.
# Optional cost segment is opt-in via AI_TOOLKIT_STATUSLINE_SHOW_COST=1.
#
# All token + cost data is read directly from Claude Code's statusLine stdin
# (context_window.total_input_tokens, total_output_tokens, cost.total_cost_usd,
# effort.level). No JSONL parsing in the hot path.
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
#   AI_TOOLKIT_STATUSLINE_NO_COLOR  — "1" disables ANSI colors
#   AI_TOOLKIT_STATUSLINE_NO_TOKENS — "1" hides i/o segment
#   AI_TOOLKIT_STATUSLINE_NO_GIT    — "1" hides git segment
#   AI_TOOLKIT_STATUSLINE_NO_EFFORT — "1" hides effort segment
#   AI_TOOLKIT_STATUSLINE_SHOW_COST — "1" appends Claude Code's reported cost
#   AI_TOOLKIT_STATUSLINE_DUMP      — "1" writes stdin to /tmp/cc-statusline-input.json
#
# Performance: ~50ms (single python3 parse of stdin, one git invocation).

set -u

[ "${AI_TOOLKIT_STATUSLINE_DISABLE:-0}" = "1" ] && exit 0

# ── Colors ───────────────────────────────────────────────────────────────────
# Claude Code captures stdout via pipe but interprets ANSI escapes when it
# renders the statusline. So always emit colors unless explicitly disabled.
if [ "${AI_TOOLKIT_STATUSLINE_NO_COLOR:-0}" = "1" ]; then
    C_RESET="" C_GREEN="" C_BOLD_GREEN="" C_CYAN="" C_BLUE="" C_RED=""
    C_YELLOW="" C_MAGENTA="" C_DIM="" C_BOLD_YELLOW="" C_ORANGE=""
else
    C_RESET=$'\033[0m'
    C_GREEN=$'\033[0;32m'
    C_BOLD_GREEN=$'\033[1;32m'
    C_CYAN=$'\033[0;36m'
    C_BLUE=$'\033[1;34m'
    C_RED=$'\033[0;31m'
    C_YELLOW=$'\033[0;33m'
    C_BOLD_YELLOW=$'\033[1;33m'
    C_MAGENTA=$'\033[0;35m'
    C_DIM=$'\033[2m'
    C_ORANGE=$'\033[38;5;208m'
fi

# ── Parse stdin in one python3 invocation ────────────────────────────────────
INPUT="$(cat 2>/dev/null || true)"

if [ "${AI_TOOLKIT_STATUSLINE_DUMP:-0}" = "1" ] && [ -n "$INPUT" ]; then
    printf '%s' "$INPUT" > /tmp/cc-statusline-input.json 2>/dev/null
fi

PARSED="$(printf '%s' "$INPUT" | python3 -c '
import json, sys
def get(d, path):
    for k in path.split("."):
        d = d.get(k) if isinstance(d, dict) else None
        if d is None:
            return ""
    return d if d is not None else ""
def fmt_tokens(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)
try:
    d = json.loads(sys.stdin.read() or "{}")
except Exception:
    d = {}
cwd = get(d, "cwd") or ""
model = get(d, "model.display_name") or get(d, "model.id") or ""
ctx_pct = get(d, "context_window.used_percentage")
in_tok = fmt_tokens(get(d, "context_window.total_input_tokens"))
out_tok = fmt_tokens(get(d, "context_window.total_output_tokens"))
cost = get(d, "cost.total_cost_usd")
try:
    cost_str = f"{float(cost):.2f}" if cost != "" else ""
except (TypeError, ValueError):
    cost_str = ""
effort = get(d, "effort.level") or ""
print(f"{cwd}\t{model}\t{ctx_pct}\t{in_tok}\t{out_tok}\t{cost_str}\t{effort}")
' 2>/dev/null)"

IFS=$'\t' read -r CWD MODEL_NAME CTX_USED IN_TOK OUT_TOK COST EFFORT <<< "$PARSED"
[ -z "$CWD" ] && CWD="$PWD"

# ── Segment: prompt + dir ────────────────────────────────────────────────────
DIR_BASENAME="$(basename "$CWD" 2>/dev/null || echo '~')"
SEG_PROMPT="${C_BOLD_GREEN}\xe2\x9e\x9c${C_RESET}  ${C_CYAN}${DIR_BASENAME}${C_RESET}"

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

# ── Segment: context window as progress bar ────────────────────────────────
# 10-cell bar with usage-shaded color: green <50%, yellow 50-79%, red ≥80%.
build_ctx_bar() {
    local pct=$1
    local cells=10
    local filled=$(( (pct * cells + 50) / 100 ))
    [ "$filled" -gt "$cells" ] && filled=$cells
    [ "$filled" -lt 0 ] && filled=0
    local color
    if [ "$pct" -ge 90 ]; then
        color="$C_RED"
    elif [ "$pct" -ge 70 ]; then
        color="$C_ORANGE"
    else
        color="$C_GREEN"
    fi
    local bar=""
    local i=0
    while [ "$i" -lt "$filled" ]; do
        bar+="\xe2\x96\x88"  # █  FULL BLOCK
        i=$((i+1))
    done
    local empty=""
    while [ "$i" -lt "$cells" ]; do
        empty+="\xe2\x96\x91"  # ░  LIGHT SHADE
        i=$((i+1))
    done
    printf '%b' "${color}${bar}${C_DIM}${empty}${C_RESET}"
}

SEG_CTX=""
if [ -n "$CTX_USED" ]; then
    CTX_INT="$(printf '%.0f' "$CTX_USED" 2>/dev/null || echo "$CTX_USED")"
    case "$CTX_INT" in
        ''|*[!0-9]*) CTX_INT=0 ;;
    esac
    SEG_CTX=" $(build_ctx_bar "$CTX_INT") ${C_DIM}${CTX_INT}%${C_RESET}"
fi

# ── Segment: tokens with up/down arrows ─────────────────────────────────────
# ↑ green = upload (input tokens sent to model)
# ↓ red   = download (output tokens received from model)
SEG_TOKENS=""
if [ "${AI_TOOLKIT_STATUSLINE_NO_TOKENS:-0}" != "1" ] && [ -n "$IN_TOK" ] && \
   { [ "$IN_TOK" != "0" ] || [ "$OUT_TOK" != "0" ]; }; then
    SEG_TOKENS="  ${C_BOLD_GREEN}\xe2\x86\x91${IN_TOK}${C_RESET} ${C_RED}\xe2\x86\x93${OUT_TOK}${C_RESET}"
    if [ "${AI_TOOLKIT_STATUSLINE_SHOW_COST:-0}" = "1" ] && [ -n "$COST" ]; then
        SEG_TOKENS+=" ${C_BOLD_GREEN}\$${COST}${C_RESET}"
    fi
fi

# ── Right-aligned segments: effort + model ───────────────────────────────────
SEG_EFFORT=""
if [ "${AI_TOOLKIT_STATUSLINE_NO_EFFORT:-0}" != "1" ] && [ -n "$EFFORT" ]; then
    case "$EFFORT" in
        xhigh|high) E_COLOR="$C_BOLD_YELLOW" ;;
        medium)     E_COLOR="$C_YELLOW" ;;
        *)          E_COLOR="$C_DIM" ;;
    esac
    SEG_EFFORT="${C_DIM}effort:${C_RESET}${E_COLOR}${EFFORT}${C_RESET}"
fi

SEG_MODEL=""
if [ -n "$MODEL_NAME" ]; then
    SEG_MODEL="${C_MAGENTA}${MODEL_NAME}${C_RESET}"
fi

# ── Render (left-aligned, single line) ───────────────────────────────────────
# Right-align was attempted earlier but Claude Code reserves variable-width
# space on the right of the rendered statusline for its own UI overlay,
# truncating any content right-padded near COLUMNS. Left-align with effort
# and model as trailing segments avoids the truncation.
SEG_TRAILER=""
[ -n "$SEG_EFFORT" ] && SEG_TRAILER+=" $SEG_EFFORT"
[ -n "$SEG_MODEL" ] && SEG_TRAILER+=" $SEG_MODEL"

printf "%b%b%b%b%b\n" \
    "$SEG_PROMPT" \
    "${SEG_GIT:-}" \
    "${SEG_CTX:-}" \
    "${SEG_TOKENS:-}" \
    "${SEG_TRAILER}"
