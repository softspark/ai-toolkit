# Visual Companion

Browser-based companion for showing mockups, diagrams, and layouts during PRD brainstorming sessions.

## What

A lightweight Node.js HTTP server that serves a dark-themed HTML page in the user's browser. The agent pushes HTML content to the page via a POST endpoint, enabling real-time display of mockups, wireframes, comparison tables, and diagrams alongside the terminal conversation.

## When to Offer

Anticipate visual questions during the PRD interview. Offer the companion when upcoming questions will involve:

- UI mockups or wireframes
- Layout comparisons (side-by-side options)
- Architecture diagrams
- Data flow visualizations
- Feature comparison tables with visual elements

## Consent Flow

1. **Offer once, as its own message.** Do not combine with other questions.
2. **Wait for the user's response** before proceeding.
3. **Respect a "no"** — continue the interview entirely in the terminal.

Example offer:

> "Some of what we're working on might be easier to explain visually. I can show mockups and diagrams in a browser. Want to try it?"

## Per-Question Decision

After the companion is accepted, decide per question:

| Content Type | Where |
|---|---|
| Mockups, wireframes, layouts | Browser |
| Architecture diagrams | Browser |
| Comparison tables (visual) | Browser |
| Conceptual questions | Terminal |
| Text-only decisions | Terminal |
| Yes/no confirmations | Terminal |

## How to Start

```bash
node scripts/visual-server.cjs
```

The server prints the URL to stdout:

```
Visual companion ready at http://localhost:PORT
```

Share this URL with the user so they can open it in their browser.

## How to Update Content

POST HTML to the `/update` endpoint:

```bash
curl -X POST http://localhost:PORT/update \
  -H "Content-Type: application/json" \
  -d '{"html": "<h2>Mockup A</h2><p>Description here...</p>"}'
```

The browser page polls `/content` every 2 seconds and updates automatically with a brief fade transition.

## Auto-Shutdown

The server automatically shuts down after 30 minutes of inactivity (no HTTP requests). It also responds to SIGINT and SIGTERM for graceful shutdown.

## Technical Details

- **Dependencies:** None. Uses Node.js built-in `http`, `fs`, `path` modules only.
- **Port:** Binds to a random available port (falls back to 38888 on error).
- **Template:** Served from `frame-template.html` in the same directory.
- **Content endpoint:** GET `/content` returns `{"html": "..."}` for polling.
- **Update endpoint:** POST `/update` accepts `{"html": "..."}` to change displayed content.
