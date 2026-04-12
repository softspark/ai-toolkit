---
title: "Plan: Local Dashboard — ai-toolkit ui"
category: planning
service: ai-toolkit
tags:
  - dashboard
  - developer-experience
  - web-ui
  - tui
  - configuration
  - visualization
doc_type: plan
status: proposed
created: "2026-04-10"
last_updated: "2026-04-12"
completion: "0%"
description: "Ephemeral local web dashboard for ai-toolkit. Provides visual management of agents, skills, hooks, plugins, stats, config inheritance, project registry, and configuration profiles. Zero external dependencies — stdlib Node.js server with embedded HTML/CSS/JS. Launched via `ai-toolkit ui`."
---

# Plan: Local Dashboard — `ai-toolkit ui`

**Status:** Proposed
**Completion:** 0%
**Created:** 2026-04-10
**Origin:** DX friction — managing 44 agents, 92 skills, 21 hooks, 11 plugin packs, and multiple profiles via CLI only creates a steep learning curve for new adopters. Visual management lowers the adoption barrier.
**Estimated Effort:** 6-7 weeks (1 person)

---

## 1. Objective

Create an `ai-toolkit ui` command that launches an ephemeral local HTTP server serving a single-page web dashboard. The dashboard provides visual management of all toolkit components — no more memorizing CLI flags.

**Key design principles:**
- **Zero external dependencies** — stdlib Node.js `http` module, embedded HTML/CSS/JS (same approach as `visual-server.cjs` in `/write-a-prd`). Server lives in `app/dashboard/` (not `scripts/`) — aligns with `visual-server.cjs` precedent and the "scripts/ = Python stdlib only" convention
- **Ephemeral** — auto-kills after 30 minutes of inactivity (matching existing companion pattern)
- **Read-write** — reads state from `~/.ai-toolkit/state.json`, `~/.claude/settings.json`, `manifest.json`; writes config changes through existing CLI commands (never mutates files directly)
- **Dark theme** — premium aesthetic, responsive, glassmorphism accents
- **Offline** — no CDN dependencies, no external fonts, no analytics
- **Port discovery** — starts on 3141, auto-increments if busy

---

## 1a. Functional Requirements

| ID | Requirement | Priority | Success Metric |
|----|-------------|----------|----------------|
| FR1 | HTTP server with auto-kill + port discovery | Must | Starts, auto-kills after 30 min, increments port if busy |
| FR2 | Read API endpoints (status, agents, skills, hooks, plugins, stats, config, mcp) | Must | All 8 endpoints return valid JSON |
| FR3 | Action execution via `POST /api/action` with SSE streaming | Must | Command output streamed, exit code returned |
| FR4 | Overview page with health checks + component counts | Must | Live data, matches `ai-toolkit validate` output |
| FR5 | Agents page with grid view + category filter | Must | All 44 agents parsed, 10 categories filterable |
| FR6 | Skills page with type/effort filter + sortable table | Must | All 92 skills, 3 type badges |
| FR7 | Hooks page with lifecycle diagram + profile toggle | Should | 21 hooks, 3 profiles toggleable |
| FR8 | Plugins page with install/remove action buttons | Should | Action triggers CLI via POST /api/action |
| FR9 | Config page with profile/persona management | Should | Reads + writes profiles via CLI |
| FR10 | Stats page with inline SVG charts | Should | Bar chart + trend line minimum (v1) |
| FR11 | MCP template browser with add/remove | Could | 25 templates browseable |
| FR12 | Dark theme + glassmorphism CSS design system | Must | Zero external CSS/font deps |
| FR13 | Client-side SPA routing (hash-based) | Must | Navigation without page reload |
| FR14 | Responsive design (desktop, tablet, mobile) | Should | 3 breakpoints, usable on mobile |
| FR15 | Command allowlist enforcement on /api/action | Must | Non-allowlisted commands → 403 |

---

## 2. Architecture Overview

