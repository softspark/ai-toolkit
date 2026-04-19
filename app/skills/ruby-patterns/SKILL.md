---
name: ruby-patterns
description: "Ruby and Rails development patterns: blocks, metaprogramming, ActiveRecord, Sidekiq, RSpec, Sorbet/RBS, Hanami, Roda, Rack middleware. Triggers: Ruby, Rails, ActiveRecord, Sidekiq, RSpec, gem, Gemfile, bundler, rake, Hanami, Sorbet. Load when writing or reviewing Ruby code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Ruby Patterns

## Project Structure

### Gem Layout
```
my_gem/
├── lib/
│   ├── my_gem.rb              # Entry point, require sub-files
│   └── my_gem/
│       ├── version.rb
│       ├── configuration.rb
│       ├── client.rb
│       └── errors.rb
├── spec/
│   ├── spec_helper.rb
│   ├── my_gem/
│   │   └── client_spec.rb
│   └── fixtures/
├── bin/
│   └── console              # IRB with gem loaded
├── sig/                     # RBS type signatures
├── Gemfile
├── Rakefile
├── my_gem.gemspec
├── .rubocop.yml
└── .ruby-version
```

### Rails Standard Structure
```
app/
├── controllers/
│   ├── application_controller.rb
│   └── api/v1/
│       └── users_controller.rb
├── models/
│   ├── application_record.rb
│   ├── user.rb
│   └── concerns/
│       └── searchable.rb
├── services/
│   └── users/
│       ├── create_service.rb
│       └── import_service.rb
├── jobs/
│   └── user_sync_job.rb
├── mailers/
├── serializers/
│   └── user_serializer.rb
└── views/
config/
├── routes.rb
├── database.yml
├── initializers/
│   ├── sidekiq.rb
│   └── cors.rb
└── environments/
db/
├── migrate/
├── schema.rb
└── seeds.rb
spec/
├── rails_helper.rb
├── spec_helper.rb
├── models/
├── requests/
├── services/
├── factories/
│   └── users.rb
└── support/
    └── shared_examples/
```

### Gemfile Best Practices
```ruby
source "https://rubygems.org"

ruby "~> 3.3"

gem "rails", "~> 7.2"
gem "pg"
gem "puma", ">= 6.0"
gem "sidekiq", "~> 7.0"
gem "redis", ">= 5.0"

group :development, :test do
  gem "rspec-rails"
  gem "factory_bot_rails"
  gem "faker"
  gem "debug"
  gem "rubocop-rails", require: false
  gem "rubocop-rspec", require: false
end

group :test do
  gem "shoulda-matchers"
  gem "webmock"
  gem "vcr"
  gem "simplecov", require: false
end
```

---

## Idioms / Code Style

### Blocks, Procs, and Lambdas
```ruby
# Block -- yielded to, not stored
def with_retry(attempts: 3)
  attempts.times do |i|
    return yield
  rescue StandardError => e
    raise if i == attempts - 1
    sleep(2**i)
  end
end

with_retry { http_client.get("/data") }

# Proc -- flexible arity, returns from enclosing method
validator = Proc.new { |val| val.to_s.strip.length > 0 }

# Lambda -- strict arity, returns from itself
transform = ->(x) { x.to_s.downcase.strip }
words = ["Hello ", " WORLD"].map(&transform)

# Method reference
names = users.map(&:name)
valid = values.select(&method(:valid?))
```

### Modules and Mixins
```ruby
# Concern pattern (Rails)
module Searchable
  extend ActiveSupport::Concern

  included do
    scope :search, ->(query) {
      where("name ILIKE ?", "%#{sanitize_sql_like(query)}%")
    }
  end

  class_methods do
    def searchable_columns
      %i[name email]
    end
  end
end

# Pure Ruby mixin
module Loggable
  def logger
    @logger ||= Logger.new($stdout, progname: self.class.name)
  end

  def log_info(msg) = logger.info(msg)
  def log_error(msg) = logger.error(msg)
end
```

### method_missing with respond_to_missing?
```ruby
class Config
  def initialize(data = {})
    @data = data
  end

  def method_missing(name, *args)
    key = name.to_s.chomp("=").to_sym
    if name.to_s.end_with?("=")
      @data[key] = args.first
    elsif @data.key?(key)
      @data[key]
    else
      super
    end
  end

  def respond_to_missing?(name, include_private = false)
    @data.key?(name.to_s.chomp("=").to_sym) || super
  end
end
```

### Frozen String Literals
```ruby
# frozen_string_literal: true

# Add to every file. Prevents accidental mutation, improves memory.
# Enforce via RuboCop: Style/FrozenStringLiteralComment
```

### Pattern Matching (Ruby 3+)
```ruby
case response
in { status: 200, body: { data: Array => items } }
  process_items(items)
in { status: 200, body: { data: Hash => item } }
  process_item(item)
in { status: 404 }
  raise NotFoundError
in { status: (500..) }
  raise ServerError, response[:body]
end

# Find pattern
case users
in [*, { role: "admin", name: String => admin_name }, *]
  puts "Found admin: #{admin_name}"
end

# Pin operator
expected_status = 200
case response
in { status: ^expected_status }
  handle_success(response)
end
```

