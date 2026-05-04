`src/auth/login.ts:42` — SQL injection. OWASP A03:2021. High.

Fix:
```ts
db.query("SELECT * FROM users WHERE email = $1", [email])
```
