---
language: swift
category: frameworks
version: "1.0.0"
---

# Swift Frameworks

## SwiftUI
- Use `VStack`, `HStack`, `ZStack` for layout composition.
- Use `List` with `ForEach` for dynamic content. Use `LazyVStack` for large lists.
- Use `NavigationStack` (iOS 16+) with `navigationDestination(for:)` for type-safe navigation.
- Use `.task { }` modifier for async data loading tied to view lifecycle.
- Use `@ViewBuilder` for conditional view composition in custom containers.
- Use `PreviewProvider` or `#Preview` macro for rapid UI iteration.

## UIKit (Legacy / Hybrid)
- Use `UIHostingController` to embed SwiftUI views in UIKit.
- Use `UIViewRepresentable` to wrap UIKit views in SwiftUI.
- Use Auto Layout with constraints or `UIStackView` for layout.
- Use `UICollectionViewCompositionalLayout` for complex collection layouts.
- Use `Coordinator` pattern for delegate-based UIKit interop in SwiftUI.

## Combine
- Use `Publisher` / `Subscriber` for reactive data streams.
- Use `sink` for subscribing. Store cancellables in `Set<AnyCancellable>`.
- Use `map`, `filter`, `flatMap`, `combineLatest` for stream transformation.
- Use `@Published` on class properties for automatic publisher generation.
- Prefer `AsyncSequence` (async/await) over Combine for new code.

## Swift Data
- Use `@Model` macro for persistent model definitions.
- Use `@Query` in SwiftUI views for automatic fetching and observation.
- Use `ModelContext` for CRUD operations: `context.insert(item)`, `context.delete(item)`.
- Use `#Predicate` macro for type-safe query filtering.
- Use `ModelConfiguration` for custom store locations and migration options.

## Core Data (Legacy)
- Use `NSPersistentContainer` for stack setup.
- Use `NSFetchRequest` with `NSPredicate` for querying.
- Use `performBackgroundTask` for background context operations.
- Use lightweight migrations for schema changes when possible.
- Prefer SwiftData for new projects (iOS 17+).

## Vapor (Server-Side)
- Use `routes.get("users")` for route definitions.
- Use `Content` protocol for request/response body codable conformance.
- Use Fluent ORM with migrations for database access.
- Use middleware for authentication, CORS, and error handling.
- Use `async`/`await` natively (Vapor 4+ is fully async).

## Networking
- Use `URLSession` with `async/await` for HTTP requests.
- Use `Codable` with `JSONDecoder` for response parsing.
- Use `URLCache` and `ETag` for response caching.
- Set `timeoutIntervalForRequest` on `URLSessionConfiguration`.
- Use `TaskLocal` for request-scoped values (tracing, auth context).

## Package Management
- Use Swift Package Manager (SPM) for dependency management.
- Define dependencies in `Package.swift` with exact version or version ranges.
- Use `Package.resolved` committed to the repository for reproducible builds.
- Prefer SPM over CocoaPods/Carthage for new projects.
