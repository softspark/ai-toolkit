# Authorization Patterns

## RBAC (Role-Based)
```python
ROLES = {
    "admin": ["read", "write", "delete", "admin"],
    "editor": ["read", "write"],
    "viewer": ["read"]
}

def check_permission(user, action):
    return action in ROLES.get(user.role, [])
```

## ABAC (Attribute-Based)
```python
def can_access(user, resource):
    return (
        user.department == resource.department
        and user.clearance >= resource.classification
    )
```
