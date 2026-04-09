---
description: Design and implement a new API endpoint
---

# API Design Workflow

1. Define the resource and its relationships
2. Choose HTTP methods (GET/POST/PUT/PATCH/DELETE) following REST conventions
3. Define request/response schemas with types
4. Plan error responses (400, 401, 403, 404, 422, 500)
5. Implement validation for all input fields
6. Write integration tests covering happy path and error cases
7. Add rate limiting and authentication if needed
8. Document the endpoint (OpenAPI/Swagger or inline docs)
9. Test with real HTTP client (curl, httpie, Postman)
