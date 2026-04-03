---
name: swift-patterns
description: "Loaded when user asks about Swift or iOS development patterns"
effort: medium
user-invocable: false
allowed-tools: Read
---

# Swift / iOS Patterns

## Project Structure

### Swift Package (SPM)

```
MyPackage/
├── Package.swift
├── Sources/
│   ├── MyLibrary/
│   └── MyExecutable/
├── Tests/
│   └── MyLibraryTests/
└── Plugins/
```

```swift
// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "MyPackage",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "MyLibrary", targets: ["MyLibrary"]),
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-algorithms", from: "1.2.0"),
    ],
    targets: [
        .target(name: "MyLibrary",
                dependencies: [.product(name: "Algorithms", package: "swift-algorithms")]),
        .testTarget(name: "MyLibraryTests", dependencies: ["MyLibrary"]),
    ]
)
```

### Xcode Project Layout

```
MyApp/
├── MyApp/
│   ├── App/             # Entry point, ContentView
│   ├── Features/        # Feature modules (Views, ViewModels, Models)
│   ├── Core/            # Networking, Storage, Extensions
│   └── Resources/       # Assets.xcassets, Info.plist
├── MyAppTests/
└── MyAppUITests/
```

---

## Idioms / Code Style

### Optionals

```swift
// guard-let for early exit
func process(user: User?) {
    guard let user else { return }
    print(user.name)
}

// Optional chaining + nil coalescing
let name = user?.profile?.displayName ?? "Anonymous"

// map/flatMap on optionals
let length: Int? = optionalString.map { $0.count }
// Never force-unwrap in production: user!.name
```

### Protocol-Oriented Programming

```swift
protocol Cacheable: Identifiable where ID: Hashable {
    var cacheKey: String { get }
}

extension Cacheable where ID == String {
    var cacheKey: String { id }
}
```

### Value Types vs Reference Types

Use structs by default (value semantics, thread-safe). Use classes when identity matters, shared mutable state is intentional, inheritance is needed, or ObjC interop is required.

### Property Wrappers

```swift
@propertyWrapper
struct Clamped<Value: Comparable> {
    var wrappedValue: Value {
        didSet { wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound) }
    }
    let range: ClosedRange<Value>

    init(wrappedValue: Value, _ range: ClosedRange<Value>) {
        self.range = range
        self.wrappedValue = min(max(wrappedValue, range.lowerBound), range.upperBound)
    }
}

struct Volume {
    @Clamped(0...100) var level: Int = 50
}
```

### Result Builders

```swift
@resultBuilder
struct ArrayBuilder<Element> {
    static func buildBlock(_ components: [Element]...) -> [Element] { components.flatMap { $0 } }
    static func buildExpression(_ expression: Element) -> [Element] { [expression] }
    static func buildOptional(_ component: [Element]?) -> [Element] { component ?? [] }
}
```

---

## Error Handling

### throws / try / catch

```swift
enum NetworkError: Error, LocalizedError {
    case invalidURL
    case timeout(seconds: Int)
    case serverError(statusCode: Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL: "Invalid URL."
        case .timeout(let s): "Timed out after \(s)s."
        case .serverError(let code): "Server returned \(code)."
        }
    }
}

do {
    let user = try fetchUser(id: "123")
} catch let error as NetworkError {
    handleNetworkError(error)
} catch {
    handleUnexpected(error)
}

let user = try? fetchUser(id: "123") // nil on error
```

### Result Type

```swift
switch fetchData(from: url) {
case .success(let data): process(data)
case .failure(let error): showError(error)
}
```

### Typed Throws (Swift 6) and Async Throws

```swift
func load() throws(DatabaseError) -> [Item] { /* compiler-enforced error type */ }

func fetchUser(id: String) async throws -> User {
    let (data, response) = try await URLSession.shared.data(from: url)
    guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
        throw NetworkError.serverError(statusCode: 0)
    }
    return try JSONDecoder().decode(User.self, from: data)
}
```

---

## Testing

### XCTest

