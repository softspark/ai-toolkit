---
description: Boost test coverage for a module or feature
---

# Test Coverage Workflow

1. Run coverage report to identify untested code
2. Prioritize: critical paths > edge cases > happy paths already covered
3. Write tests for uncovered public APIs first
4. Add edge case tests: null inputs, empty collections, boundary values
5. Add error path tests: invalid inputs, network failures, timeouts
6. Run coverage again — verify improvement
7. Do not write tests just for coverage numbers — each test should catch real bugs
