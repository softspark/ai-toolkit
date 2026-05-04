---
title: "Plan: Output & Token Discipline — Concise Modes, MCP Trim, Token Receipts"
category: planning
service: ai-toolkit
tags:
  - brand-voice
  - output-style
  - mcp
  - statusline
  - token-tracking
  - hooks
  - briefing
doc_type: plan
status: completed
created: "2026-05-04"
last_updated: "2026-05-04"
completed: "2026-05-04"
completion: "100% of v3.2.0 scope (F2 deferred to v4.0 per spike conclusion)"
shipped_in: "v3.2.0"
description: "Three coordinated extensions to ai-toolkit that reduce token usage and surface real cost data: (1) brand-voice output modes for concise/strict Claude responses, (2) MCP description trimmer to compact tool listings before they reach the model, (3) token receipts in statusline reading session JSONL directly. Native extensions, no third-party skill names imported."
---

# Plan: Output & Token Discipline

**Status:** Completed (shipped in v3.2.0 on 2026-05-04)
**Author:** lukasz.krzemien
**Source of inspiration:** external Claude Code plugin observed 2026-05-04 (mechanism only, not naming or branding)
**Spike companion:** [`kb/history/completed/f2-mcp-trim-spike-20260504.md`](f2-mcp-trim-spike-20260504.md)

## Cel

Zmniejszyć realne zużycie tokenów w sesjach Claude Code i dać użytkownikowi widoczność tego zużycia w czasie rzeczywistym. Trzy mechanizmy działające razem, każdy jako natywne rozszerzenie istniejących komponentów ai-toolkit (`brand-voice`, `briefing`, `track-usage.sh`). Bez importowania obcych nazw — adaptacja idei jako własnych.

## Kontekst

Obecnie ai-toolkit ma:

- `brand-voice` skill — pilnuje stylu pisanego (docs, README, content)
- `track-usage.sh` hook — liczy `/skill` invocations do `~/.softspark/ai-toolkit/stats.json`
- `compile_slm.py` — kompresuje cały toolkit dla małych modeli (inny scope)
- 113 skilli, pełen system hooków, doctor, eject

Brakuje:

- Trybu zwięzłego dla *odpowiedzi* Claude'a (brand-voice działa tylko dla pisanej zawartości)
- Kompresji opisów MCP-tooli, które zżerają setki tokenów na każdym wywołaniu
- Realnego pomiaru tokenów per sesja (mamy tylko licznik invocations, nie tokenów)

## Zakres

Trzy features, zaplanowane w kolejności narastającego ryzyka.

---

## Feature 1 — `brand-voice` output modes

### Cel
Rozszerzyć `brand-voice` o tryby zwięzłości stosowane do odpowiedzi konwersacyjnych Claude'a, nie tylko do generowanych dokumentów.

### Decyzje nazewnicze
- **Wybrane:** zostaje `brand-voice` z wewnętrznymi trybami (`default`, `concise`, `strict`)
- **Odrzucone:**
  - `concise` jako osobny skill — duplikuje brand-voice, niepotrzebny rozłam
  - `terse` — niejednoznaczne, kojarzy się z "rude"
  - `output-discipline` — zbyt biurokratyczne

### Pliki

| Ścieżka | Akcja | Cel |
|---------|-------|-----|
| `app/skills/brand-voice/SKILL.md` | edit | Dodaj sekcję `## Output Modes` z opisem trzech trybów i sposobu aktywacji |
| `app/skills/brand-voice/modes/concise.md` | new | Reguły: max 3 zdania per odpowiedź na pytanie zamknięte, brak preamble, brak "I'll now..." |
| `app/skills/brand-voice/modes/strict.md` | new | Reguły: tylko fakty, zero filler adjectives, max 1 zdanie per fakt, listy zamiast prozy |
| `app/skills/brand-voice/scripts/measure.py` | new | Eval przed/po na fixtures, raport oszczędności tokenów |
| `tests/fixtures/output-modes/` | new | 10 par baseline/expected dla różnych typów zadań (debug, review, plan, eksploracja) |
| `tests/skills_brand_voice.bats` | edit | Dodaj asercje dla modes (regex na zakazane filler, max-line-length) |

