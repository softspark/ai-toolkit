---
language: php
category: testing
version: "1.0.0"
---

# PHP Testing

## Framework
- Use PHPUnit 10+ as the primary test framework.
- Use Pest PHP for expressive, minimal-boilerplate testing (built on PHPUnit).
- Use Mockery for flexible mocking. Use PHPUnit built-in mocks for simple cases.
- Use Testcontainers (via Docker) for integration tests with databases.

## File Naming
- Test files: `FooTest.php` in `tests/` mirroring `src/` namespace structure.
- Unit tests: `tests/Unit/`. Integration tests: `tests/Integration/` or `tests/Feature/`.
- PHPUnit config: `phpunit.xml.dist` at project root.
- Use `@group` annotations for test categorization.

## Structure (PHPUnit)
- Use `#[Test]` attribute (PHP 8) or `test` prefix for test methods.
- Use `setUp()` / `tearDown()` for per-test initialization and cleanup.
- Use `#[DataProvider('dataMethodName')]` for parameterized tests.
- Name tests: `testMethodName_Scenario_ExpectedResult` or descriptive snake_case.

## Structure (Pest)
- Use `test('description', function () { ... })` for test cases.
- Use `it('should do something', ...)` for BDD-style descriptions.
- Use `beforeEach()` / `afterEach()` for setup and teardown.
- Use `dataset()` for shared test data across multiple tests.
- Use `->with([...])` for inline parameterized tests.

## Assertions
- Use `$this->assertSame()` for strict equality (type + value).
- Use `$this->assertInstanceOf(Foo::class, $result)` for type checks.
- Use `$this->expectException(FooException::class)` before the throwing call.
- Use `$this->assertCount()`, `$this->assertContains()` for collections.
- Pest: use `expect($value)->toBe()`, `->toBeInstanceOf()`, `->toThrow()`.

## Mocking (Mockery)
- Create mocks: `$mock = Mockery::mock(UserRepository::class)`.
- Stub: `$mock->shouldReceive('find')->with(1)->andReturn($user)`.
- Verify: `$mock->shouldHaveReceived('save')->once()`.
- Use `Mockery::close()` in `tearDown()` or `afterEach()`.
- Use `spy()` to verify interactions without stubbing.

## Laravel Testing
- Use `RefreshDatabase` trait for database test isolation.
- Use `$this->actingAs($user)` for authenticated request testing.
- Use `$this->getJson('/api/users')->assertOk()->assertJsonCount(3)`.
- Use factories: `User::factory()->create()` for test data.
- Use `Bus::fake()`, `Event::fake()`, `Mail::fake()` for side-effect assertion.

## Best Practices
- Test behavior, not implementation. Do not test private methods.
- Use in-memory SQLite for fast database tests when schema is compatible.
- Run `php artisan test --parallel` for faster Laravel test execution.
- Use `--coverage-html` for visual coverage reports.
- Keep tests fast: mock external HTTP calls with `Http::fake()`.
