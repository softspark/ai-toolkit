---
name: kotlin-patterns
description: "Loaded when user asks about Kotlin development patterns"
effort: medium
user-invocable: false
allowed-tools: Read
---

# Kotlin Patterns Skill

## Project Structure

### Gradle KTS Multi-Module Layout
```
project-root/
├── build.gradle.kts
├── settings.gradle.kts
├── gradle/libs.versions.toml
├── app/
│   ├── build.gradle.kts
│   └── src/{main,test}/kotlin/com/example/app/
├── domain/
│   └── src/main/kotlin/com/example/domain/
│       ├── model/
│       ├── repository/
│       └── usecase/
└── infrastructure/
    └── src/main/kotlin/com/example/infra/
```

### settings.gradle.kts
```kotlin
rootProject.name = "my-project"
dependencyResolutionManagement {
    versionCatalogs { create("libs") { from(files("gradle/libs.versions.toml")) } }
}
include(":app", ":domain", ":infrastructure")
```

### Module build.gradle.kts
```kotlin
plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.kotlin.serialization)
}
dependencies {
    implementation(project(":domain"))
    implementation(libs.kotlinx.coroutines.core)
    testImplementation(libs.bundles.testing)
}
kotlin { jvmToolchain(21) }
```

---

## Idioms / Code Style

### Data Classes + Value Classes
```kotlin
data class User(
    val id: UserId,
    val name: String,
    val email: String,
    val role: Role = Role.USER,
) {
    init {
        require(name.isNotBlank()) { "Name must not be blank" }
        require(email.contains("@")) { "Invalid email format" }
    }
}

@JvmInline
value class UserId(val value: String)  // Zero-overhead type-safe ID
enum class Role { ADMIN, USER, GUEST }
```

### Sealed Interfaces for Domain Modeling
```kotlin
sealed interface PaymentResult {
    data class Success(val transactionId: String, val amount: Money) : PaymentResult
    data class Declined(val reason: String) : PaymentResult
    data class Error(val exception: Throwable) : PaymentResult
}

// Exhaustive when -- compiler enforces all branches
fun handlePayment(result: PaymentResult): String = when (result) {
    is PaymentResult.Success -> "Paid: ${result.amount}"
    is PaymentResult.Declined -> "Declined: ${result.reason}"
    is PaymentResult.Error -> "Error: ${result.exception.message}"
}
```

### Extension Functions
```kotlin
fun String.toSlug(): String =
    lowercase().replace(Regex("[^a-z0-9\\s-]"), "").replace(Regex("\\s+"), "-").trim('-')

// Scoped extensions -- visible only inside containing class
class OrderService {
    private fun Order.totalWithTax(): Money = total * (1 + taxRate)
}
```

### Null Safety
```kotlin
fun getDisplayName(user: User?): String =
    user?.name?.takeIf { it.isNotBlank() } ?: "Anonymous"

fun processEmail(email: String?) { email?.let { sendWelcomeEmail(it) } }

fun loadConfig(path: String?): Config {
    val resolved = requireNotNull(path) { "Config path must not be null" }
    return parseConfig(resolved)
}
```

### Scope Functions

| Function | Ref | Returns | Use case |
|----------|-----|---------|----------|
| `let` | `it` | Lambda result | Null check + transform |
| `run` | `this` | Lambda result | Config + compute |
| `apply` | `this` | Object itself | Object initialization |
| `also` | `it` | Object itself | Side effects |

```kotlin
val conn = Connection().apply { host = "localhost"; port = 5432 }
fun createUser(req: CreateUserRequest): User =
    userRepository.save(req.toUser()).also { logger.info("Created: ${it.id}") }
```

### Type-Safe Builders (DSL)
```kotlin
fun html(block: HtmlBuilder.() -> Unit): String = HtmlBuilder().apply(block).build()

val page = html {
    head { title("My Page") }
    body { p("Hello, world!") }
}
```

---

## Error Handling

### Result<T> and runCatching
```kotlin
fun findUser(id: UserId): Result<User> = runCatching {
    userRepository.findById(id) ?: throw UserNotFoundException(id)
}

fun getUserDisplayName(id: UserId): String =
    findUser(id).map { it.name }.recover { "Unknown User" }.getOrThrow()

fun handleLookup(id: UserId): Response = findUser(id).fold(
    onSuccess = { Response.ok(it) },
    onFailure = { Response.notFound(it.message) },
)
```