```
ai-toolkit ui [--port 3141] [--no-auto-kill]

  ┌──────────────────────────────────────────────────────────┐
  │                   Local Dashboard                         │
  │                                                          │
  │  Server: stdlib Node.js http (0 deps)                    │
  │  Port: 3141 (auto-increment if busy)                    │
  │  Auto-kill: 30 min idle (configurable)                   │
  │                                                          │
  │  Pages:                                                  │
  │    /                        Overview + health             │
  │    /agents                  44 agents — grid view         │
  │    /skills                  92 skills — filterable table  │
  │    /hooks                   21 hooks — lifecycle diagram  │
  │    /plugins                 11 packs — install/remove     │
  │    /config                  Profile / persona / modules   │
  │    /stats                   Usage analytics + charts      │
  │    /mcp                     MCP templates — add/remove    │
  │    /extends                 Config inheritance — extends status, merge view, enforcement │
  │    /projects                Project registry — registered projects, stale detection       │
  │    (credentials page deferred — requires cloud-security-pack CLI) │
  │                                                          │
  │  API (JSON, internal):                                   │
  │    GET  /api/status         Toolkit state                 │
  │    GET  /api/agents         Agent catalog                 │
  │    GET  /api/skills         Skill catalog                 │
  │    GET  /api/hooks          Hook definitions              │
  │    GET  /api/plugins        Plugin packs + install state  │
  │    GET  /api/stats          Usage statistics              │
  │    GET  /api/config         Current configuration         │
  │    GET  /api/mcp            MCP templates + installed     │
  │    GET  /api/extends        Config inheritance state      │
  │    GET  /api/projects       Registered project list       │
  │    (credentials endpoint deferred — see Future section)   │
  │    POST /api/action         Execute CLI command           │
  │                                                          │
  │  Static assets (inlined in server.js):                   │
  │    HTML template (single page, client-side routing)      │
  │    CSS  (dark theme, glassmorphism, responsive)          │
  │    JS   (vanilla, fetch-based, no framework)             │
  └──────────────────────────────────────────────────────────┘
```

### Action Execution Model

All write operations go through `POST /api/action`:

```json
{
  "command": "plugin",
  "args": ["install", "memory-pack"]
}
```

The server spawns `ai-toolkit <command> <args>` as a child process, streams stdout/stderr back via SSE (Server-Sent Events), and returns exit code. This ensures:
1. All existing validation logic in CLI scripts executes
2. No file mutation logic duplicated in the dashboard
3. Audit trail identical to CLI usage

---

## 3. Progress Tracking

| # | Feature | Priority | Status | Est. Time | Notes |
|---|---------|----------|--------|-----------|-------|
| 1.1 | HTTP server + auto-kill + port discovery | P0 | Proposed | 1d | stdlib Node.js, ephemeral lifecycle |
| 1.2 | API layer — read endpoints (status, agents, skills, hooks, plugins, stats, config, mcp) | P0 | Proposed | 2d | Parse frontmatter, state.json, hooks.json |
| 1.3 | API layer — action execution endpoint | P0 | Proposed | 1d | Spawn CLI + SSE streaming |
| 2.1 | Overview page (health, component counts, version) | P0 | Proposed | 1.5d | Dashboard landing page |
| 2.2 | Agents page (grid + detail view + category filter) | P0 | Proposed | 2d | Parse agent .md frontmatter |
| 2.3 | Skills page (filterable table + type badges + effort) | P0 | Proposed | 2d | Task / hybrid / knowledge taxonomy |
| 2.4 | Hooks page (lifecycle diagram + profile toggle) | P1 | Proposed | 2d | Visual event → script mapping |
| 2.5 | Plugins page (install/remove/status cards) | P1 | Proposed | 2d | Action buttons trigger CLI |
| 2.6 | Config page (profile/persona/modules checkboxes) | P1 | Proposed | 2d | Read/write profiles |
| 2.7 | Stats page (usage charts, skill invocation heatmap) | P1 | Proposed | 3.5d | Hand-drawn SVG charts (bar, heatmap, trend), no chart library |
| 2.8 | MCP page (template browser, add/remove) | P2 | Proposed | 1.5d | 25 MCP templates |
| 2.9 | Config Inheritance page (extends status, merge view, enforcement) | P1 | Proposed | 2d | v1.8.0 feature — extends pipeline visualization, lock file status, enforcement indicators |
| 2.10 | Projects page (registry, stale detection, bulk update) | P1 | Proposed | 1.5d | v1.9.0 feature — registered projects list, prune action, update-all trigger |
| 2.11 | ~~Credentials page~~ | — | Deferred | — | Requires cloud-security-pack CLI commands (not yet implemented) |
| 3.1 | CSS design system (dark theme, glassmorphism, responsive) | P0 | Proposed | 2d | Premium aesthetic, zero external deps |
| 3.2 | Client-side routing + navigation | P0 | Proposed | 1d | Hash-based SPA routing |
| 4.1 | CLI command registration (`ai-toolkit ui`) | P0 | Proposed | 0.5d | bin/ai-toolkit.js integration |
| 4.2 | Tests (bats + node:test) | P1 | Proposed | 3d | Server lifecycle (bats) + API endpoints + SSE streaming (node:test) |
| 4.3 | Documentation | P1 | Proposed | 2.5d | README, CLAUDE.md, ARCHITECTURE.md, package.json, llms.txt, llms-full.txt, AGENTS.md, skills-catalog.md, architecture-overview.md |

**Phasing:**
- **Phase 1 (week 1-3):** Foundation — server, API, design system, overview page, agents page, skills page
- **Phase 2 (week 3-5):** Interactive — hooks, plugins, config, action execution, stats
- **Phase 3 (week 6-7):** Polish — MCP, responsive testing, tests, documentation (2.5d docs — all 9 docs per CLAUDE.md rules)

