---
name: rust-patterns
description: "Loaded when user asks about Rust development patterns"
effort: medium
user-invocable: false
allowed-tools: Read
---

# Rust Patterns

## Project Structure

```
my-app/
├── Cargo.toml
├── src/
│   ├── main.rs           # Binary entry point
│   ├── lib.rs            # Library root (re-exports)
│   ├── error.rs          # Crate-level error types
│   ├── api/
│   │   ├── mod.rs
│   │   └── handlers.rs
│   └── domain/
│       ├── mod.rs
│       └── service.rs
├── tests/                # Integration tests (separate crate)
│   └── api_test.rs
├── benches/              # criterion benchmarks
│   └── throughput.rs
└── examples/
    └── demo.rs
```

Workspace layout for multi-crate projects:

```toml
# Cargo.toml (workspace root)
[workspace]
resolver = "2"
members = ["crates/core", "crates/api", "crates/cli"]

[workspace.dependencies]
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["full"] }
```

---

## Idioms / Code Style

### Ownership and Borrowing

```rust
// Borrow when you only need to read
fn print_name(name: &str) { println!("{name}"); }

// Take ownership when storing or consuming the value
fn register_user(name: String) -> User {
    User { name, id: Uuid::new_v4() }
}
```

### Lifetimes

```rust
// Annotate only when the compiler cannot infer
struct Parser<'input> {
    source: &'input str,
    pos: usize,
}

impl<'input> Parser<'input> {
    fn next_token(&mut self) -> Option<&'input str> {
        let start = self.pos;
        // ... advance self.pos ...
        Some(&self.source[start..self.pos])
    }
}
```

### Trait-Based Design

```rust
trait Repository {
    fn find_by_id(&self, id: Uuid) -> Result<Option<User>, DbError>;
    fn save(&self, user: &User) -> Result<(), DbError>;
}

// Accept generics for testability
fn create_user(repo: &impl Repository, name: String) -> Result<User, AppError> {
    let user = User::new(name);
    repo.save(&user)?;
    Ok(user)
}
```

### Iterators, Pattern Matching, Newtype

```rust
// Iterator chains over manual loops
let active: Vec<&str> = users.iter()
    .filter(|u| u.is_active)
    .map(|u| u.email.as_str())
    .collect();

// Exhaustive matching
match command {
    Command::Start { port } => start_server(port),
    Command::Stop => shutdown(),
}

// let-else for early exit (Rust 1.65+)
let Some(cfg) = load_config() else { return Ok(Config::default()); };

// Newtype to prevent primitive misuse
struct UserId(Uuid);
struct Email(String);

impl Email {
    fn new(raw: &str) -> Result<Self, ValidationError> {
        if raw.contains('@') { Ok(Self(raw.to_lowercase())) }
        else { Err(ValidationError::InvalidEmail) }
    }
}
```

### Builder Pattern

```rust
#[derive(Default)]
struct RequestBuilder { url: String, timeout: Option<Duration> }

impl RequestBuilder {
    fn url(mut self, url: impl Into<String>) -> Self { self.url = url.into(); self }
    fn timeout(mut self, d: Duration) -> Self { self.timeout = Some(d); self }
    fn build(self) -> Result<Request, BuildError> {
        if self.url.is_empty() { return Err(BuildError::MissingUrl); }
        Ok(Request { url: self.url, timeout: self.timeout.unwrap_or(Duration::from_secs(30)) })
    }
}
```

---

## Error Handling

### thiserror (libraries) vs anyhow (binaries)

```rust
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("validation failed: {0}")]
    Validation(String),
    #[error("database error")]
    Database(#[from] sqlx::Error),
    #[error(transparent)]
    Unexpected(#[from] anyhow::Error),
}
```

```rust
// anyhow for application / binary code -- adds context to any error
use anyhow::{Context, Result};

fn load_config(path: &Path) -> Result<Config> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("failed to read {}", path.display()))?;
    toml::from_str(&content).context("invalid TOML")
}
```

### Error Propagation and Boundary Mapping

```rust
// ? converts and propagates via From impls
fn get_email(pool: &PgPool, id: Uuid) -> Result<String, AppError> {
    let user = sqlx::query_as!(User, "SELECT * FROM users WHERE id = $1", id)
        .fetch_optional(pool).await?
        .ok_or_else(|| AppError::NotFound(format!("user {id}")))?;
    Ok(user.email)
}

// Map domain errors to HTTP at the API boundary
impl IntoResponse for AppError {
    fn into_response(self) -> axum::response::Response {
        let (status, msg) = match &self {
            AppError::NotFound(m) => (StatusCode::NOT_FOUND, m.clone()),
            AppError::Validation(m) => (StatusCode::BAD_REQUEST, m.clone()),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, "internal error".into()),
        };
        (status, Json(json!({ "error": msg }))).into_response()
    }
}
```

---

## Testing Patterns

### Unit Tests (inline module)

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn email_rejects_invalid() { assert!(Email::new("bad").is_err()); }

    #[tokio::test]
    async fn fetches_user() {
        let pool = setup_test_db().await;
        let user = get_user(&pool, test_id()).await.unwrap();
        assert_eq!(user.name, "Alice");
    }
}
```

### Integration Tests (tests/ directory)

```rust
// tests/api_test.rs -- compiled as separate crate, only sees pub API
#[tokio::test]
async fn health_returns_200() {
    let app = my_app::app().await;
    let resp = app.oneshot(
        Request::builder().uri("/health").body(Body::empty()).unwrap()
    ).await.unwrap();
    assert_eq!(resp.status(), StatusCode::OK);
}
```

### Mocking (mockall) and Property Testing (proptest)

```rust
use mockall::automock;

