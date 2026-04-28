---
name: ruby-rules
description: "Ruby coding rules from ai-toolkit: coding-style, frameworks, patterns, security, testing. Triggers: .rb, Gemfile, .gemspec, Rails, ActiveRecord, Sidekiq, RSpec, Sorbet, rubocop. Load when writing, reviewing, or editing Ruby code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Ruby Rules

These rules come from `app/rules/ruby/` in ai-toolkit. They cover
the project's standards for coding style, frameworks, patterns,
security, and testing in Ruby. Apply them when writing or
reviewing Ruby code.

# Ruby Coding Style

## Naming
- PascalCase: classes, modules.
- snake_case: methods, variables, file names, directories.
- UPPER_SNAKE: constants (`MAX_RETRIES = 3`).
- Prefix boolean methods with predicate: `empty?`, `valid?`, `admin?`.
- Suffix dangerous methods with `!`: `save!`, `sort!`, `strip!`.
- Use `_` prefix for intentionally unused variables: `_unused`.

## Methods
- Keep methods short: 5-10 lines ideal. Extract helper methods.
- Use keyword arguments for methods with >2 parameters.
- Use default parameter values instead of checking for nil.
- Use `def method_name = expression` (Ruby 3.0+) for one-liners.
- Prefer `each` over `for` loops. Use block-style iteration.
- Return values implicitly (last expression). Use explicit `return` only for early exit.

## Blocks, Procs, Lambdas
- Use `{ }` for single-line blocks. Use `do...end` for multi-line blocks.
- Use `&:method` shorthand: `names.map(&:upcase)`.
- Use lambdas for strict argument checking. Use procs for flexible arity.
- Use `yield` for single-block methods. Use explicit `&block` for storing/forwarding.

## Classes
- Use `attr_reader`, `attr_writer`, `attr_accessor` for simple getters/setters.
- Use `Struct` for simple data containers. Use `Data.define` (Ruby 3.2+) for immutable.
- Use modules for mixins: `include` for instance methods, `extend` for class methods.
- Use `frozen_string_literal: true` magic comment at the top of every file.
- Use `private` / `protected` keywords to control method visibility.

## Collections
- Use `map`, `select`, `reject`, `reduce`, `flat_map` for transformations.
- Use `each_with_object` over `inject` when accumulating into a mutable object.
- Use `dig` for safe nested hash/array access: `data.dig(:user, :address, :city)`.
- Use `Hash#fetch` with default for explicit missing-key handling.
- Use `Enumerable#lazy` for large collection processing.

## Pattern Matching (Ruby 3+)
- Use `case/in` for structural pattern matching on hashes and arrays.
- Use `=>` pin operator to match against existing variables.
- Use `in` pattern for conditional deconstruction in `if` statements.
- Use pattern matching for API response parsing and validation.

## Formatting
- Use RuboCop for automated style enforcement.
- Use `.rubocop.yml` committed to the repository for project conventions.
- Max line length: 120 characters.
- Two-space indentation. No tabs.
- Use trailing commas in multi-line arrays and hashes.

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

# Ruby Patterns

## Error Handling
- Rescue specific exceptions. Never bare `rescue` (catches `StandardError`).
- Create domain exception hierarchies: `class AppError < StandardError; end`.
- Use `raise` with message and optional cause: `raise AppError, "msg"`.
- Use `retry` with a counter for transient failures.
- Use `ensure` for cleanup. Use `else` for code that runs only on success.

## Service Objects
- Use single-purpose service classes with a `call` method.
- Use `Dry::Monads` Result type for operation outcomes.
- Return `Success(value)` or `Failure(error)` from service calls.
- Chain services with `bind` / `fmap` for pipeline composition.
- Keep services stateless. Pass all data through method parameters.

## Value Objects
- Use `Data.define` (Ruby 3.2+) for immutable value objects.
- Use `Struct` with `keyword_init: true` for lightweight data containers.
- Use `freeze` on objects that should not be mutated after creation.
- Override `==` and `hash` for value-based equality when needed.

## Metaprogramming (Use Sparingly)
- Use `define_method` over `method_missing` when possible.
- Always define `respond_to_missing?` alongside `method_missing`.
- Use `class_attribute` (Rails) for inheritable class-level configuration.
- Prefer explicit code over DSL magic for maintainability.
- Document metaprogrammed methods with YARD `@!method` directives.

## Concurrency
- Use `Concurrent::Future` (concurrent-ruby) for parallel operations.
- Use `Concurrent::Promise` for composable async chains.
- Use thread pools (`Concurrent::FixedThreadPool`) for bounded concurrency.
- Use `Ractor` (Ruby 3+) for true parallel execution without GVL.
- Use `Mutex` and `Queue` for thread-safe shared state access.

## Module Patterns
- Use `include` for shared behavior (instance methods).
- Use `prepend` for wrapping/overriding existing methods (decorating).
- Use `extend` for adding class-level methods from a module.
- Use `Concern` (ActiveSupport) for Rails modules with class methods.
- Keep modules focused: one responsibility per module.

## Decorator Pattern
- Use `SimpleDelegator` for transparent object wrapping.
- Use `Draper` gem for view-layer decorators in Rails.
- Prefer composition (wrapping) over inheritance for adding behavior.
- Use `Module#prepend` for method-level decoration without wrapper classes.

## Anti-Patterns
- Monkey-patching core classes: use refinements or wrapper methods.
- Callbacks for business logic (Rails): use service objects.
- God objects: split into focused classes with single responsibility.
- N+1 queries: use `includes()`, `preload()`, `eager_load()`.
- Using `eval` or `send` with user input: remote code execution risk.