> **Demand validation gate:** Ship Phase 1 (server + overview + agents + skills) as MVP. Announce, measure adoption (track `ai-toolkit ui` invocations via `stats.json`). Only build Phase 2 interactive pages if usage > 10 sessions/week across early adopters.

---

## 4. Dependency Graph

```
                     Phase 1: Foundation (week 1-3)
                     ================================
HTTP server (1.1) ──────┐
                        ├──► API read layer (1.2) ──► Overview page (2.1)
CSS design system (3.1) ┤                          ├──► Agents page (2.2)
Client routing (3.2) ───┘                          └──► Skills page (2.3)

                     Phase 2: Interactive (week 3-5)
                     =================================
API action layer (1.3) ─┐
                        ├──► Hooks page (2.4)
                        ├──► Plugins page (2.5)
                        ├──► Config page (2.6)
                        ├──► Stats page (2.7)
                        ├──► Config Inheritance page (2.9)
                        └──► Projects page (2.10)

                     Phase 3: Polish (week 6-7)
                     ===========================
                        ├──► MCP page (2.8)
                        ├──► CLI registration (4.1)
                        └──► Tests + docs (4.2, 4.3)
```

---

## 5. Detailed Implementation

### Phase 1: Foundation (week 1-3)

#### 1.1 HTTP Server + Lifecycle

**File:** `app/dashboard/server.js`

```javascript
// Key design decisions:
// 1. stdlib only — require('http'), require('fs'), require('path')
// 2. Auto-kill timer — 30 min idle, reset on every request
// 3. Port discovery — try 3141, increment until available
// 4. Single-file deployment — HTML/CSS/JS embedded as template literals
// 5. Same pattern as visual-brainstorming companion in /write-a-prd

const AUTO_KILL_MS = 30 * 60 * 1000; // 30 minutes
const DEFAULT_PORT = 3141;
const MAX_PORT_ATTEMPTS = 10;
```

**CLI interface:**
```bash
ai-toolkit ui                    # open dashboard on port 3141
ai-toolkit ui --port 4000        # custom port
ai-toolkit ui --no-auto-kill     # disable 30 min auto-kill
ai-toolkit ui --open             # auto-open browser (default: true)
```

**Lifecycle:**
1. Start HTTP server on available port
2. Open browser via `open` (macOS) / `xdg-open` (Linux)
3. Reset idle timer on every request
4. After 30 min inactivity → `process.exit(0)` with console message
5. `Ctrl+C` → graceful shutdown

**Security:**
- Bind to `127.0.0.1` only (never `0.0.0.0`)
- No authentication needed (localhost only, ephemeral)
- POST `/api/action` validates command against allowlist (same commands as CLI)
- No file uploads, no eval, no template injection

**Files:**

| File | Action | Description |
|------|--------|-------------|
| `app/dashboard/server.js` | CREATE | HTTP server + API + embedded UI |
| `app/dashboard/api.js` | CREATE | API endpoint handlers |
| `app/dashboard/assets.js` | CREATE | Embedded HTML/CSS/JS templates |

**Success Criteria:**
- [ ] Server starts on port 3141 (or next available)
- [ ] Auto-kills after 30 min idle
- [ ] Browser auto-opens on launch
- [ ] Binds to 127.0.0.1 only
- [ ] `Ctrl+C` graceful shutdown

---

#### 1.2 API Layer — Read Endpoints

All endpoints return JSON. Data sources:

| Endpoint | Source | Description |
|----------|--------|-------------|
| `GET /api/status` | `~/.ai-toolkit/state.json` + `manifest.json` | Version, profile, installed modules |
| `GET /api/agents` | `app/agents/*.md` frontmatter | Name, description, tools, triggers, category |
| `GET /api/skills` | `app/skills/*/SKILL.md` frontmatter | Name, type, effort, agent, description |
| `GET /api/hooks` | `app/hooks.json` | Event, script, description, profile |
| `GET /api/plugins` | `app/plugins/*/plugin.json` + state | Name, domain, status, installed?, components |
| `GET /api/stats` | `~/.ai-toolkit/stats.json` | Skill invocation counts, dates |
| `GET /api/config` | `~/.ai-toolkit/state.json` + settings | Profile, persona, modules, hook profile |
| `GET /api/mcp` | `app/mcp-templates/*.json` + `.mcp.json` | Available templates, installed servers |
| `GET /api/extends` | `.ai-toolkit.json` + `.ai-toolkit.lock.json` + `state.json` | Extends status, resolved base configs, enforcement, lock file state |
| `GET /api/projects` | `~/.ai-toolkit/projects.json` | Registered projects with path, profile, extends, last_updated, exists status |
| ~~`GET /api/credentials`~~ | — | Deferred — requires cloud-security-pack CLI |

**Frontmatter parser:** Reuse the YAML-subset parser pattern from existing `scripts/frontmatter.py` — port to JS (simple `---` delimited key-value extraction, covers all toolkit frontmatter which is flat YAML).