### Aktywacja

Trzy mechanizmy:

1. Frontmatter w projekcie: `output-mode: concise` w `CLAUDE.md` lub `.claude/settings.json`
2. Slash: `/brand-voice concise` przełącza dla bieżącej sesji (przez `track-usage.sh` zapisuje do session state)
3. Auto-trigger: skill ładuje się także przy długich sesjach generowania (>30 min, heurystyka)

### Success criteria

- Na zestawie 10 fixtures `concise` redukuje output >40% bez utraty kluczowych faktów
- Test asercji: zachowane są wszystkie nazwy plików i symboli z baseline (regex match)
- `validate.py --strict` przechodzi
- `audit_skills.py --ci` zero HIGH

### Estymata
4–6h

---

## Feature 2 — MCP context trim — DEFERRED TO v4.0

**Status:** Deferred. Spike conducted before implementation, conclusion in [`f2-mcp-trim-spike-20260504.md`](f2-mcp-trim-spike-20260504.md).

**Reason:** Claude Code hooks do not expose the MCP `tools/list` response or the system-prompt tool catalog. Hook events (`PreToolUse`, `PermissionRequest`, `Elicitation`) operate on individual tool calls only. Modifying tool descriptions before they reach the model requires a local MCP proxy server — multi-day scope, single-bug-breaks-all-MCP failure mode, out of scope for v3.2.0.

**Resolution:** Full proxy-server approach moved to its own active planning doc: [`kb/planning/mcp-context-trim-v4-prd.md`](../../planning/mcp-context-trim-v4-prd.md). The mid-spike "F2-lite observability tool" alternative was also dropped per user decision (2026-05-04) — v3.2.0 ships F1+F3 only; v4.0 picks up the proxy-server work in full scope.

The compression heuristics, file plan, and risk register from the original Feature 2 design were migrated into the v4.0 PRD. They are no longer duplicated in this archived doc.

---

## Feature 3 — Token receipts w statusline

### Cel
Pokazać realne (nie estymowane) zużycie tokenów per-sesja w statusline Claude Code. Dane czytane z session JSONL, nie z heurystyk.

### Decyzje nazewnicze
- **Wybrane:** rozszerzenie istniejącego skilla `briefing` + nowy hook `statusline-tokens.sh` + nowy skrypt `session_token_stats.py`
- **Odrzucone:**
  - Nowy skill `stats` / `receipts` — duplikuje funkcjonalnie `briefing`
  - Modyfikacja istniejącego `track-usage.sh` jako jedynego punktu — za duża odpowiedzialność jednego pliku

### Pliki

| Ścieżka | Akcja | Cel |
|---------|-------|-----|
| `scripts/session_token_stats.py` | new | Parser JSONL stdlib-only. Funkcje: `read_session()`, `aggregate_by_skill()`, `compare_baseline_vs_concise()` |
| `app/hooks/statusline-tokens.sh` | new | Type `statusLine` w settings.json. Sumuje `usage.input_tokens` + `usage.output_tokens` z bieżącej sesji JSONL |
| `app/hooks/track-usage.sh` | edit | Po wykryciu `/skill` zapisuj też `prompt_tokens` jeśli `transcript_path` dostępne |
| `app/skills/briefing/SKILL.md` | edit | Nowa sekcja "Token receipts", komendy `/briefing --tokens --since 7d`, `/briefing --tokens --share` |
| `scripts/merge-hooks.py` | edit | Statusline injection do `settings.json`, preserve user-customized entries (delivered as F3.5) |
| `app/hooks/ai-toolkit-statusline.sh` | new | Comprehensive statusline (cwd + git + ctx + tokens + cost + model), default install (delivered as F3.5) |
| `tests/session_token_stats.bats` | new | Fixture JSONL z 3 messages, asercje na sumę i breakdown |
| `tests/statusline_tokens.bats` | new | Mock JSONL, weryfikacja outputu hooka (max 80 znaków, brak NaN, fallback gdy brak sesji) |

### Format statusline (proponowany)

```
[ai-toolkit] /concise · session: 24.7k · trend: ↓18%
```