# Ruby Security

## Mass Assignment
- Use strong parameters in controllers: `params.require(:user).permit(:name, :email)`.
- Never use `params.permit!` or pass unsanitized params to `create`/`update`.
- Use `attr_readonly` for fields that should never be updated after creation.
- Audit `update_columns` and `update_attribute` usage (bypass validations).

## SQL Injection
- Use ActiveRecord query interface with parameterized conditions.
- Use `where(name: value)` hash syntax or `where("name = ?", value)` placeholders.
- Never interpolate user input into `where()` strings: `where("name = '#{input}'")`.
- Use `sanitize_sql_array` if building raw SQL fragments is unavoidable.
- Audit all `find_by_sql`, `execute`, and `Arel.sql` calls.

## XSS Prevention
- Rails auto-escapes ERB output with `<%= %>`. Never use `raw()` with user data.
- Use `sanitize()` helper for allowing limited HTML tags.
- Set `Content-Security-Policy` header in `config/initializers/content_security_policy.rb`.
- Use `content_tag` helper for safe HTML generation.
- Mark strings as `html_safe` only when content is guaranteed safe.

## CSRF Protection
- Use `protect_from_forgery with: :exception` in `ApplicationController`.
- Use `authenticity_token` in all forms (Rails includes it by default).
- Use `X-CSRF-Token` header for AJAX requests from JavaScript.
- Exempt only webhook endpoints from CSRF (with payload signature verification).

## Authentication
- Use Devise or `has_secure_password` for authentication.
- Use `bcrypt` for password hashing (included with `has_secure_password`).
- Implement account lockout after N failed login attempts.
- Use `SecureRandom.urlsafe_base64` for generating tokens.
- Store sessions server-side (Redis/database) instead of cookie store in production.

## Authorization
- Use Pundit or CanCanCan for authorization logic.
- Define policies per model: `class UserPolicy < ApplicationPolicy`.
- Check ownership in policies, not just role membership.
- Use `authorize @resource` in every controller action.
- Default deny: require explicit authorization for all actions.

## Secrets Management
- Use `Rails.application.credentials` for encrypted secrets.
- Use `EDITOR="vim" bin/rails credentials:edit` to manage secrets.
- Use per-environment credentials: `credentials/production.yml.enc`.
- Never commit `master.key` or `production.key` to version control.
- Use environment variables for CI/CD and containerized deployments.

## Dependency Security
- Run `bundle audit check --update` for known vulnerability scanning.
- Use `Dependabot` for automated dependency update PRs.
- Pin gem versions in `Gemfile`. Review `Gemfile.lock` changes carefully.
- Use `bundler-audit` in CI pipeline as a required check.
- Update Rails promptly when security patches are released.

# Ruby Testing

## Framework
- Use RSpec as the primary test framework.
- Use Minitest for lightweight, stdlib-based testing.
- Use FactoryBot for test data generation.
- Use WebMock or VCR for HTTP request stubbing.

## File Naming
- RSpec: `spec/models/user_spec.rb` mirroring `app/models/user.rb`.
- Minitest: `test/models/user_test.rb` mirroring source structure.
- Support files: `spec/support/` for shared helpers and configurations.
- Use `spec/rails_helper.rb` for Rails-specific RSpec configuration.

## Structure (RSpec)
- Use `describe` for the class/method under test. Use `context` for scenarios.
- Use `it` for individual test cases with clear descriptions.
- Use `let` for lazy-evaluated test data. Use `let!` for eager evaluation.
- Use `before` / `after` blocks for setup and teardown.
- Use `subject` for the primary object under test.

## Matchers (RSpec)
- Use `expect(result).to eq(expected)` for equality.
- Use `expect(result).to be_truthy`, `be_falsy`, `be_nil`.
- Use `expect { action }.to raise_error(FooError)` for exception testing.
- Use `expect { action }.to change { User.count }.by(1)` for side effects.
- Use `expect(list).to include(item)`, `contain_exactly(a, b, c)`.
- Use `expect(result).to match(hash_including(key: value))` for partial matching.

## Mocking (RSpec)
- Use `instance_double(UserService)` for verified doubles.
- Stub: `allow(mock).to receive(:find).with(1).and_return(user)`.
- Verify: `expect(mock).to have_received(:save).once`.
- Use `receive_messages(method1: val1, method2: val2)` for multi-stubbing.
- Use `class_double` for stubbing class methods.
- Avoid stubbing the object under test. Stub only collaborators.

## FactoryBot
- Define factories in `spec/factories/`: `FactoryBot.define { factory :user { ... } }`.
- Use `create` for persisted records. Use `build` for in-memory only.
- Use traits for variations: `create(:user, :admin)`.
- Use `build_stubbed` for fast tests that do not need database.
- Use sequences for unique attributes: `sequence(:email) { |n| "user#{n}@test.com" }`.

## Rails Testing
- Use `request specs` for API endpoint testing (RSpec).
- Use `system specs` with Capybara for browser integration tests.
- Use `DatabaseCleaner` or `use_transactional_fixtures` for test isolation.
- Use `travel_to` for time-dependent test scenarios.
- Use `ActiveJob::TestHelper` for testing background jobs inline.

## Best Practices
- Test behavior, not implementation. Do not test private methods directly.
- Use `shared_examples` for testing common behavior across classes.
- Use `aggregate_failures` to collect multiple assertion failures.
- Keep tests fast: stub external services, use `build_stubbed`.
- Run `bundle exec rspec --format documentation` for readable output.
