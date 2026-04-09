---
description: Multi-vector security assessment of codebase
---

# Security Audit Workflow

1. Scan dependencies for known CVEs (npm audit, pip audit, etc.)
2. Check for hardcoded secrets, API keys, and credentials
3. Review authentication and authorization logic
4. Test input validation — look for SQL injection, XSS, SSTI
5. Check file upload handling and path traversal risks
6. Review error handling — ensure no sensitive data in error messages
7. Verify HTTPS usage for all external communication
8. Check access control — principle of least privilege
9. Document findings with severity (HIGH/MEDIUM/LOW)
10. Create issues for each finding with fix recommendations
