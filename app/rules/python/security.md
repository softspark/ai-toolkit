---
language: python
category: security
version: "1.0.0"
---

# Python Security

## Input Validation
- Validate all input with Pydantic models at API boundaries.
- Use `constr`, `conint`, `conlist` for constrained types.
- Never use `eval()`, `exec()`, or `compile()` with user input.
- Never use `pickle.loads()` on untrusted data (arbitrary code execution).

## SQL Injection
- Use ORM query builders (SQLAlchemy, Django ORM) for all queries.
- For raw SQL, always use parameterized queries: `cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))`.
- Never use f-strings or `.format()` to build SQL queries.
- Use `text()` with `:param` syntax in SQLAlchemy raw queries.

## SSTI (Server-Side Template Injection)
- Use Jinja2 with autoescaping enabled: `Environment(autoescape=True)`.
- Never render user input as a template string.
- Use `markupsafe.Markup` only for trusted HTML content.

## Command Injection
- Never use `os.system()` or `subprocess.run(shell=True)` with user input.
- Use `subprocess.run()` with list arguments: `subprocess.run(["ls", "-la", path])`.
- Use `shlex.quote()` if shell=True is absolutely necessary.

## Path Traversal
- Use `pathlib.Path.resolve()` and verify the result is within allowed directory.
- Never concatenate user input into file paths without validation.
- Use `os.path.commonpath()` to verify path containment.

## Secrets
- Use `secrets` module for tokens: `secrets.token_urlsafe(32)`.
- Use `hashlib.scrypt` or `bcrypt` for password hashing.
- Use `hmac.compare_digest()` for constant-time secret comparison.
- Load secrets from environment: `os.environ["SECRET_KEY"]`, never hardcode.

## Dependencies
- Run `pip-audit` or `safety check` in CI.
- Use `uv` or `pip-compile` for reproducible dependency resolution.
- Avoid installing packages with native extensions from untrusted sources.
- Pin all dependency versions. Review dependency updates carefully.

## Deserialization
- Never deserialize untrusted data with `pickle`, `yaml.load()`, or `marshal`.
- Use `yaml.safe_load()` instead of `yaml.load()`.
- Use `json.loads()` for untrusted data (safe by default).
- Validate deserialized data with Pydantic before use.

## Django-Specific
- Set `DEBUG = False` in production. Never expose debug pages.
- Use `django.utils.html.escape()` for manual HTML escaping.
- Use `CSRF_COOKIE_HTTPONLY = True` and `SESSION_COOKIE_SECURE = True`.
- Keep `SECRET_KEY` unique per environment and out of version control.
