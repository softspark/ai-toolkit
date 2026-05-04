`src/auth/login.ts:42` — SQL injection. String-concatenates `email` into query.

Fix: parameterized query. With `pg`:

```ts
db.query("SELECT * FROM users WHERE email = $1", [email])
```

OWASP A03:2021. High priority.
