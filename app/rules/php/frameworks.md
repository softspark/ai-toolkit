---
language: php
category: frameworks
version: "1.1.0"
---

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
