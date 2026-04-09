---
description: Generate or update documentation for code changes
---

# Documentation Workflow

1. Identify what changed: new feature, API change, config change, bug fix
2. Update inline code comments only where logic is non-obvious
3. Update README if setup, usage, or prerequisites changed
4. Update API docs if endpoints, params, or responses changed
5. Add examples for new features
6. Remove documentation for deleted features — no stale docs
7. Run any doc generation tools (typedoc, sphinx, etc.)