```swift
final class UserServiceTests: XCTestCase {
    var sut: UserService!
    var mockRepo: MockUserRepository!

    override func setUp() {
        mockRepo = MockUserRepository()
        sut = UserService(repository: mockRepo)
    }

    func testFetchUser_success() async throws {
        mockRepo.stubbedUser = User(id: "1", name: "Alice")
        let user = try await sut.fetchUser(id: "1")
        XCTAssertEqual(user.name, "Alice")
    }

    func testFetchUser_notFound_throws() async {
        mockRepo.shouldFail = true
        do {
            _ = try await sut.fetchUser(id: "999")
            XCTFail("Expected error")
        } catch {
            XCTAssertTrue(error is UserService.Error)
        }
    }
}
```

### Swift Testing Framework (Swift 6+)

```swift
import Testing

@Suite("UserService")
struct UserServiceTests {
    @Test("fetches user by ID")
    func fetchUser() async throws {
        let mockRepo = MockUserRepository()
        mockRepo.stubbedUser = User(id: "1", name: "Alice")
        let sut = UserService(repository: mockRepo)
        let user = try await sut.fetchUser(id: "1")
        #expect(user.name == "Alice")
    }

    @Test("throws on missing user", arguments: ["999", ""])
    func fetchMissingUser(id: String) async {
        let sut = UserService(repository: MockUserRepository())
        await #expect(throws: UserService.Error.self) {
            try await sut.fetchUser(id: id)
        }
    }
}
```

### Protocol-Based Mocking

```swift
protocol UserRepository {
    func fetch(id: String) async throws -> User
}

final class MockUserRepository: UserRepository {
    var stubbedUser: User?
    var shouldFail = false
    private(set) var fetchCallCount = 0

    func fetch(id: String) async throws -> User {
        fetchCallCount += 1
        if shouldFail { throw NSError(domain: "", code: 0) }
        return stubbedUser ?? User(id: id, name: "Default")
    }
}
```

### UI Testing

```swift
func testLoginFlow() {
    let app = XCUIApplication()
    app.launchArguments = ["--uitesting"]
    app.launch()
    app.textFields["email"].tap()
    app.textFields["email"].typeText("user@example.com")
    app.secureTextFields["password"].typeText("pass")
    app.buttons["Sign In"].tap()
    XCTAssertTrue(app.staticTexts["Welcome"].waitForExistence(timeout: 5))
}
```

---

## Common Frameworks

### SwiftUI + @Observable (iOS 17+)

```swift
@Observable
final class UserViewModel {
    var users: [User] = []
    var isLoading = false
    private let service: UserService

    init(service: UserService) { self.service = service }

    func load() async {
        isLoading = true
        defer { isLoading = false }
        users = (try? await service.fetchAll()) ?? []
    }
}

struct UserListView: View {
    @State private var vm: UserViewModel

    init(service: UserService) {
        _vm = State(initialValue: UserViewModel(service: service))
    }

    var body: some View {
        NavigationStack {
            List(vm.users) { user in
                NavigationLink(value: user) { Text(user.name) }
            }
            .navigationTitle("Users")
            .navigationDestination(for: User.self) { UserDetailView(user: $0) }
            .task { await vm.load() }
        }
    }
}
```

### Combine

```swift
class SearchVM: ObservableObject {
    @Published var query = ""
    @Published var results: [Item] = []
    private var cancellables = Set<AnyCancellable>()

    init(service: SearchService) {
        $query
            .debounce(for: .milliseconds(300), scheduler: DispatchQueue.main)
            .removeDuplicates()
            .filter { !$0.isEmpty }
            .flatMap { service.search(query: $0) }
            .receive(on: DispatchQueue.main)
            .sink(receiveCompletion: { _ in },
                  receiveValue: { [weak self] in self?.results = $0 })
            .store(in: &cancellables)
    }
}
```

### Structured Concurrency

```swift
func fetchAllProfiles(ids: [String]) async throws -> [Profile] {
    try await withThrowingTaskGroup(of: Profile.self) { group in
        for id in ids { group.addTask { try await fetchProfile(id: id) } }
        return try await group.reduce(into: []) { $0.append($1) }
    }
}

// AsyncStream for bridging callbacks
let locations = AsyncStream<Location> { continuation in
    manager.onUpdate = { continuation.yield($0) }
    continuation.onTermination = { _ in manager.stop() }
}
```

