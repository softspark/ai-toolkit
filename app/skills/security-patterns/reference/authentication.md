# Authentication Patterns

## JWT Structure
```
Header.Payload.Signature

{
  "alg": "HS256",
  "typ": "JWT"
}
.
{
  "sub": "user_id",
  "exp": 1234567890,
  "iat": 1234567800
}
.
[signature]
```

## Token Strategy
| Token Type | Storage | Lifetime |
|------------|---------|----------|
| Access Token | Memory | 15 min |
| Refresh Token | HttpOnly Cookie | 7 days |
| API Key | Secure storage | Long-lived |

## Password Hashing
```python
# Python (bcrypt)
import bcrypt
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(12))

# Node.js (argon2)
import argon2 from 'argon2';
const hash = await argon2.hash(password);
```
