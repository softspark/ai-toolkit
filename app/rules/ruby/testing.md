---
language: ruby
category: testing
version: "1.0.0"
---

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