**Response format (example):**
```json
{
  "agents": [
    {
      "name": "backend-specialist",
      "description": "Expert backend architect for Node.js, Python, PHP...",
      "tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
      "triggers": ["backend", "server", "api", "endpoint"],
      "category": "development",
      "file": "app/agents/backend-specialist.md"
    }
  ],
  "meta": { "count": 44, "categories": 10 }
}
```

**Success Criteria:**
- [ ] All 8 read endpoints return valid JSON
- [ ] Agent frontmatter parsed for all 44 agents
- [ ] Skill frontmatter parsed for all 92 skills
- [ ] Stats endpoint handles missing stats.json gracefully

---

#### 1.3 API Layer — Action Execution

**Endpoint:** `POST /api/action`

```json
// Request
{
  "command": "plugin",
  "args": ["install", "memory-pack"]
}

// Response (SSE stream)
event: stdout
data: Installing memory-pack...

event: stdout
data: ✓ Hooks installed

event: done
data: {"exitCode": 0, "duration": 1234}
```

**Command allowlist:**
```javascript
const ALLOWED_COMMANDS = [
  'plugin install', 'plugin remove', 'plugin update', 'plugin clean',
  'mcp add', 'mcp remove',
  'install --profile', 'install --persona',
  'update', 'validate', 'doctor', 'doctor --fix',
  'stats', 'stats --reset',
  'config validate', 'config diff', 'config check', 'config init',
  'projects', 'projects --prune',
  // 'credentials add/remove/test' — deferred until cloud-security-pack CLI ships
];
```

**Security:** Commands not in allowlist → 403. No shell injection — args passed as array to `execFile`, never interpolated into a string.

**Success Criteria:**
- [ ] SSE streaming of command output
- [ ] Exit code returned in final event
- [ ] Command allowlist enforced
- [ ] No shell injection possible
- [ ] Concurrent commands rejected (one at a time)

---

### Phase 2: UI Pages (week 3-5)

#### 2.1 Overview Page

The landing page — first thing the user sees.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  ai-toolkit v1.5.1              [● running]     │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐       │
│  │  44  │  │  92  │  │  21  │  │  11  │       │
│  │agents│  │skills│  │hooks │  │packs │       │
│  └──────┘  └──────┘  └──────┘  └──────┘       │
│                                                 │
│  Profile: standard    Persona: (none)           │
│  Hook Profile: standard                         │
│  Node: v22.x    Python: 3.12                    │
│                                                 │
│  ┌─ Health ──────────────────────────────────┐  │
│  │ ✓ Constitution symlinked                  │  │
│  │ ✓ Hooks installed (21/21)                 │  │
│  │ ✓ Agents symlinked (44/44)                │  │
│  │ ⚠ 2 plugins not installed                 │  │
│  │ ✓ MCP servers: 3 configured               │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌─ Recent Activity ─────────────────────────┐  │
│  │ /review  — 12 invocations (last: 2h ago)  │  │
│  │ /commit  — 8 invocations (last: 5h ago)   │  │
│  │ /test    — 6 invocations (last: 1d ago)   │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**Data sources:** `/api/status` + `/api/stats` + `/api/plugins`

**Success Criteria:**
- [ ] Component counts rendered from live data
- [ ] Health checks match `ai-toolkit validate` output
- [ ] Recent activity from stats.json
- [ ] Responsive on mobile-width screens

---

#### 2.2 Agents Page

**Layout:** Grid of agent cards, filterable by category (10 categories).

**Card design:**
```
┌─────────────────────────────────┐
│ 🔧 backend-specialist          │
│                                 │
│ Expert backend architect for    │
│ Node.js, Python, PHP...        │
│                                 │
│ Tools: Read, Write, Edit, Bash  │
│ Triggers: backend, server, api  │
│                                 │
│ [View Definition]               │
└─────────────────────────────────┘
```

**Features:**
- Category filter pills (development, security, data, infrastructure, etc.)
- Search by name/description/trigger
- Click card → modal with full agent definition (rendered markdown)
- Agent count per category in filter pills

---

#### 2.3 Skills Page

**Layout:** Filterable table with type badges.

| Skill | Type | Effort | Agent | Description |
|-------|------|--------|-------|-------------|
| /commit | task | medium | — | Structured commit with linting |
| /review | hybrid | high | code-reviewer | Code review: quality, security |
| clean-code | knowledge | — | — | Auto-loaded code quality patterns |

**Features:**
- Filter by type (task / hybrid / knowledge)
- Filter by effort (low / medium / high / max)
- Search by name/description
- Sort by any column
- Badge colors: task=blue, hybrid=purple, knowledge=green

---

#### 2.4 Hooks Page

**Layout:** Lifecycle diagram with profile toggle (minimal/standard/strict).