### Sealed Class Error Hierarchy
```kotlin
sealed class DomainError(override val message: String) : Exception(message) {
    data class NotFound(val resource: String, val id: String) : DomainError("$resource not found: $id")
    data class Validation(val field: String, val reason: String) : DomainError("Invalid $field: $reason")
    data class Conflict(val detail: String) : DomainError("Conflict: $detail")
}

fun handleError(error: DomainError): Response = when (error) {
    is DomainError.NotFound -> Response.status(404).body(error.message)
    is DomainError.Validation -> Response.status(422).body(error.message)
    is DomainError.Conflict -> Response.status(409).body(error.message)
}
```

### Preconditions
```kotlin
fun transferMoney(from: Account, to: Account, amount: Money) {
    require(amount.value > 0) { "Transfer amount must be positive" }
    require(from.id != to.id) { "Cannot transfer to same account" }
    check(from.balance >= amount) { "Insufficient funds: ${from.balance}" }
}
```

---

## Testing Patterns

### JUnit 5 + MockK
```kotlin
class UserServiceTest {
    private val repository = mockk<UserRepository>()
    private val notifier = mockk<NotificationService>(relaxed = true)
    private val service = UserService(repository, notifier)

    @Test
    fun `creates user and sends welcome notification`() {
        val expected = User(UserId("1"), "Alice", "alice@test.com")
        every { repository.save(any()) } returns expected

        val result = service.createUser(CreateUserRequest("Alice", "alice@test.com"))

        assertThat(result).isEqualTo(expected)
        verify(exactly = 1) { notifier.sendWelcome(expected) }
    }

    @Test
    fun `throws on duplicate email`() {
        every { repository.save(any()) } throws DomainError.Conflict("Email exists")
        assertThrows<DomainError.Conflict> {
            service.createUser(CreateUserRequest("Bob", "dup@test.com"))
        }
    }
}
```

### Kotest + Property-Based Testing
```kotlin
class MoneySpec : FunSpec({
    test("addition is commutative") {
        checkAll(Arb.positiveLong(), Arb.positiveLong()) { a, b ->
            Money(a) + Money(b) shouldBe Money(b) + Money(a)
        }
    }
    test("cannot create negative money") {
        shouldThrow<IllegalArgumentException> { Money(-1) }
    }
})
```

### assertSoftly + Parameterized Tests
```kotlin
@Test
fun `user has correct defaults`() {
    val user = User.create("Alice", "alice@test.com")
    assertSoftly(user) {
        name shouldBe "Alice"
        role shouldBe Role.USER
        isActive shouldBe true
    }
}

@ParameterizedTest
@CsvSource("alice@test.com, true", "not-an-email, false", "'', false")
fun `validates email format`(input: String, expected: Boolean) {
    assertThat(isValidEmail(input)).isEqualTo(expected)
}
```

---

## Common Frameworks

### Spring Boot with Kotlin
```kotlin
@RestController
@RequestMapping("/api/v1/users")
class UserController(private val userService: UserService) {
    @GetMapping("/{id}")
    fun getUser(@PathVariable id: String): ResponseEntity<UserDto> =
        userService.findById(UserId(id))?.let { ResponseEntity.ok(it.toDto()) }
            ?: ResponseEntity.notFound().build()

    @PostMapping
    fun createUser(@Valid @RequestBody req: CreateUserRequest): ResponseEntity<UserDto> {
        val user = userService.create(req)
        return ResponseEntity.created(URI("/api/v1/users/${user.id.value}")).body(user.toDto())
    }
}
```

### Ktor
```kotlin
fun Application.configureRouting() {
    routing {
        route("/api/v1/users") {
            get { call.respond(userService.listAll()) }
            get("/{id}") {
                val id = call.parameters["id"] ?: return@get call.respond(HttpStatusCode.BadRequest)
                val user = userService.findById(UserId(id)) ?: return@get call.respond(HttpStatusCode.NotFound)
                call.respond(user)
            }
            post {
                val req = call.receive<CreateUserRequest>()
                call.respond(HttpStatusCode.Created, userService.create(req))
            }
        }
    }
}

fun Application.configurePlugins() {
    install(ContentNegotiation) { json() }
    install(StatusPages) {
        exception<DomainError.NotFound> { call, e -> call.respond(HttpStatusCode.NotFound, e.message) }
    }
}
```

### Exposed (SQL DSL)
```kotlin
object Users : Table("users") {
    val id = varchar("id", 36)
    val name = varchar("name", 255)
    val email = varchar("email", 255).uniqueIndex()
    val role = enumerationByName<Role>("role", 20)
    override val primaryKey = PrimaryKey(id)
}

suspend fun findByRole(role: Role): List<User> = newSuspendedTransaction(Dispatchers.IO) {
    Users.selectAll().where { Users.role eq role }.map { it.toUser() }
}
```

