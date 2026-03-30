# OAuth2, CSRF Protection & Audit Logging

## OAuth2 Flows

### Authorization Code Flow (FastAPI)
```python
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

config = Config('.env')
oauth = OAuth(config)

oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    client_kwargs={'scope': 'openid email profile'},
)

@app.get('/login')
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/callback')
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = token.get('userinfo')
    return {"email": user_info['email']}
```

---

## CSRF Protection

```python
from fastapi import FastAPI, Request, Depends
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = "your-secret-key-min-32-chars-long!"
    cookie_samesite: str = "lax"
    cookie_secure: bool = True

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

@app.get("/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    token = csrf_protect.generate_csrf()
    return {"csrf_token": token}

@app.post("/protected")
async def protected_route(request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    return {"status": "ok"}
```

### CSRF Best Practices
| Technique | Implementation |
|-----------|---------------|
| SameSite Cookie | `cookie_samesite: "strict"` or `"lax"` |
| Double Submit | Token in cookie + header |
| Origin Validation | Check `Origin`/`Referer` headers |
| Secure Flag | `cookie_secure: True` in production |

---

## Audit Logging

```python
import structlog
from enum import Enum
from datetime import datetime
from typing import Any

logger = structlog.get_logger()

class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"

def audit_log(
    action: AuditAction,
    user_id: str,
    resource: str,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None
) -> None:
    logger.info(
        "audit_event",
        action=action.value,
        user_id=user_id,
        resource=resource,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        timestamp=datetime.utcnow().isoformat()
    )

# Usage in FastAPI
@app.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request, current_user: User = Depends()):
    audit_log(
        action=AuditAction.DELETE,
        user_id=current_user.id,
        resource="users",
        resource_id=user_id,
        ip_address=request.client.host
    )
    # ... delete logic
```

### Audit Log Requirements
| Event | Must Log |
|-------|----------|
| Authentication | Login, logout, failed attempts |
| Authorization | Access denied, permission changes |
| Data Changes | Create, update, delete with before/after |
| Admin Actions | User management, config changes |
| Security Events | Password reset, MFA changes |