**Visualization:**
```
Event Timeline (horizontal flow):
  PreToolUse ──► ToolUse ──► PostToolUse ──► Notification
       │              │             │              │
  guard-path.sh   (tool exec)  quality-check.sh  track-usage.sh
  guard-destructive.sh          session-context.sh
```

**Features:**
- Lifecycle event diagram — visual mapping of event → hook script(s)
- Profile toggle — show/hide hooks per profile (minimal hides most, strict shows all)
- Hook detail panel — click hook name to see: script path, description, when it fires, which profile includes it
- Profile diff — highlight which hooks are added/removed between profiles
- Status indicators — green (installed), red (missing script), yellow (overridden by plugin)

**Data source:** `app/hooks.json` + `~/.ai-toolkit/hooks/` filesystem check

**Success Criteria:**
- [ ] All 21 hooks rendered with correct lifecycle event
- [ ] Profile toggle filters hooks correctly
- [ ] Missing hook scripts shown with warning indicator
- [ ] Hook detail panel shows script content preview

---

#### 2.5 Plugins Page

**Layout:** Cards with install/remove buttons.

```
┌─────────────────────────────────┐
│ 🧩 memory-pack        ● installed │
│                                 │
│ SQLite-based persistent memory  │
│ with FTS5 search across sessions│
│                                 │
│ Skills: 1  Hooks: 2  Agents: 0  │
│ DB size: 2.4 MB  Obs: 1,234     │
│                                 │
│ [Update]  [Clean]  [Remove]     │
└─────────────────────────────────┘
```

**Actions:** Install, update, remove, clean — all via `POST /api/action` → `ai-toolkit plugin <action> <name>`. SSE output shown in a slide-out console panel.

---

#### 2.6 Config Page

**Layout:** Form with current configuration, editable.

**Sections:**
1. **Profile selector:** minimal / standard / strict (radio buttons)
2. **Persona selector:** none / backend-lead / frontend-lead / devops-eng / junior-dev
3. **Hook profile:** minimal / standard / strict
4. **Installed modules:** checkboxes for each module from manifest.json
5. **Language rules:** detected languages + override checkboxes
6. **Editor configs:** which editors are configured (read-only status)

**Save:** Generates and executes the equivalent `ai-toolkit install --profile X --persona Y --modules A,B,C` command.

---

#### 2.7 Stats Page

**Layout:** Usage analytics with inline SVG charts.

**Charts (SVG, hand-drawn — no chart library):**
1. **Skill invocation bar chart** — top 15 most-used skills
2. **Invocation heatmap** — 7x24 grid (day of week × hour) showing when skills are used
3. **Effort distribution** — pie chart of low/medium/high/max invocations
4. **Trend line** — daily invocations over last 30 days

**Data source:** `~/.ai-toolkit/stats.json` (written by `track-usage.sh` hook)

**SVG implementation notes:**
- All charts rendered as inline SVG strings in `assets.js` — no external chart library
- Bar chart: `<rect>` elements with calculated heights, axis labels as `<text>`
- Heatmap: 7x24 grid of `<rect>` with color intensity mapped to invocation count (0=transparent, max=accent-primary)
- Trend line: `<polyline>` with data points as `<circle>`, area fill via `<polygon>`
- Pie chart: `<path>` arcs calculated from percentages (use `Math.cos`/`Math.sin` for arc endpoints)
- All charts use CSS custom properties for colors (respects design system tokens)

**Fallback:** If hand-drawn SVG proves too complex for 4 chart types in 3.5d budget, reduce to 2 charts (bar + trend) for v1 and defer heatmap + pie to v2.

**Success Criteria:**
- [ ] All 4 chart types render from live stats.json data
- [ ] Empty state when stats.json missing: "No usage data yet — skills will appear here after first use"
- [ ] Charts responsive (SVG viewBox scales to container width)
- [ ] Tooltip on hover showing exact counts

---

#### 2.9 Config Inheritance Page (`/extends`)

**Layout:** Extends pipeline visualization + enforcement status.

```
┌─────────────────────────────────────────────────┐
│  Config Inheritance                              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─ Extends Chain ──────────────────────────┐   │
│  │ @acme/ai-toolkit-config v2.1.0           │   │
│  │   → standard profile                     │   │
│  │   → 5 agents enabled                     │   │
│  │   → 2 rules injected                     │   │
│  │   → Lock: sha256:abc1... (up-to-date)    │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─ Enforcement ────────────────────────────┐   │
│  │ ✓ Required agents: security-auditor      │   │
│  │ ✓ Min hook profile: standard             │   │
│  │ ✗ Forbidden overrides: constitution      │   │
│  │ ✓ Constitution articles I-V: immutable   │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌─ Constitution Amendments ────────────────┐   │
│  │ Art. I-V — immutable (toolkit)           │   │
│  │ Art. 6 — Data Sovereignty (base)         │   │
│  │ Art. 7 — Audit Compliance (base)         │   │
│  │ Art. 8 — API Standards (project) ★       │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  [Validate] [Diff] [Check]                      │
└─────────────────────────────────────────────────┘
```

