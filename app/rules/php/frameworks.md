---
language: php
category: frameworks
version: "1.0.0"
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

## API Platform
- Use API Platform for rapid REST/GraphQL API generation from entities.
- Use `#[ApiResource]` attribute for automatic CRUD endpoint generation.
- Use custom state providers and processors for business logic.
- Use serialization groups for controlling response shape.
- Use filters for query parameter support: pagination, search, ordering.

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
