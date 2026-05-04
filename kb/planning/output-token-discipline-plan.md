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
completion: "100% of v3.2.0 scope (F2 deferred to v4.0 per spike conclusion)"
description: "Three coordinated extensions to ai-toolkit that reduce token usage and surface real cost data: (1) brand-voice output modes for concise/strict Claude responses, (2) MCP description trimmer to compact tool listings before they reach the model, (3) token receipts in statusline reading session JSONL directly. Native extensions, no third-party skill names imported."
---

# Plan: Output & Token Discipline

**Status:** Proposed
**Author:** lukasz.krzemien
**Source of inspiration:** external Claude Code plugin observed 2026-05-04 (mechanism only, not naming or branding)

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

**Status:** Deferred. See `kb/planning/f2-mcp-trim-spike-conclusion.md` for the spike result.

**Reason:** Claude Code's hook system does not expose `tools/list` metadata to hooks; only individual tool calls and inputs. Modifying MCP tool descriptions before they reach the model requires either a local MCP proxy server (multi-day scope, high blast radius) or source-side forks of MCP servers (high maintenance). Both are out of scope for v3.2.0.

The full proxy approach is parked for v4.0 with its own dedicated PRD and architecture spike.



### Cel
Pre-tool-use hook który skraca opisy MCP-tooli zanim trafią do modelu. Zachowuje URL-e, identifiers, parametry funkcji.

### Decyzje nazewnicze
- **Wybrane:** nowy skill `mcp-trim` (knowledge-only, dokumentuje użycie) + skrypt `scripts/mcp_description_trimmer.py` + opt-in hook `app/hooks/mcp-trim.sh`
- **Odrzucone:**
  - Rozszerzenie `mcp-builder` — buduje serwery, nie modyfikuje runtime, niepasujący scope
  - Rozszerzenie `mcp-patterns` — to skill wiedzy, nie wykonawczy
  - Standalone MCP proxy serwer — za duże blast-radius na pierwszą iterację

### Pliki

| Ścieżka | Akcja | Cel |
|---------|-------|-----|
| `scripts/mcp_description_trimmer.py` | new | Stdin: JSON z mcp tool list; stdout: skompresowany JSON. Stdlib-only. |
| `app/skills/mcp-trim/SKILL.md` | new | Knowledge skill: kiedy używać, ostrzeżenia, jak wyłączyć dla konkretnego serwera |
| `app/hooks/mcp-trim.sh` | new | Opt-in hook (typu PreToolUse jeśli wykonalne — patrz spike) |
| `tests/mcp_trimmer.bats` | new | Fixtures z jira/filesystem/dart-mcp listings, asercje na zachowanie inputSchema |

### Heurystyki kompresji

- Usuń przykłady z `description` >40 znaków
- Skróć `Use this server to...` do najkrótszej formy zachowującej cel
- Usuń duplikat nazwy tool'a w opisie
- **Zachowaj bezwzględnie:** `inputSchema.properties[*].description` (typy), `required`, `enum` values, identyfikatory URL/path
- Cel: redukcja >40% długości opisu, 0% utraty parametrów

### Spike przed implementacją (1h)

- Sprawdzić czy Claude Code's `PreToolUse` hook może modyfikować deklarację tool'a, czy tylko payload wywołania
- Jeśli tylko payload → wymagany MCP proxy server, dokończenie odsuwane do v2
- Wynik spike'u: ADR/decision note w `kb/decisions/`

### Profil instalacji

- NIE w `default` ani `standard`
- Tylko `--with-mcp-trim` flag lub `--profile strict`
- Ostrzeżenie w README: "może odebrać Claude'owi sygnał kiedy NIE używać tool'a"

### Ryzyka (devil's advocate)

1. **Skompresowanie usuwa sygnał discriminacji** — opis "Use this server only for X, never for Y" po skróceniu może stracić "never for Y". Mitigacja: heurystyka NIE usuwa `not`, `never`, `only`, `except`, `unless`.
2. **Brak Claude Code API do modyfikacji tool list** — wymaga MCP proxy. Spike rozstrzygnie.
3. **Niespodziewana regresja w innych projektach** — opt-in z dokładnym dokumentem migracji.

### Success criteria

- Opisy MCP w fixtures zredukowane >40%
- Deep-equal `inputSchema` z baseline po stripie pól description (zero zmiany w schematach)
- `tests/mcp_trimmer.bats` pass

### Estymata
1h spike + 6–10h implementacji (jeśli spike pozytywny) lub 0h (jeśli spike pokaże wymóg proxy server, scope odsuwany)

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
| `scripts/install.py` lub hook injector | edit | Rejestracja `statusLine` w settings.json template (opt-in) |
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

## Open questions

1. Czy `PreToolUse` hook może modyfikować deklarację tool'a w MCP listingu? (rozstrzyga F2 spike)
2. Czy Claude Code wystawia hookom `CLAUDE_SESSION_ID` env var? Jeśli nie — heurystyka "newest JSONL" w kursorze.
3. Czy włączyć `concise` mode jako default po F1, czy zostawić opt-in? Decyzja po pomiarach z F3 (dane > opinia).

## Status & rewizje

| Data | Zmiana | Autor |
|------|--------|-------|
| 2026-05-04 | Initial draft | lukasz.krzemien |
| 2026-05-04 | F1 implementation done — brand-voice modes (concise/strict), measure.py, 3 fixtures, 14 bats tests passing. Aggregate ratio: concise 21%, strict 14% on shipped fixtures (well under 60%/40% targets). | claude |
| 2026-05-04 | F3 implementation done — `scripts/session_token_stats.py` (stdlib JSONL parser), `app/hooks/statusline-tokens.sh`, briefing skill extended with `--tokens` and statusline wire-up docs. 22 new bats tests passing. Smoke-tested on real Claude Code session: 96.6k tokens correctly parsed. Installer integration deferred to follow-up — manual settings.json edit documented in briefing skill. | claude |
| 2026-05-04 | F3.5 follow-up done — replaced focused tokens-only hook with comprehensive `app/hooks/ai-toolkit-statusline.sh` combining cwd, git, ctx%, tokens, trend, model-aware cost, model name. Extended `merge-hooks.py` to inject `statusLine` into settings.json by default while preserving user-customized entries (no `_source: ai-toolkit` tag). Added `app/hooks.json` `statusLine` entry. Bumped version 3.1.1 → 3.2.0. Added 22 new bats tests (statusline + merge-hooks). CHANGELOG, README "What's New", briefing skill all updated. | claude |