**Data source:** `/api/extends` — reads `.ai-toolkit.json`, `.ai-toolkit.lock.json`, `state.json` extends metadata.

**Features:**
- Visual extends chain (base → project) with version + integrity
- Enforcement status indicators (pass/fail per constraint)
- Constitution article list with source labels (toolkit/base/project)
- Lock file freshness indicator
- Action buttons: validate, diff, check — via `POST /api/action`
- Empty state when no `.ai-toolkit.json`: "No config inheritance configured — run `ai-toolkit config init`"

**Success Criteria:**
- [ ] Extends chain rendered from resolved metadata
- [ ] Enforcement constraints shown with pass/fail indicators
- [ ] Constitution articles grouped by source
- [ ] Lock file staleness warning when outdated
- [ ] Action buttons trigger CLI commands via SSE

---

#### 2.10 Projects Page (`/projects`)

**Layout:** Registered project list with status and actions.

```
┌─────────────────────────────────────────────────┐
│  Registered Projects (5)         [Update All]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ✓ ~/code/my-service                            │
│    profile: standard | extends: @acme/config    │
│    updated: 2026-04-12 09:00                    │
│                                          [Remove]│
│                                                 │
│  ✓ ~/code/api-gateway                           │
│    profile: strict | extends: @acme/config      │
│    updated: 2026-04-12 09:00                    │
│                                          [Remove]│
│                                                 │
│  ✗ ~/code/old-project  (MISSING)                │
│    profile: standard                            │
│    registered: 2026-03-15                       │
│                                   [Prune] [Remove]│
│                                                 │
│  [Prune All Stale]                              │
└─────────────────────────────────────────────────┘
```

**Data source:** `/api/projects` — reads `~/.ai-toolkit/projects.json`, checks path existence.

**Features:**
- List all registered projects with exists/missing status
- Profile and extends info per project
- Last updated timestamp
- Remove button per project → `POST /api/action` `projects remove <path>`
- Prune stale button → `POST /api/action` `projects --prune`
- Update All button → `POST /api/action` `update` (triggers parallel update)
- Empty state: "No registered projects — run `ai-toolkit install --local` in a project"

**Success Criteria:**
- [ ] All registered projects listed with correct status
- [ ] Stale projects highlighted with warning
- [ ] Prune action removes stale entries
- [ ] Update All triggers parallel update via SSE
- [ ] Remove button deregisters specific project

---

### Phase 3: Polish (week 6-7)

#### 3.1 CSS Design System

**Design tokens:**
```css
:root {
  /* Dark theme palette */
  --bg-primary: #0f0f14;
  --bg-secondary: #1a1a24;
  --bg-card: rgba(255, 255, 255, 0.04);
  --bg-glass: rgba(255, 255, 255, 0.06);
  --border-glass: rgba(255, 255, 255, 0.08);

  /* Accent colors (derived from SoftSpark brand) */
  --accent-primary: #6366f1;    /* indigo */
  --accent-secondary: #8b5cf6;  /* violet */
  --accent-success: #10b981;    /* emerald */
  --accent-warning: #f59e0b;    /* amber */
  --accent-danger: #ef4444;     /* red */

  /* Typography */
  --font-sans: system-ui, -apple-system, sans-serif;
  --font-mono: 'SF Mono', 'Cascadia Code', monospace;

  /* Spacing scale */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;

  /* Glassmorphism */
  --glass-blur: 12px;
  --glass-bg: rgba(255, 255, 255, 0.05);
  --glass-border: rgba(255, 255, 255, 0.1);
}
```

**Components:**
- Cards with glassmorphism backdrop-filter
- Badge pills (type, effort, status)
- Sidebar navigation with active state
- Console output panel (slide-out, monospace)
- Modal overlays for detail views
- Toast notifications for action results
- Skeleton loading states

**Responsive breakpoints:**
- Desktop: 1200px+ (sidebar + content)
- Tablet: 768px-1199px (collapsed sidebar)
- Mobile: <768px (hamburger menu, stacked cards)

---

#### 4.1 CLI Command Registration

**File:** `bin/ai-toolkit.js` — add to `COMMANDS` and `SPECIAL_HANDLERS`:

```javascript
// COMMANDS
'ui': 'Launch local web dashboard for visual toolkit management',

// SPECIAL_HANDLERS
'ui': (args) => {
  const serverPath = path.join(TOOLKIT_DIR, 'app', 'dashboard', 'server.js');
  const child = require('child_process').spawn('node', [serverPath, ...args], {
    stdio: 'inherit',
    env: { ...process.env, TOOLKIT_DIR }
  });
  child.on('exit', (code) => process.exit(code || 0));
},
```

**Files to modify:**

