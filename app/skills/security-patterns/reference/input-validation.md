# Input Validation

## Validation Rules
```python
from pydantic import BaseModel, EmailStr, Field, constr

class UserInput(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    age: int = Field(ge=0, le=150)
```

## Validation contract gotchas

These traps came from repeated corrections during a DTO-to-client validation
rollout. Apply them when a client mirrors server rules; they do not require a
new generator for every small form.

- **Two validators can still be two conflicting policies.** Derive portable
  client checks from the server's authoritative schema or resolved metadata.
  A shared schema is also valid when the backend actually enforces it. Bind
  field feedback and serialized-payload preflight to that same contract.
  Backend enforcement remains mandatory, including when client code is bypassed.
- **The entity may never be validated.** Trace the operation's real input object.
  In API Platform, an input DTO can be validated before mapping to an entity.
  Validation groups select constraints; denormalization groups select writable
  fields. Output-only constraints add no protection to the request path.
- **PATCH does not make every property optional.** An update hydrated from
  existing state and a newly constructed input DTO have different missing-field
  semantics. Preserve actual defaults and distinguish omitted keys, null and
  empty values. Resolve this per operation, not from the HTTP method alone.
- **A constraint name is not a finite bound.** Length(min), Count(min),
  All(Email) and an unbounded regex do not cap input size. Check actual maximum
  values, collection size, item shape/type and nested validation separately.
  In Symfony, retain All/Collection/Valid and sequential evaluation semantics.
  Bound body size and violation output too; stop expensive item validation
  after an oversized list is refused.
- **A field name does not identify its storage or wire format.** Read the
  mapper/processor and owning storage before choosing limits. An Id field can
  accept an IRI; a timestamp ceiling does not validate a real date. Feature
  limits and established domain error codes can be stricter or more specific
  than a generic ceiling. Do not replace them accidentally in a bulk pass.
- **Unicode length has several units.** Specify bytes, code units, codepoints
  or grapheme clusters and the normalization order. Test decomposed accents,
  non-BMP characters, joined emoji and IME composition. A client must not
  silently truncate a value the server accepts; preserve input when showing an
  error. Do not normalize passwords or apply identifier alphabet rules to
  names without a documented product policy.
- **Rule names hide runtime options.** Email modes, URL schemes, numeric
  coercion, regex dialects and conditional validation can differ across
  languages. Export supported options explicitly. Conditional rules are
  audited data, never arbitrary server expressions evaluated in the client.
- **Some checks depend on server state or libraries.** Keep authorization,
  availability, uniqueness and domain invariants on the server. If a portable
  equivalent is unavailable, record the exact operation/field/rule and reason
  in reviewed policy. Newly unsupported rules must surface as a failed
  generation/check step, not become an always-valid adapter. Bodyless routes
  and exclusions are separate measurements, not evidence of client coverage.
- **A local refusal is not an HTTP response.** Use a distinct local error type,
  preserve field paths and rule codes, and show localized field feedback.
  Do not invent an HTTP status or trigger token refresh/network retry for a
  request that was never sent. Server refusals remain authoritative; keep
  local/server error state distinguishable and test correction/resubmission.
- **Generation proves synchronization, not semantic equivalence.** Run shared
  accepted/rejected fixtures through the real backend validator and client
  evaluator, including both conditional branches and nested error paths.
  Check deterministic generation and reviewed exclusions in CI. A snapshot
  of the exporter tested against itself does not prove parity. HTTP tests
  must also exercise deserialization and rejected-write persistence behavior.

Input validation does not replace parameterized queries or context-appropriate
output encoding. The backend may still reject a client-valid request because
state changed after local validation.

For regression selection, use the "Validation contract regressions" section
of the installed `testing-patterns` skill. For HTTP failure semantics, read
`reference/error-contracts.md` from the installed `api-patterns` skill.
Locate these skills through the current client's catalog because adapters may
namespace their directory names.

## SQL Injection Prevention
```python
# Bad
query = f"SELECT * FROM users WHERE email = '{email}'"

# Good (parameterized)
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

## XSS Prevention
```python
# Escape HTML
from markupsafe import escape
safe_text = escape(user_input)

# Content Security Policy
response.headers['Content-Security-Policy'] = "default-src 'self'"
```
