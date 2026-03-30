# Input Validation

## Validation Rules
```python
from pydantic import BaseModel, EmailStr, constr

class UserInput(BaseModel):
    email: EmailStr
    username: constr(min_length=3, max_length=20, pattern=r'^[a-zA-Z0-9_]+$')
    age: int = Field(ge=0, le=150)
```

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
