# Conventional Commit Template

```
<type>(<scope>): <description>

<body>

<footer>

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Types

| Type | When to use |
|------|-------------|
| `feat` | New feature for the user |
| `fix` | Bug fix for the user |
| `docs` | Documentation only changes |
| `style` | Formatting, missing semicolons, etc. |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Build process, auxiliary tools, libraries |
| `ci` | CI/CD configuration changes |
| `revert` | Reverts a previous commit |

## Scope examples

- `auth`, `api`, `db`, `ui`, `config`, `deps`, `docker`, `ci`

## Breaking changes

Add `!` after type/scope and `BREAKING CHANGE:` in footer:
```
feat(api)!: change authentication endpoint

BREAKING CHANGE: /auth/login now requires email instead of username
```

## Multi-line body

Use bullet points for multiple changes:
```
feat(search): add advanced filtering

- Add date range filter
- Add category filter with multi-select
- Add saved filters functionality

Closes #456
```
