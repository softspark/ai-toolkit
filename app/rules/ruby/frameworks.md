---
language: ruby
category: frameworks
version: "1.0.0"
---

# Ruby Frameworks

## Rails (General)
- Follow Rails conventions: convention over configuration.
- Use `rails generate` for scaffolding models, controllers, migrations.
- Use strong parameters: `params.require(:user).permit(:name, :email)`.
- Use concerns for shared controller/model behavior.
- Use `config/routes.rb` with resourceful routing: `resources :users`.
- Use environment-specific configuration in `config/environments/`.

## ActiveRecord
- Use migrations for all schema changes. Never modify the database directly.
- Use `has_many`, `belongs_to`, `has_many :through` for associations.
- Use scopes for reusable query chains: `scope :active, -> { where(active: true) }`.
- Use `includes()` for eager loading to prevent N+1 queries.
- Use `find_each` for batch processing large record sets.
- Use `transaction` blocks for atomic multi-record operations.

## ActionController
- Keep controllers thin: max 7 RESTful actions per controller.
- Use `before_action` for authentication and authorization checks.
- Use `respond_to` for content negotiation (JSON, HTML).
- Use `rescue_from` for centralized error handling in controllers.
- Use `render json:` with serializers (e.g., `ActiveModelSerializers`, `Blueprinter`).

## Background Jobs
- Use Sidekiq for Redis-backed background job processing.
- Use ActiveJob as the abstraction layer over queue backends.
- Use `perform_later` for async execution. Use `perform_now` only in tests.
- Set `retry` count and `discard_on` / `retry_on` for error handling.
- Use `Sidekiq::Cron` or `clockwork` for scheduled recurring jobs.

## Sinatra / Hanami
- Use Sinatra for lightweight APIs and microservices.
- Use Hanami for structured, modular Ruby web applications.
- Use Hanami actions (single-purpose) instead of fat controllers.
- Use Hanami repositories for data access abstraction.

## API Mode
- Use `rails new --api` for API-only applications (no views, sessions).
- Use `Jbuilder` or `Blueprinter` for JSON serialization.
- Use `Rack::Attack` for rate limiting and throttling.
- Use versioned API namespaces: `namespace :v1 do ... end`.
- Use pagination with `kaminari` or `pagy` for collection endpoints.

## Hotwire / Turbo
- Use Turbo Frames for partial page updates without JavaScript.
- Use Turbo Streams for real-time server-pushed DOM updates.
- Use Stimulus for lightweight JavaScript behavior on HTML elements.
- Keep JavaScript minimal: let the server render HTML.