| File | Action | Description |
|------|--------|-------------|
| `bin/ai-toolkit.js` | EDIT | Register `ui` command |
| `app/dashboard/server.js` | CREATE | HTTP server (main) |
| `app/dashboard/api.js` | CREATE | API handlers |
| `app/dashboard/assets.js` | CREATE | Embedded HTML/CSS/JS |
| `app/dashboard/frontmatter.js` | CREATE | JS frontmatter parser |
| `tests/test_dashboard.bats` | CREATE | Server lifecycle tests |
| `tests/test_dashboard_api.bats` | CREATE | API endpoint tests |

---

## 6. File Summary

| File | Action | LOC (est.) | Description |
|------|--------|------------|-------------|
| `app/dashboard/server.js` | CREATE | ~300 | HTTP server, lifecycle, routing |
| `app/dashboard/api.js` | CREATE | ~500 | All API endpoint handlers (10 read + 1 action, incl. extends + projects) |
| `app/dashboard/assets.js` | CREATE | ~3200 | Embedded HTML + CSS + JS for 10 pages. Split internally: `getOverviewHTML()`, `getAgentsHTML()`, `getExtendsHTML()`, `getProjectsHTML()`, etc. — one exported function per page. Single file, multiple functions (not multiple files — preserves single-`require` deployment). If file exceeds 3500 LOC, extract to `assets/` directory with `index.js` barrel |
| `app/dashboard/frontmatter.js` | CREATE | ~80 | Frontmatter parser (JS port) |
| `bin/ai-toolkit.js` | EDIT | +15 | Register `ui` command |
| `tests/test_dashboard.bats` | CREATE | ~100 | Server lifecycle tests |
| `tests/test_dashboard_api.bats` | CREATE | ~150 | API endpoint tests |
| **Total** | | **~4345** | |

---

## 7. Success Criteria (Overall)

| Metric | Target |
|--------|--------|
| Pages | 10 (overview, agents, skills, hooks, plugins, config, stats, mcp, extends, projects) |
| API endpoints | 11 (10 read + 1 action) |
| External dependencies | 0 (stdlib Node.js only) |
| Server startup time | < 500ms |
| Auto-kill | 30 min idle (configurable) |
| Responsive breakpoints | 3 (desktop, tablet, mobile) |
| Tests | 25+ |
| Browser support | Chrome, Firefox, Safari (modern, no IE) |

---

## 7a. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Server startup < 500ms. Page render < 200ms. API responses < 100ms. |
| **Memory** | Max RSS < 100MB (including embedded assets). No unbounded caching. |
| **Concurrency** | Max 1 concurrent action execution. Queue or reject additional requests with 429. |
| **Security** | Bind `127.0.0.1` only. CSP header: `default-src 'self' 'unsafe-inline'`. No CORS headers (same-origin only). Command allowlist enforced server-side. `execFile` with array args (no shell). |
| **Accessibility** | Keyboard navigation for all interactive elements. Focus management on page transitions. Minimum 4.5:1 contrast ratio (WCAG AA). ARIA labels on icon-only buttons. |
| **Error handling** | Missing/corrupt data files → graceful empty state with message. Server crash → exit code 1 with stderr diagnostic. API errors → JSON `{ "error": "..." }` with HTTP status. |
| **Graceful degradation** | If `stats.json` missing → stats page shows "No data yet". If `state.json` missing → overview shows defaults. If agent/skill .md unreadable → skip with warning in console. |

---

## 7b. Rollback & Feature Flag

The dashboard is purely additive — removing it is trivial:
1. Delete `app/dashboard/` directory
2. Remove `ui` from `COMMANDS` and `SPECIAL_HANDLERS` in `bin/ai-toolkit.js`
3. No config files, no state files, no hooks to clean up

**Disable without removal:** `ai-toolkit ui --disabled` could print "Dashboard disabled" and exit. Alternatively, skip registering the `ui` command in `bin/ai-toolkit.js` behind a `manifest.json` module flag so users can opt out via `--skip dashboard`.

---

## 7c. Testing Strategy

| Layer | Framework | Coverage |
|-------|-----------|----------|
| Server lifecycle (start, port discovery, auto-kill, shutdown) | bats | 5+ tests |
| API endpoints (all 8 read + action) | `node:test` (stdlib) | 15+ tests |
| SSE streaming (stdout/stderr/done events) | `node:test` | 3+ tests |
| Command allowlist enforcement | `node:test` | 5+ tests |
| Frontmatter parser edge cases | `node:test` | 5+ tests |
| Integration: full pipeline (start → API → action → stop) | `node:test` | 3+ tests |
| **Total** | | **36+** |

`node:test` is stdlib (Node 18+), zero dependencies. Bats tests are for CLI-level integration (process start/stop). JS tests cover API correctness.

---

## 7d. Discoverability

| Touchpoint | Action |
|------------|--------|
| `ai-toolkit install` output | Print banner: `Run 'ai-toolkit ui' to explore agents, skills, and plugins visually.` |
| `ai-toolkit help` | Include `ui` in command list |
| README.md | Screenshot/GIF of dashboard overview page |
| First-run detection | If `stats.json` is empty, show a "Try the dashboard" suggestion after `ai-toolkit install` |

