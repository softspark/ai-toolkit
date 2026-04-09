# Security

* Never commit secrets, API keys, credentials, or tokens — use environment variables
* Validate and sanitize all external input (user input, API responses, file uploads)
* Use parameterized queries — never concatenate SQL strings
* Escape output to prevent XSS in web contexts
* Apply principle of least privilege for file permissions and API scopes
* Keep dependencies updated — audit regularly for known CVEs
* Use HTTPS for all external communication
* Log security events without logging sensitive data (passwords, tokens, PII)