### Enumerable Idioms
```ruby
# Chaining
active_emails = users
  .select(&:active?)
  .reject { |u| u.email.nil? }
  .map(&:email)
  .uniq
  .sort

# Grouping and tallying
users.group_by(&:role)           # => { "admin" => [...], "user" => [...] }
users.tally_by(&:role)           # => { "admin" => 3, "user" => 15 }
orders.sum(&:total)
scores.filter_map { |s| s.value if s.valid? }

# each_with_object over inject for building hashes
users.each_with_object({}) do |user, memo|
  memo[user.id] = user.name
end
```

---

## Error Handling

### begin/rescue/ensure
```ruby
def fetch_user(id)
  user = api_client.get("/users/#{id}")
  User.new(user)
rescue Faraday::TimeoutError => e
  logger.warn("Timeout fetching user #{id}: #{e.message}")
  nil
rescue Faraday::ClientError => e
  raise if e.response_status != 404
  nil
rescue StandardError => e
  logger.error("Unexpected error: #{e.class} - #{e.message}")
  raise
ensure
  api_client.close if api_client
end
```

### Custom Exceptions
```ruby
module MyApp
  class Error < StandardError; end

  class NotFoundError < Error
    attr_reader :resource, :id

    def initialize(resource:, id:)
      @resource = resource
      @id = id
      super("#{resource} not found: #{id}")
    end
  end

  class ValidationError < Error
    attr_reader :errors

    def initialize(errors)
      @errors = errors
      super(errors.join(", "))
    end
  end

  class RateLimitError < Error
    attr_reader :retry_after

    def initialize(retry_after:)
      @retry_after = retry_after
      super("Rate limited. Retry after #{retry_after}s")
    end
  end
end
```

### Retry with Backoff
```ruby
def with_retries(max: 3, base_delay: 0.5, errors: [StandardError])
  attempts = 0
  begin
    attempts += 1
    yield
  rescue *errors => e
    raise if attempts >= max
    delay = base_delay * (2**(attempts - 1)) + rand(0.0..0.5)
    sleep(delay)
    retry
  end
end

with_retries(max: 5, errors: [Net::OpenTimeout, Faraday::TimeoutError]) do
  api_client.post("/webhook", payload)
end
```

### Dry::Monads (Railway-oriented)
```ruby
require "dry/monads"

class CreateUser
  include Dry::Monads[:result, :do]

  def call(params)
    values = yield validate(params)
    user   = yield persist(values)
    yield send_welcome_email(user)
    Success(user)
  end

  private

  def validate(params)
    result = UserContract.new.call(params)
    result.success? ? Success(result.to_h) : Failure(result.errors.to_h)
  end

  def persist(values)
    user = User.create(values)
    user.persisted? ? Success(user) : Failure(user.errors.full_messages)
  end

  def send_welcome_email(user)
    UserMailer.welcome(user).deliver_later
    Success(user)
  rescue StandardError => e
    # Non-critical -- log and continue
    Rails.logger.error("Welcome email failed: #{e.message}")
    Success(user)
  end
end
```

---

## Testing Patterns

### RSpec Structure
```ruby
RSpec.describe UserService, "#create" do
  subject(:result) { described_class.new(repo: repo).create(params) }

  let(:repo) { instance_double(UserRepository) }
  let(:params) { { name: "Ada", email: "ada@example.com" } }

  context "when params are valid" do
    before do
      allow(repo).to receive(:save).and_return(build(:user, **params))
    end

    it "returns the created user" do
      expect(result).to be_a(User)
      expect(result.name).to eq("Ada")
    end

    it "persists via repository" do
      result
      expect(repo).to have_received(:save).with(hash_including(name: "Ada"))
    end
  end

  context "when email is taken" do
    before do
      allow(repo).to receive(:save).and_raise(ActiveRecord::RecordNotUnique)
    end

    it "raises a duplicate error" do
      expect { result }.to raise_error(UserService::DuplicateEmail)
    end
  end
end
```

### FactoryBot
```ruby
FactoryBot.define do
  factory :user do
    name  { Faker::Name.name }
    email { Faker::Internet.unique.email }
    role  { :user }

    trait :admin do
      role { :admin }
    end

    trait :with_orders do
      transient do
        order_count { 3 }
      end

      after(:create) do |user, ctx|
        create_list(:order, ctx.order_count, user: user)
      end
    end
  end
end

# Usage
create(:user, :admin)
create(:user, :with_orders, order_count: 5)
build_stubbed(:user)  # No DB hit
```

### VCR / WebMock
```ruby
# spec/support/vcr.rb
VCR.configure do |c|
  c.cassette_library_dir = "spec/fixtures/cassettes"
  c.hook_into :webmock
  c.filter_sensitive_data("<API_KEY>") { ENV.fetch("API_KEY") }
  c.default_cassette_options = { record: :once, decode_compressed_response: true }
end

RSpec.describe GitHubClient do
  it "fetches repositories", vcr: { cassette_name: "github/repos" } do
    repos = described_class.new.repos("rails")
    expect(repos).not_to be_empty
    expect(repos.first).to respond_to(:name)
  end
end
```