---

## 8. Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Assets.js file too large (embedded HTML/CSS/JS) | Medium | Low | Split into multiple template modules, lazy-load pages |
| Port conflict on 3141 | Low | Low | Auto-increment port, show clear message |
| SSE not supported in old browsers | Low | Low | Fallback to polling for action results |
| Frontmatter parser edge cases | Low | Medium | Match exact patterns used in existing toolkit metadata |
| Config writes break installation | Low | High | All writes go through existing CLI commands — never direct file mutation |
| Stats.json missing or empty | Medium | Low | Graceful empty state with "No usage data yet" message |

---

## 9. Pre-Mortem

1. **"Too many features per page"** — Dashboard tries to show everything. Users may feel overwhelmed. Mitigation: progressive disclosure — overview page shows summary only, detail pages are opt-in.
2. **"Asset file becomes unmaintainable"** — ~2800 LOC of embedded HTML/CSS/JS is hard to iterate on. Mitigation: split into `assets/overview.js`, `assets/agents.js`, etc. with a build-free concatenation in server.js.
3. **"Nobody uses it"** — CLI users may prefer CLI. Mitigation: dashboard is opt-in, never required. Add `ai-toolkit ui` suggestion to `ai-toolkit install` output for new users.
4. **"Action execution feels disconnected"** — SSE console output may confuse users unfamiliar with CLI. Mitigation: rich UI feedback (progress bars, success/error toasts) layered on top of raw output.
5. **"Charts look bad without a library"** — Hand-drawn SVG charts may look amateur. Mitigation: keep charts simple (bar + heatmap), use consistent design tokens, test extensively.

---

## 10. Next Actions

1. [ ] Approve plan
2. [ ] Create `app/dashboard/server.js` with HTTP server + lifecycle (1.1)
3. [ ] Create API layer — read endpoints (1.2)
4. [ ] Create CSS design system + client routing (3.1, 3.2)
5. [ ] Build Overview page (2.1)
6. [ ] Build Agents page (2.2)
7. [ ] Build Skills page (2.3)
8. [ ] Add action execution API (1.3)
9. [ ] Build Hooks, Plugins, Config pages (2.4, 2.5, 2.6)
10. [ ] Build Stats page with SVG charts (2.7)
11. [ ] Build MCP page (2.8)
12. [ ] Register CLI command (4.1)
13. [ ] Tests — bats + node:test (4.2)
14. [ ] Documentation — all 9 docs per CLAUDE.md rules (4.3)

---

## 11. Future (Deferred)

| Feature | Reason for deferral | Prerequisite |
|---------|-------------------|--------------|
| Credentials page (2.9) | CLI has no `credentials` commands yet | cloud-security-pack CLI implementation |
| `ai-toolkit ui --static` | Generate a single standalone HTML file (no server) — covers 80% of catalog value at 20% complexity | Post-v1 evaluation of actual usage patterns |
| Guided onboarding flow | Interactive wizard for new users | Post-v1, based on user feedback |
| Light theme toggle | Dark-only for v1 | CSS variable architecture makes this easy later |

---

## 10. Market Positioning

**Target users:**
1. **New adopters** — developers evaluating ai-toolkit who want to understand what's included before committing to a profile
2. **Team leads** — visual overview of which agents, skills, and plugins are active across team setups
3. **Plugin explorers** — developers browsing available plugin packs without memorizing CLI commands
4. **Onboarding** — new team members getting oriented with the toolkit's capabilities

**Competitive advantage:** No existing AI coding toolkit provides a zero-dependency ephemeral web dashboard for visual management. Backstage is 1000x heavier (requires Kubernetes, PostgreSQL). TUI tools (mise, lazygit) lack visual richness. The ephemeral auto-kill design means zero operational burden.

**Discovery opportunity:** The dashboard serves as a self-documenting catalog — users discover agents and skills they didn't know existed, increasing toolkit utilization.

---

## 12. Cross-Plan Dependencies

This plan shares modification targets with two other proposed plans:

| Shared File | This Plan | Enterprise Config Plan | Offline SLM Plan |
|-------------|-----------|----------------------|-----------------|
| `bin/ai-toolkit.js` | +15 LOC (ui command) | +40 LOC (config subcommands) | +10 LOC (compile-slm command) |

**If Enterprise Config ships first:** Dashboard Config page (2.6) should display `.ai-toolkit.json` / `extends` status and `config diff` output. Add an API endpoint `GET /api/config/extends` reading resolved extends state from `state.json`.

**If Offline SLM ships first:** Dashboard Overview page (2.1) should display `offline-slm` profile status and link to compiled output. Stats page may show limited data (SLM providers don't emit hook-based stats).

---

**Last Updated:** 2026-04-10
