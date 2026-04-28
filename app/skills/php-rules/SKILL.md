---
name: php-rules
description: "PHP coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .php, composer.json, Laravel, Symfony, PHPUnit, PSR-12, Composer. Load when writing, reviewing, or editing PHP code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# PHP Rules

These rules come from `app/rules/php/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in PHP. Apply them when writing or
reviewing PHP code.

# PHP Coding Style

## Standards
- Follow PSR-12 extended coding style.
- Use `declare(strict_types=1)` at the top of every file.
- Use PHP 8.1+ features: enums, fibers, readonly properties, intersection types.
- Use PHP CS Fixer or Pint for automated formatting.

## Naming
- PascalCase: classes, interfaces, traits, enums.
- camelCase: methods, functions, variables.
- UPPER_SNAKE: class constants (`public const MAX_RETRIES = 3`).
- snake_case: not used for methods. PSR convention is camelCase.
- Suffix interfaces with `Interface` or prefix with contract name (project convention).

## Type System
- Use typed properties: `private readonly string $name;`.
- Use union types: `string|int`. Use intersection types: `Countable&Iterator`.
- Use `enum` (PHP 8.1) for fixed sets of values. Use backed enums for persistence.
- Use `readonly` classes (PHP 8.2) for immutable DTOs.
- Use constructor promotion: `public function __construct(private string $name)`.
- Use `never` return type for functions that throw or exit.

## Functions
- Use typed parameters and return types on all functions/methods.
- Use named arguments for readability: `new User(name: 'Ada', age: 36)`.
- Use null-safe operator: `$user?->address?->city`.
- Use match expression over switch for value mapping.
- Use first-class callable syntax: `array_map($this->transform(...), $items)`.

## Imports and Namespaces
- Use PSR-4 autoloading via Composer.
- Group `use` statements: classes, functions, constants.
- Never use `require`/`include` for class loading. Use Composer autoloader.
- Use one class per file. File name matches class name.

## Error Handling
- Use exceptions for error conditions. Never return error codes.
- Create domain exception hierarchies extending `RuntimeException` or `LogicException`.
- Use `match` with `throw` for exhaustive error mapping.
- Log exceptions with context using PSR-3 logger.

## Configuration
- Use PHPStan at level 8+ for static analysis.
- Use Rector for automated code upgrades and refactoring.
- Use `.php-cs-fixer.dist.php` for formatting rules.
- Run `composer analyse` (PHPStan) and `composer format` (Pint) in CI.

# PHP Frameworks

## Laravel
- Use route model binding: `Route::get('/users/{user}', ...)`.
- Use Form Requests for validation: `class StoreUserRequest extends FormRequest`.
- Use Eloquent scopes for reusable query constraints: `scopeActive()`.
- Use API Resources for response transformation: `UserResource::collection($users)`.
- Use `config()` helper for configuration. Never access `env()` outside config files.
- Use middleware groups for auth, throttling, and CORS.

## Eloquent ORM
- Use relationships: `hasMany`, `belongsTo`, `belongsToMany`, `morphMany`.
- Use eager loading: `User::with('posts.comments')->get()` to prevent N+1.
- Use `$fillable` or `$guarded` on models. Prefer `$fillable` (explicit whitelist).
- Use model events or observers for lifecycle hooks.
- Use `upsert()` for bulk insert-or-update operations.
- Use `cursor()` for memory-efficient iteration over large result sets.

## Symfony
- Use attributes for route definitions: `#[Route('/api/users', methods: ['GET'])]`.
- Use autowiring for dependency injection. Register services in `services.yaml`.
- Use Symfony Forms for complex validation and data mapping.
- Use Messenger component for async message handling (commands, events).
- Use Doctrine ORM with repository pattern and query builders.

## Doctrine ORM
- Use entity classes with annotations or attributes for mapping.
- Use repositories for data access: `$em->getRepository(User::class)`.
- Use DQL for type-safe queries. Use QueryBuilder for dynamic queries.
- Use migrations: `bin/console doctrine:migrations:diff` and `migrate`.
- Use lifecycle callbacks (`@PrePersist`, `@PostUpdate`) for entity events.