Krótki tryb default, `--verbose` dodaje breakdown per skill.

### Ścieżka odczytu sesji

Claude Code zapisuje JSONL do `~/.claude/projects/<sanitized-cwd>/<session-id>.jsonl`. Każda linia to message z polem `usage` (input_tokens, output_tokens, cache_*). Skrypt:

1. Identyfikuje aktualną sesję z env var `CLAUDE_SESSION_ID` (jeśli istnieje) lub najświeższy plik
2. Parsuje linie ignorując te bez `usage`
3. Sumuje + agreguje per skill (jeśli `track-usage.sh` zapisał skill mapping w sidecar pliku)

### Success criteria

- Statusline pokazuje liczbę tokenów odczytaną z JSONL z dokładnością ±2% vs Anthropic API report (jeśli dostępny)
- Brak crash gdy sesja jeszcze pusta
- Brak crash gdy JSONL malformed
- `validate.py --strict` przechodzi

### Estymata
6–8h

---

## Co nie wchodzi w plan

| Pomysł | Powód odrzucenia |
|--------|------------------|
| Memory/file compressor (`/compress <file>`) | `compile_slm.py` już kompresuje toolkit, brak konkretnego use-case dla per-file |
| Compact `/commit`, `/review` modes | Powstaną automatycznie po Feature 1 (te skille będą używać reguł `concise` mode) |
| "Caveman speak" / classical Chinese mode | Nie pasuje do tonu workmanlike, sprzeczne z brand-voice |
| Single curl-installer | Już mamy `ai-toolkit install` z profilami |

---

## Kolejność realizacji i zależności

```
Feature 1 (brand-voice modes)
    ↓ dostarcza reguły zwięzłości
Feature 3 (token receipts)
    ↓ dostarcza pomiar before/after dla F1
Feature 2 (mcp-trim)  ← spike research najpierw, niezależne od F1/F3
```

**F1 i F3 mogą iść parallel po dokończeniu F1 mode files.**
**F2 ma osobną decyzję go/no-go po spike'u.**

## Estymata zbiorcza

| Feature | Min | Max |
|---------|-----|-----|
| F1 | 4h | 6h |
| F3 | 6h | 8h |
| F2 spike | 1h | 1h |
| F2 implementacja | 0h | 10h |
| **Total** | **11h** | **25h** |

## Doc & test sweep (obowiązkowy po każdym feature)

