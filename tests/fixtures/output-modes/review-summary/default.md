I took a look at `src/auth/login.ts` line 42 for you. Let me walk you through what I found and what I think about it.

On line 42, the code does a user lookup by calling `db.query("SELECT * FROM users WHERE email = '" + email + "'")`. Unfortunately, this is a classic SQL injection vulnerability. The user-provided email is being concatenated directly into the SQL string, which means an attacker could potentially submit something like `' OR '1'='1` as the email and bypass the authentication check entirely. This is one of the most well-known security issues, and it's listed in OWASP Top 10 as A03:2021 — Injection.

To fix this, you should use a parameterized query instead. Most database drivers support this natively. For example, with `pg` for PostgreSQL, you'd write something like `db.query("SELECT * FROM users WHERE email = $1", [email])`. The driver handles the escaping for you, and even better, the query plan can be cached.

I'd recommend treating this as a high-priority fix. Let me know if you'd like me to make the change for you, or if you have any questions about the approach!