## Symfony Serializer
- Default behavior uses property names as-is. Combined with PSR-12 `camelCase` property names, JSON output is `camelCase` with zero configuration.
- Avoid adding `api_platform.name_converter: CamelCaseToSnakeCaseNameConverter` globally. Known side-effect ([api-platform/core #6101](https://github.com/api-platform/core/issues/6101)): overrides the project-wide `MetadataAwareNameConverter`, affecting Messenger serializers, custom normalizers, and CLI JSON output — not just the HTTP API.
- Use `#[SerializedName]` only when justified: legacy field alias during rename, external contract mapping, ObjectNormalizer cross-version stabilization. Community practice ([Symfony docs](https://symfony.com/doc/current/serializer.html), Sylius, SymfonyCasts): prefer clean property/getter naming over aliases. When using, document the reason next to the attribute.
- Symfony 7.3.5+ `ObjectNormalizer` produces `isActive` natively for a `isActive(): bool` getter ([symfony/symfony #62353](https://github.com/symfony/symfony/issues/62353)). Older `#[SerializedName('isActive')]` aliases added for pre-7.3.5 `ObjectNormalizer` (which produced `active`) are redundant after upgrade — remove them.
- Avoid duplicate getters like `isActive()` + `getIsActive()` on the same property — `ObjectNormalizer` treats them as two fields and serializes ambiguously. Keep one (`isXxx()` for booleans, `getXxx()` otherwise).

## API Platform
- Use API Platform for rapid REST/GraphQL API generation from entities.
- Use `#[ApiResource]` attribute for automatic CRUD endpoint generation.
- Use custom state providers and processors for business logic.
- Use serialization groups for controlling response shape.
- Use filters for query parameter support: pagination, search, ordering.
- Property names on `ApiResource` DTOs drive JSON keys directly (see Symfony Serializer above). Write them in `camelCase` — that is both the Symfony default and the dominant JSON API convention.
- Use `operation_name` in `extraProperties` for dispatch metadata (e.g., `extraProperties: ['operation_name' => 'club_activate']`). The key `operation_name` and its `snake_case` values are framework metadata, not JSON wire keys — keeping them `snake_case` is expected.

## Livewire (Laravel)
- Use Livewire components for reactive UI without JavaScript.
- Use `wire:model` for two-way data binding on form inputs.
- Use `$rules` property for inline validation on component properties.
- Use component actions for server-side event handling.
- Use `wire:loading` for loading state indicators.

## Queues and Workers
- Use Laravel Horizon for Redis queue monitoring and management.
- Use Symfony Messenger with transports (Redis, AMQP, Doctrine).
- Use dead letter queues for failed job inspection and replay.
- Use rate limiting on queue workers to prevent downstream overload.

# PHP Patterns

## Error Handling
- Use custom exception hierarchies: `class DomainException extends RuntimeException`.
- Add context to exceptions: `throw new UserNotFoundException(userId: $id)`.
- Use `match` with `default => throw` for exhaustive error mapping.
- Use `set_exception_handler()` for global uncaught exception handling.
- Log exceptions with PSR-3 logger and structured context.

## Enums and Value Objects
- Use backed enums for database-persisted values: `enum Status: string`.
- Use `from()` for strict conversion, `tryFrom()` for nullable safe conversion.
- Implement methods on enums for behavior: `public function label(): string`.
- Use readonly classes for value objects: `readonly class Money { ... }`.
- Use constructor promotion for concise value object definitions.

## Repository Pattern
- Abstract data access behind repository interfaces.
- Repositories return domain entities, not Eloquent models or arrays.
- Use constructor injection for repository dependencies.
- Use specifications or criteria objects for complex query building.
- Keep repository methods focused: one query per method.

## Service Layer
- Use service classes for business logic. Keep controllers thin.
- Use action classes (single-method services) for discrete operations.
- Use DTOs for data transfer between layers. Never pass request objects to services.
- Use command/query separation: commands mutate, queries read.
- Inject dependencies via constructor. Never use `app()` helper in services.

## Collections and Iterators
- Use Laravel Collections or standalone `illuminate/collections` for data manipulation.
- Chain `map()`, `filter()`, `reduce()` for declarative data transformation.
- Use `LazyCollection` for memory-efficient processing of large datasets.
- Use generators (`yield`) for lazy iteration over large result sets.
- Prefer `collect()` pipeline over nested loops.

## Async Patterns
- Use Laravel Queues for background job processing.
- Use `dispatch()` for fire-and-forget. Use `Bus::chain()` for sequential jobs.
- Use `ShouldQueue` interface on jobs, listeners, and mailables.
- Set `$tries`, `$timeout`, `$backoff` on job classes.
- Use `batch()` for parallel job execution with completion callback.

## Event-Driven
- Use events and listeners for decoupled side effects.
- Use domain events for cross-boundary communication.
- Use `ShouldQueue` on listeners for async event handling.
- Use event subscribers for grouping related listeners.
- Keep event payloads minimal: IDs and timestamps, not full objects.

## Anti-Patterns
- Fat controllers: move logic to services/actions.
- God models: split into focused models with traits or separate classes.
- Using `DB::raw()` without parameterization: SQL injection risk.
- Static method calls for testable dependencies: use DI instead.
- Returning mixed types: use typed returns or Result objects.

# PHP Security

## SQL Injection
- Use PDO prepared statements with bound parameters for all queries.
- Use Eloquent/Doctrine ORM for type-safe query building.
- Never concatenate user input into SQL strings. Never use `DB::raw($input)`.
- Use `whereIn()` with arrays, not string interpolation for IN clauses.
- Audit raw queries: `DB::select(DB::raw(...))` must use `?` placeholders.

## XSS Prevention
- Blade templates auto-escape with `{{ }}`. Never use `{!! !!}` with user data.
- Use `htmlspecialchars()` with `ENT_QUOTES` when outputting outside Blade.
- Set `Content-Security-Policy` headers to restrict inline scripts.
- Sanitize rich-text input with HTMLPurifier before storage.
- Use `strip_tags()` only as a secondary measure, not primary defense.

## CSRF Protection
- Use `@csrf` directive in all Blade forms.
- Use `VerifyCsrfToken` middleware (enabled by default in Laravel).
- Use `X-CSRF-TOKEN` header for AJAX requests from SPA frontends.
- Exclude only webhook endpoints from CSRF verification (with careful validation).

## Authentication
- Use `password_hash()` with `PASSWORD_ARGON2ID` or `PASSWORD_BCRYPT`.
- Use Laravel Sanctum for SPA/mobile API authentication.
- Use Laravel Passport for full OAuth2 server implementation.
- Implement rate limiting on login endpoints: `ThrottleRequests` middleware.
- Use multi-factor authentication for admin accounts.

## Authorization
- Use Laravel Gates and Policies for authorization logic.
- Use `$this->authorize('update', $post)` in controllers.
- Check resource ownership in policies, not just role membership.
- Default deny: use `Gate::before()` for super-admin bypass, nothing else.
- Use middleware `can:permission` for route-level authorization.

## File Upload
- Validate file MIME type server-side. Do not trust `Content-Type` header.
- Store uploads outside the web root. Use `storage/` with `Storage::disk()`.
- Generate random filenames. Never use original user-provided filenames.
- Set maximum file size limits in validation and PHP `upload_max_filesize`.
- Scan uploaded files for malware in production environments.

## Mass Assignment
- Use `$fillable` on Eloquent models. Never use `$guarded = []`.
- Use Form Requests to whitelist fields before model assignment.
- Use DTOs for data transfer. Never pass `$request->all()` to `create()`.
- Audit `forceFill()` and `forceCreate()` usage (bypasses guarding).

## Secrets and Configuration
- Use `.env` files for local secrets. Use Vault or SSM for production.
- Never commit `.env` to version control. Commit `.env.example` as template.
- Use `config()` helper, never `env()` outside of config files (caching issue).
- Never log request content containing passwords or tokens.
- Use `APP_DEBUG=false` in production. Debug mode leaks sensitive data.

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