#[automock]
trait UserRepo { fn find(&self, id: Uuid) -> Result<Option<User>, DbError>; }

#[test]
fn returns_not_found_when_missing() {
    let mut mock = MockUserRepo::new();
    mock.expect_find().returning(|_| Ok(None));
    assert!(matches!(UserService::new(mock).get_user(id), Err(AppError::NotFound(_))));
}
```

```rust
use proptest::prelude::*;
proptest! {
    #[test]
    fn roundtrips(s in "[a-z]{1,20}@[a-z]{1,10}\\.[a-z]{2,4}") {
        let e = Email::new(&s).unwrap();
        assert_eq!(e.to_string(), s.to_lowercase());
    }
}
```

```bash
cargo test                        # All tests
cargo test --lib                  # Unit only
cargo test --test api_test        # Single integration file
cargo nextest run                 # Parallel runner, better output
```

---

## Common Libraries

| Crate | Purpose | Notes |
|-------|---------|-------|
| **serde** / serde_json | Serialization | `#[derive(Serialize, Deserialize)]` on DTOs |
| **tokio** | Async runtime | `features = ["full"]` for apps |
| **axum** | HTTP framework | Tower-based, extractors, `State` |
| **clap** | CLI parsing | `#[derive(Parser)]` |
| **reqwest** | HTTP client | Async, rustls TLS |
| **tracing** | Structured logging | Replaces `log`; use `tracing-subscriber` |
| **sqlx** | Async SQL | Compile-time checked queries |
| **tower** | Middleware | Layers, timeouts, rate limiting |
| **rayon** | Data parallelism | `.par_iter()` drop-in |
| **criterion** | Benchmarking | Statistical, HTML reports |

### Axum + Tracing Minimal Server

```rust
use axum::{extract::State, routing::get, Json, Router};
use std::sync::Arc;

struct AppState { db: PgPool }

async fn list_users(State(s): State<Arc<AppState>>) -> Json<Vec<User>> {
    Json(sqlx::query_as!(User, "SELECT * FROM users")
        .fetch_all(&s.db).await.unwrap())
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .json().init();
    let pool = PgPool::connect(&std::env::var("DATABASE_URL").unwrap()).await.unwrap();
    let app = Router::new().route("/users", get(list_users)).with_state(Arc::new(AppState { db: pool }));
    let listener = tokio::net::TcpListener::bind("0.0.0.0:3000").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

---

## Performance Tips

```rust
// Avoid cloning -- return references when possible
fn names(data: &[Record]) -> Vec<&str> {
    data.iter().map(|r| r.name.as_str()).collect()
}

// Cow for conditional ownership -- zero alloc on the happy path
use std::borrow::Cow;
fn normalize(input: &str) -> Cow<'_, str> {
    if input.contains(' ') { Cow::Owned(input.replace(' ', "_")) }
    else { Cow::Borrowed(input) }
}

// Rayon for CPU-bound parallelism
use rayon::prelude::*;
let out: Vec<_> = inputs.par_iter().map(|i| compute(i)).collect();

// Preallocate collections
let mut v = Vec::with_capacity(items.len());

// Zero-cost abstractions: iterators compile to the same code as manual loops
let sum: u64 = values.iter().filter(|v| **v > 0).sum();

// #[inline] only on small hot functions crossing crate boundaries
```

### Benchmarking (criterion)

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn bench_parse(c: &mut Criterion) {
    let input = include_str!("../fixtures/large.json");
    c.bench_function("parse_json", |b| b.iter(|| parse(black_box(input))));
}
criterion_group!(benches, bench_parse);
criterion_main!(benches);
```

---

## Build / Package Management

### Cargo.toml

```toml
[package]
name = "my-app"
version = "0.1.0"
edition = "2021"
rust-version = "1.75"              # MSRV

[dependencies]
serde = { version = "1", features = ["derive"] }
tokio = { version = "1", features = ["full"] }

[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }
mockall = "0.13"

[[bench]]
name = "throughput"
harness = false
```

### Feature Flags

```toml
[features]
default = ["json"]
json = ["serde_json"]
postgres = ["sqlx/postgres"]
```

```rust
#[cfg(feature = "postgres")]
pub mod pg_backend;
```

### Release Profile

```toml
[profile.release]
lto = true
codegen-units = 1
strip = true
panic = "abort"

[profile.dev.package."*"]
opt-level = 2                      # Optimize deps even in dev
```

### Cross-Compilation

```bash
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl
# Or use cross for Docker-based builds
cargo install cross && cross build --release --target aarch64-unknown-linux-gnu
```

### Essential Cargo Commands

```bash
cargo clippy -- -D warnings       # Lint (treat warnings as errors)
cargo fmt --check                  # Format check
cargo doc --open                   # Generate docs
cargo tree -d                      # Duplicate dependencies
cargo audit                        # Known vulnerabilities
cargo deny check                   # License and advisory
cargo bloat --release              # Binary size analysis
```

### CI Pipeline (minimum)

```bash
cargo fmt --check && cargo clippy -- -D warnings && cargo test && cargo audit
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| `.unwrap()` in lib code | Panics | Return `Result`/`Option` |
| `.clone()` everywhere | Hidden allocs | Borrow, `Cow`, restructure ownership |
| `String` in every field | Unnecessary allocs | `&str` or `Cow<str>` where lifetime allows |
| `Box<dyn Error>` only | No matching | `thiserror` enums |
| `Arc<Mutex<T>>` first | Contention | Channels (`tokio::sync::mpsc`) or actors |
| Ignoring `#[must_use]` | Silent drops | Handle or `let _ =` explicitly |