### SwiftData

```swift
@Model
final class Item {
    var title: String
    var timestamp: Date
    @Relationship(deleteRule: .cascade) var tags: [Tag]
    init(title: String) { self.title = title; self.timestamp = .now; self.tags = [] }
}

struct ItemListView: View {
    @Query(sort: \Item.timestamp, order: .reverse) private var items: [Item]
    @Environment(\.modelContext) private var context

    var body: some View {
        List(items) { Text($0.title) }
    }
}
```

### Vapor (Server-Side)

```swift
app.get("users", ":id") { req async throws -> User in
    guard let id = req.parameters.get("id", as: UUID.self) else { throw Abort(.badRequest) }
    guard let user = try await User.find(id, on: req.db) else { throw Abort(.notFound) }
    return user
}
```

---

## Performance

### Copy-on-Write

Array, String, Dictionary use COW automatically. For custom value types:

```swift
struct LargeData {
    private final class Storage { var buffer: [UInt8]; init(_ b: [UInt8]) { buffer = b } }
    private var storage: Storage

    var buffer: [UInt8] {
        get { storage.buffer }
        set {
            if !isKnownUniquelyReferenced(&storage) { storage = Storage(newValue) }
            else { storage.buffer = newValue }
        }
    }
}
```

### ARC Retain Cycles

```swift
// weak — closure may outlive self
service.fetch { [weak self] result in
    guard let self else { return }
    self.update(with: result)
}

// unowned — self guaranteed to outlive closure
lazy var tick: () -> Void = { [unowned self] in self.count += 1 }
```

### Sendable and Actors

```swift
struct Config: Sendable { let apiURL: URL; let timeout: TimeInterval }

actor ImageCache {
    private var cache: [URL: Data] = [:]
    func image(for url: URL) -> Data? { cache[url] }
    func store(_ data: Data, for url: URL) { cache[url] = data }
}
```

### Instruments

| Instrument | Use For |
|---|---|
| Time Profiler | CPU bottlenecks |
| Allocations | Memory growth |
| Leaks | Retain cycles |
| SwiftUI | View body re-evaluations |
| Core Animation | FPS, offscreen rendering |

Profile on device (not simulator). Use `os_signpost` for custom spans.

---

## Build / Package Management

### SPM Commands

```bash
swift package resolve       # Resolve deps
swift build -c release      # Release build
swift test --filter MyTests # Filtered test run
```

### xcconfig

```
// Shared.xcconfig
SWIFT_VERSION = 5.10
IPHONEOS_DEPLOYMENT_TARGET = 17.0
SWIFT_STRICT_CONCURRENCY = complete

// Debug.xcconfig
#include "Shared.xcconfig"
SWIFT_OPTIMIZATION_LEVEL = -Onone
SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG

// Release.xcconfig
#include "Shared.xcconfig"
SWIFT_OPTIMIZATION_LEVEL = -O
SWIFT_COMPILATION_MODE = wholemodule
```

### Tuist

Define targets in `Project.swift` using `ProjectDescription`. Map each app, framework, and test target with `bundleId`, `sources`, and `dependencies`. Use `.external(name:)` for SPM deps and `.target(name:)` for internal.

Schemes: separate Debug/Release/Testing. Enable ASan + TSan in test schemes.

---

## Anti-Patterns
| Anti-Pattern | Problem | Fix |
|---|---|---|
| Force unwrap `!` | Runtime crash | `guard let`, `if let`, `??` |
| Massive view controller | Untestable | MVVM, composable views |
| Stringly-typed APIs | No compiler checks | Enums, phantom types |
| Ignoring `@MainActor` | Off-main-thread UI | Annotate view models |
| Retain cycles | Memory leaks | `[weak self]` / `[unowned self]` |
| Blocking main thread | UI freezes | `async/await`, `Task { }` |
| `UserDefaults` for secrets | Insecure | Keychain (`SecItemAdd`) |
| `@ObservedObject` for owned state | Object recreated | `@StateObject` or `@State` + `@Observable` |