1. `python3 scripts/validate.py --strict`
2. `python3 scripts/audit_skills.py --ci`
3. Regen `AGENTS.md`: `python3 scripts/generate_agents_md.py > AGENTS.md`
4. Regen `llms.txt`: `python3 scripts/generate_llms_txt.py > llms.txt`
5. Bump version w `package.json` + `plugin.json`
6. Update `skills-catalog.md` z nowymi/zmienionymi skillami
7. Update `README.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `architecture-overview.md` jeśli zmiana behavior
8. Commit conventional: `feat(brand-voice): add output modes`, `feat(briefing): add token receipts`, `feat(mcp-trim): add description trimmer`

## Open questions — resolved

1. **Czy `PreToolUse` może modyfikować deklarację tool'a w MCP listingu?** — NIE. Spike potwierdził że żaden hook event nie wystawia `tools/list`. F2 wymaga MCP proxy. Odsunięte do v4.0.
2. **Czy Claude Code wystawia hookom `CLAUDE_SESSION_ID`?** — częściowo. `scripts/session_token_stats.py` używa fallback "newest JSONL w katalogu projektu" + opcjonalnie cwd → sanitize → match. Działa stabilnie na realnych sesjach (96.6k tokens parsed correctly w smoke tescie).
3. **Czy włączyć `concise` mode jako default?** — pozostaje opt-in. `brand-voice` z trybami auto-loaduje się tylko gdy projekt ustawi `output-mode: concise` w `CLAUDE.md` lub user wpisze `/brand-voice concise`. Pomiary z F3 dadzą dane do późniejszej decyzji.

## Final delivery (v3.2.0)

### Shipped

| Feature | Outcome | Pliki |
|---------|---------|-------|
| **F1 — brand-voice output modes** | Done. Aggregate ratio na 3 fixtures: concise **21%**, strict **14%** (cel ≤60% / ≤40%). | `app/skills/brand-voice/SKILL.md`, `app/skills/brand-voice/modes/{concise,strict}.md`, `app/skills/brand-voice/scripts/measure.py`, `tests/fixtures/output-modes/{debug-explanation,plan-question,review-summary}/`, `tests/test_brand_voice.bats` (14 tests) |
| **F3 — token receipts** | Done. Smoke-test na realnej sesji: 96.6k tokenów poprawnie sparsowane. | `scripts/session_token_stats.py`, `tests/fixtures/session-jsonl/{three-messages,malformed,empty}.jsonl`, `tests/test_session_token_stats.bats` (15 tests) |
| **F3.5 — comprehensive default statusline** | Done. Pełny segment: cwd + git + ctx% + tokens + trend + model-aware cost + model. Installed by default via `merge-hooks.py`, user-custom statusLine preserved untouched. | `app/hooks/ai-toolkit-statusline.sh`, `app/hooks.json` (`statusLine` entry), `scripts/merge-hooks.py` (statusLine inject/strip), `tests/test_statusline_hook.bats` (14 tests), `tests/test_merge_hooks_statusline.bats` (8 tests) |
| **briefing skill extension** | `/briefing --tokens` + wire-up docs + opt-out env vars. | `app/skills/briefing/SKILL.md` |

### Deviations from plan

| Plan said | Shipped | Reason |
|-----------|---------|--------|
| 10 fixtures w F1 | 3 fixtures + `must_contain.txt` mechanism | Mniejszy zestaw + extensible konwencja wystarcza do walidacji budżetów; jakość > ilość |
| F3 hook integracja jako follow-up (manual settings.json edit) | F3.5 dostarczył pełny default install via `merge-hooks.py` | User feedback w trakcie pracy: "niech ai-toolki instaluje go domyslnie od nowej wersji" |
| F2 implementacja po spike'u | F2 deferred do v4.0 | Spike pokazał że Claude Code hooki nie wystawiają `tools/list` → wymaga proxy server, multi-day scope |

### Quality gates passed

- `validate.py --strict`: 0 errors / 0 warnings
- `audit_skills.py --ci`: 0 HIGH / 0 WARN / 13 INFO (pre-existing)
- `audit_skills.py --sarif`: SARIF 2.1.0 valid, 5 rules
- `npm test`: 1032 / 1032 passing (was 981 in v3.1.1)
- Registry drift: clean
- Provenance + checksum-pin: verified
- Ecosystem doctor: 9 cosmetic drifts (class A) refreshed

### Skill classification change

`brand-voice` przeszedł `user-invocable: false → true` (knowledge → hybrid):

- **Hybrid**: 31 → 32
- **Knowledge**: 49 → 48
- **Task**: 32 (no change)

Updated: `README.md`, `kb/reference/architecture-overview.md`, `kb/reference/skills-catalog.md`.

## Status & rewizje

| Data | Zmiana | Autor |
|------|--------|-------|
| 2026-05-04 | Initial draft | lukasz.krzemien |
| 2026-05-04 | F1 implementation done — brand-voice modes, measure.py, 3 fixtures, 14 bats tests. Aggregate ratio: concise 21%, strict 14%. | claude |
| 2026-05-04 | F3 implementation done — `session_token_stats.py`, `statusline-tokens.sh`, briefing skill extension. 22 new bats tests. Smoke-tested on real session. | claude |
| 2026-05-04 | F3.5 follow-up done — replaced focused tokens hook with comprehensive `ai-toolkit-statusline.sh`. Extended `merge-hooks.py` for safe statusLine injection. Version bumped 3.1.1 → 3.2.0. 22 new bats tests. CHANGELOG + README updated. | claude |
| 2026-05-04 | F2 spike completed — see [`f2-mcp-trim-spike-20260504.md`](f2-mcp-trim-spike-20260504.md). Hooks cannot modify `tools/list`. F2 deferred to v4.0 with own PRD. | claude |
| 2026-05-04 | Plan archived to `kb/history/completed/`. Shipped in v3.2.0. | claude |
