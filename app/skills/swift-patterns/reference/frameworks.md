# Swift Framework Patterns

Detailed patterns for SwiftUI, Combine, Structured Concurrency, SwiftData, and Vapor. Loaded on demand from `swift-patterns/SKILL.md`.

## SwiftUI + @Observable (iOS 17+)

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

## Combine

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

## Structured Concurrency

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

## SwiftData

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

## Vapor (Server-Side)

```swift
app.get("users", ":id") { req async throws -> User in
    guard let id = req.parameters.get("id", as: UUID.self) else { throw Abort(.badRequest) }
    guard let user = try await User.find(id, on: req.db) else { throw Abort(.notFound) }
    return user
}
```
