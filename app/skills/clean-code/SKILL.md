---
name: clean-code
description: "Code quality principles: meaningful names, single responsibility, DRY, small functions, clear intent, guard clauses, refactoring rules. Triggers: clean code, naming, refactor for clarity, code smell, SRP, DRY, long function, god class, magic number, dead code. Load when reviewing or writing any production code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Clean Code Skill

## Core Principles

### 1. Meaningful Names

```python
# Bad
def calc(a, b):
    return a * b

# Good
def calculate_total_price(unit_price: float, quantity: int) -> float:
    return unit_price * quantity
```

### 2. Single Responsibility

```python
# Bad - does too much
def process_user(user_data):
    validate(user_data)
    user = create_user(user_data)
    send_welcome_email(user)
    log_creation(user)
    return user

# Good - each function does one thing
def create_user(user_data: UserData) -> User:
    return User(**user_data)

def onboard_user(user_data: UserData) -> User:
    user = create_user(user_data)
    send_welcome_email(user)
    log_user_creation(user)
    return user
```

### 3. DRY (Don't Repeat Yourself)

```python
# Bad
def get_active_users():
    return [u for u in users if u.status == "active"]

def get_active_admins():
    return [u for u in users if u.status == "active" and u.role == "admin"]

# Good
def filter_users(status: str | None = None, role: str | None = None) -> list[User]:
    result = users
    if status:
        result = [u for u in result if u.status == status]
    if role:
        result = [u for u in result if u.role == role]
    return result
```

---

## Code Organization

Keep modules focused. Order contents consistently: imports (stdlib, third-party, local), constants, public API, private helpers. Use clear visibility markers (underscore prefix in Python, access modifiers in other languages). Group related functionality into cohesive modules rather than dumping everything into a single file.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| God class | Too many responsibilities | Split into smaller classes |
| Long methods | Hard to understand | Extract methods |
| Deep nesting | Complex control flow | Early returns, extract methods |
| Magic numbers | Unclear meaning | Use named constants |
| Bare except | Hides bugs | Catch specific exceptions |
| Mutable defaults | Shared state bugs | Use `None` and create inside |

---

## Quality Checklist

- [ ] Functions are small (<20 lines ideal)
- [ ] Names are descriptive and consistent
- [ ] Type hints on all public APIs
- [ ] Docstrings on all public functions/classes
- [ ] No magic numbers (use constants)
- [ ] No hardcoded strings (use enums/constants)
- [ ] Error handling is specific
- [ ] Resources are properly cleaned up
- [ ] No code duplication
- [ ] Tests cover critical paths

---

## Common Rationalizations

| Excuse | Why It's Wrong |
|--------|----------------|
| "It's readable enough" | "Enough" means someone will misread it eventually — clarity prevents incidents |
| "Refactoring for readability is gold-plating" | Readability is maintainability — future you will thank present you |
| "Short variable names are faster to type" | You type it once, readers parse it hundreds of times — optimize for reading |
| "DRY means never repeat anything" | Wrong DRY creates coupling — duplicate until you see the real abstraction |
| "More abstractions = cleaner code" | Premature abstraction is worse than duplication — wait for the third use |

## Language-Specific References

For detailed patterns, type hints, linting configuration, and idiomatic code per language:

- **Python:** type hints, docstrings, error handling, context managers, module/class structure, ruff/mypy config -- see [reference/python.md](reference/python.md)
- **TypeScript:** strict tsconfig, ESLint setup, discriminated unions, type safety -- see [reference/typescript.md](reference/typescript.md)
- **PHP:** PHPStan config, PSR-12, enums, constructor promotion -- see [reference/php.md](reference/php.md)
- **Go:** gofmt, error handling, receiver naming, early returns -- see [reference/go.md](reference/go.md)
- **Dart/Flutter:** null safety, named parameters, const constructors, dart analyze -- see [reference/dart.md](reference/dart.md)