### kotlinx.serialization
```kotlin
@Serializable
data class ApiResponse<T>(val data: T, val meta: Meta? = null)

@Serializable
data class Meta(val page: Int, val totalPages: Int, val totalItems: Long)
```

### Koin (DI)
```kotlin
val appModule = module {
    singleOf(::UserRepository)
    singleOf(::UserService)
    factoryOf(::CreateUserUseCase)
}
fun Application.configureKoin() { install(Koin) { modules(appModule) } }
```

---

## Performance Tips

### Inline Functions
```kotlin
inline fun <T> measureTimeAndReturn(block: () -> T): Pair<T, Duration> {
    val start = System.nanoTime()
    val result = block()
    return result to Duration.ofNanos(System.nanoTime() - start)
}
// crossinline: prevents non-local returns
inline fun transaction(crossinline block: () -> Unit) {
    begin(); try { block() } catch (e: Exception) { rollback(); throw e }; commit()
}
```

### Value Classes
```kotlin
@JvmInline value class Email(val value: String) {
    init { require(value.contains("@")) }
}
@JvmInline value class Meters(val value: Double)
// Compiles to raw String/Double -- zero object allocation
```

### Sequences vs Lists
```kotlin
// Bad: 3 intermediate lists
users.filter { it.isActive }.map { it.name }.take(10)
// Good: lazy, single pass, stops after 10
users.asSequence().filter { it.isActive }.map { it.name }.take(10).toList()
// Rule: sequences for 3+ chained ops on 1000+ elements
```

### Coroutines
```kotlin
suspend fun loadDashboard(userId: String): Dashboard = coroutineScope {
    val profile = async { userService.getProfile(userId) }
    val orders = async { orderService.getRecent(userId) }
    val notifs = async { notificationService.getUnread(userId) }
    Dashboard(profile.await(), orders.await(), notifs.await())
}

fun observeOrders(): Flow<Order> =
    orderRepository.observe().map { it.toDomain() }.catch { emit(Order.EMPTY) }.flowOn(Dispatchers.IO)
```

### Avoid Reflection
```kotlin
// Bad: Gson uses reflection -- slow, no compile-time safety
val json = Gson().toJson(user)
// Good: kotlinx.serialization uses compile-time codegen
@Serializable data class User(val id: String, val name: String)
val json = Json.encodeToString(user)
```

---

## Build / Package Management

### Version Catalog (gradle/libs.versions.toml)
```toml
[versions]
kotlin = "2.1.0"
coroutines = "1.10.1"
ktor = "3.0.3"
kotest = "5.9.1"
mockk = "1.13.14"

[libraries]
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version.ref = "coroutines" }
kotlinx-serialization-json = { module = "org.jetbrains.kotlinx:kotlinx-serialization-json", version = "1.7.3" }
ktor-server-core = { module = "io.ktor:ktor-server-core", version.ref = "ktor" }
mockk = { module = "io.mockk:mockk", version.ref = "mockk" }
kotest-runner = { module = "io.kotest:kotest-runner-junit5", version.ref = "kotest" }
kotest-assertions = { module = "io.kotest:kotest-assertions-core", version.ref = "kotest" }

[bundles]
testing = ["mockk", "kotest-runner", "kotest-assertions"]

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
kotlin-serialization = { id = "org.jetbrains.kotlin.plugin.serialization", version.ref = "kotlin" }
```

### Kotlin Multiplatform
```kotlin
kotlin {
    jvm(); iosArm64(); iosSimulatorArm64(); js(IR) { browser() }
    sourceSets {
        commonMain.dependencies {
            implementation(libs.kotlinx.coroutines.core)
            implementation(libs.kotlinx.serialization.json)
        }
        commonTest.dependencies { implementation(kotlin("test")) }
        jvmMain.dependencies { implementation(libs.ktor.server.core) }
    }
}
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| `!!` everywhere | NPE at runtime | Safe calls, elvis, `requireNotNull` |
| `var` by default | Mutability bugs | Default to `val` |
| Catching `Exception` | Swallows `CancellationException` | Catch specific types |
| Mutable data class props | Breaks hashCode/equals | Use `val` in data classes |
| Stringly-typed IDs | Mix up userId/orderId | Value classes |
| Blocking in coroutine | Thread starvation | `withContext(Dispatchers.IO)` |
| Ignoring `Result` failures | Silent errors | Always handle both paths |
| God object / util class | No cohesion | Extension functions |
