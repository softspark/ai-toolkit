---
name: java-patterns
description: "Java development patterns: Spring Boot, CompletableFuture, records, sealed types, streams, JPA/Hibernate, Maven/Gradle, virtual threads (Loom). Triggers: Java, Spring, Spring Boot, JPA, Hibernate, Maven, Gradle, CompletableFuture, record type, sealed class, virtual thread. Load when writing or reviewing Java code."
effort: medium
user-invocable: false
allowed-tools: Read
---

# Java Patterns Skill

## Project Structure

### Maven / Gradle Standard Layout

```
my-app/
├── pom.xml (or build.gradle.kts + settings.gradle.kts)
├── src/
│   ├── main/
│   │   ├── java/com/example/myapp/
│   │   │   ├── MyApplication.java
│   │   │   ├── config/
│   │   │   ├── controller/
│   │   │   ├── service/
│   │   │   ├── repository/
│   │   │   ├── model/
│   │   │   │   ├── entity/
│   │   │   │   └── dto/
│   │   │   └── exception/
│   │   └── resources/
│   │       ├── application.yml
│   │       └── db/migration/
│   └── test/
│       ├── java/com/example/myapp/
│       └── resources/application-test.yml
└── target/ (or build/)
```

### Multi-Module

```
parent/
├── pom.xml              (packaging=pom)
├── common/              (shared utilities)
├── domain/              (entities, business rules)
├── api/                 (REST controllers, DTOs)
└── app/                 (Spring Boot main, wiring)
```

---

## Idioms / Code Style

### Records (Java 16+)
```java
public record UserDto(Long id, String name, String email) {
    public UserDto {  // compact constructor for validation
        Objects.requireNonNull(name, "name must not be null");
        Objects.requireNonNull(email, "email must not be null");
    }
}
```

### Sealed Classes (Java 17+)
```java
public sealed interface Shape permits Circle, Rectangle, Triangle {
    double area();
}
public record Circle(double radius) implements Shape {
    public double area() { return Math.PI * radius * radius; }
}
public record Rectangle(double w, double h) implements Shape {
    public double area() { return w * h; }
}
public record Triangle(double base, double height) implements Shape {
    public double area() { return 0.5 * base * height; }
}
```

### Switch Expressions (Java 14+)
```java
String describe(Shape shape) {
    return switch (shape) {
        case Circle c    -> "Circle r=" + c.radius();
        case Rectangle r -> "Rect %sx%s".formatted(r.w(), r.h());
        case Triangle t  -> "Triangle base=" + t.base();
    };
}
// Guard patterns (Java 21+)
String classify(Shape shape) {
    return switch (shape) {
        case Circle c when c.radius() > 100 -> "large circle";
        case Circle c                        -> "small circle";
        case Rectangle r                     -> "rectangle";
        case Triangle t                      -> "triangle";
    };
}
```

### var, Streams, Optional
```java
// var -- use when RHS makes type obvious
var users = new ArrayList<User>();
var response = client.send(request, HttpResponse.BodyHandlers.ofString());
// Avoid: var result = service.process(data); -- type unclear

// Streams
List<String> names = users.stream()
    .filter(User::isActive)
    .map(User::name)
    .sorted()
    .toList();  // Java 16+, unmodifiable

Map<Department, List<User>> byDept = users.stream()
    .collect(Collectors.groupingBy(User::department));

// Optional -- return type only, never as field or parameter
String city = findByEmail(email)
    .map(User::address)
    .map(Address::city)
    .orElse("Unknown");
// Never call .get() without guard -- use orElse/orElseThrow

// Text blocks (Java 15+)
String json = """
    {"name": "%s", "email": "%s"}
    """.formatted(name, email);
```

---

## Error Handling

| Type | When | Examples |
|------|------|---------|
| Checked | Recoverable I/O the caller must handle | IOException, SQLException |
| Unchecked | Programming errors, business rule violations | IllegalArgumentException, custom domain exceptions |

### Custom Exception Hierarchy
```java
public abstract class DomainException extends RuntimeException {
    private final String errorCode;
    protected DomainException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }
    public String errorCode() { return errorCode; }
}

public class EntityNotFoundException extends DomainException {
    public EntityNotFoundException(String entity, Object id) {
        super("NOT_FOUND", "%s with id %s not found".formatted(entity, id));
    }
}
```

### Try-With-Resources
```java
try (var conn = dataSource.getConnection();
     var stmt = conn.prepareStatement(sql);
     var rs = stmt.executeQuery()) {
    while (rs.next()) { results.add(mapRow(rs)); }
}
```

### Global Handler (Spring)
```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(EntityNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(EntityNotFoundException ex) {
        return ResponseEntity.status(404).body(new ErrorResponse(ex.errorCode(), ex.getMessage()));
    }
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        var errors = ex.getBindingResult().getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage()).toList();
        return ResponseEntity.badRequest().body(new ErrorResponse("VALIDATION_ERROR", errors.toString()));
    }
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception ex) {
        log.error("Unhandled exception", ex);
        return ResponseEntity.internalServerError()
            .body(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred"));
    }
}
public record ErrorResponse(String code, String message) {}
```

---

## Testing Patterns

### JUnit 5 + Mockito + AssertJ
```java
@DisplayName("UserService")
class UserServiceTest {
    private UserRepository repository;
    private UserService service;

    @BeforeEach
    void setUp() {
        repository = mock(UserRepository.class);
        service = new UserService(repository);
    }

    @Test
    void createsUserWithValidData() {
        var request = new CreateUserRequest("Alice", "alice@example.com");
        when(repository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        var user = service.createUser(request);

        assertThat(user.name()).isEqualTo("Alice");
        verify(repository).save(any(User.class));
    }

    @Test
    void throwsWhenEmailExists() {
        when(repository.existsByEmail("taken@test.com")).thenReturn(true);
        assertThatThrownBy(() -> service.createUser(new CreateUserRequest("Bob", "taken@test.com")))
            .isInstanceOf(BusinessRuleViolationException.class)
            .hasMessageContaining("email already exists");
    }
}
```

### Parameterized Tests
```java
@ParameterizedTest
@CsvSource({"1,1,2", "0,0,0", "-1,1,0", "100,200,300"})
void addReturnsSumOfArguments(int a, int b, int expected) {
    assertThat(calculator.add(a, b)).isEqualTo(expected);
}

@ParameterizedTest
@MethodSource("invalidEmails")
void rejectsInvalidEmail(String email) {
    assertThatThrownBy(() -> new Email(email)).isInstanceOf(IllegalArgumentException.class);
}
static Stream<String> invalidEmails() {
    return Stream.of("", "no-at-sign", "@no-local", "spaces in@email.com");
}
```

### Mockito Extras
```java
// Argument captor
var captor = ArgumentCaptor.forClass(User.class);
verify(repository).save(captor.capture());
assertThat(captor.getValue().name()).isEqualTo("Alice");

// BDD style
given(repository.findById(1L)).willReturn(Optional.of(user));
then(repository).should().findById(1L);
```

### Testcontainers (Integration)
```java
@Testcontainers
@SpringBootTest
class UserRepositoryIT {
    @Container
    static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", pg::getJdbcUrl);
        r.add("spring.datasource.username", pg::getUsername);
        r.add("spring.datasource.password", pg::getPassword);
    }

    @Autowired UserRepository repository;

    @Test
    void savesAndRetrievesUser() {
        var saved = repository.save(new User("Alice", "alice@test.com"));
        assertThat(repository.findById(saved.getId())).isPresent()
            .get().extracting("name").isEqualTo("Alice");
    }
}
```

---

## Common Frameworks

### Spring Boot (Controller / Service / Repository)
```java
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping
    public List<UserDto> list(@RequestParam(defaultValue = "0") int page,
                              @RequestParam(defaultValue = "20") int size) {
        return userService.list(PageRequest.of(page, size));
    }

    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    public UserDto create(@Valid @RequestBody CreateUserRequest request) {
        return userService.create(request);
    }
}

@Service @Transactional(readOnly = true) @RequiredArgsConstructor
public class UserService {
    private final UserRepository repository;
    private final UserMapper mapper;

    @Transactional
    public UserDto create(CreateUserRequest request) {
        if (repository.existsByEmail(request.email()))
            throw new BusinessRuleViolationException("email already exists");
        return mapper.toDto(repository.save(mapper.toEntity(request)));
    }
}

public interface UserRepository extends JpaRepository<User, Long> {
    boolean existsByEmail(String email);
    @Query("SELECT u FROM User u WHERE u.active = true AND u.role = :role")
    List<User> findActiveByRole(@Param("role") Role role);
}
```

### Quarkus
Uses Jakarta REST (`@Path`, `@GET`, `@POST`) + CDI (`@Inject`, `@ApplicationScoped`). Panache simplifies JPA: `implements PanacheRepository<User>` gives `find()`, `persist()`, `list()` out of the box. Use `@Transactional` on mutating endpoints.

### Jackson, Lombok, MapStruct
```java
// Jackson -- snake_case response
@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ApiResponse<T>(T data, @JsonInclude(Include.NON_NULL) String error) {}

// Lombok -- JPA entities only (use records for DTOs)
@Entity @Getter @Setter @NoArgsConstructor(access = PROTECTED)
@Builder @ToString(exclude = "password") @EqualsAndHashCode(of = "id")
public class User {
    @Id @GeneratedValue(strategy = IDENTITY) private Long id;
    private String name;
    private String email;
    private String password;
}

// MapStruct
@Mapper(componentModel = "spring")
public interface UserMapper {
    UserDto toDto(User entity);
    User toEntity(CreateUserRequest request);
}
```

---

## Performance Tips

### JVM Tuning
```bash
# Container-friendly (Java 17+)
java -XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -jar app.jar

# GC: -XX:+UseZGC (low latency) | -XX:+UseG1GC (balanced, default) | -XX:+UseParallelGC (throughput)
```

### Virtual Threads (Java 21+)
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    var futures = urls.stream().map(url -> executor.submit(() -> fetch(url))).toList();
    var results = futures.stream().map(f -> { try { return f.get(); }
        catch (Exception e) { throw new RuntimeException(e); } }).toList();
}
// Spring Boot 3.2+: spring.threads.virtual.enabled=true
```

### Profiling with JFR
```bash
java -XX:StartFlightRecording=duration=60s,filename=profile.jfr -jar app.jar
jfr print --events jdk.CPULoad,jdk.GCHeapSummary profile.jfr
```

### Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| String concat in loop | `StringBuilder` or `String.join()` |
| Unbounded caches | `Caffeine` with `maximumSize` + `expireAfterWrite` |
| Autoboxing in hot path | Primitive streams (`mapToInt`) or primitive collections |
| Synchronized everything | `ConcurrentHashMap`, `StampedLock`, virtual threads |
| Reflection in tight loop | Cache `MethodHandle` or use code generation |

---

## Build / Package Management

### Maven (key elements)
```xml
<properties>
  <java.version>21</java.version>
</properties>
<parent>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-parent</artifactId>
  <version>3.3.0</version>
</parent>
<!-- Use dependencyManagement + BOM for non-Boot projects -->
```

### Gradle Kotlin DSL
```kotlin
plugins { java; id("org.springframework.boot") version "3.3.0" }
java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
tasks.test { useJUnitPlatform() }
```

### Dependency Management

| Concern | Approach |
|---------|----------|
| Version alignment | BOM import via `dependencyManagement` / `platform()` |
| Vulnerability scan | OWASP plugin (`dependencyCheckAnalyze`) |
| Unused deps | `mvn dependency:analyze` or Gradle `dependency-analysis` plugin |
| Reproducible builds | Pin plugin versions, `maven-enforcer-plugin` |

---

## Anti-Patterns

| Anti-Pattern | Problem | Solution |
|--------------|---------|----------|
| God service class | 1000+ lines | Split by domain concern |
| Anemic domain model | Logic only in services | Put behavior on domain objects |
| Catching `Exception` | Hides bugs | Catch specific types |
| `@Autowired` on fields | Hidden deps, untestable | Constructor injection |
| Mutable DTOs | Thread-safety issues | Use records |
| Raw JDBC everywhere | Injection risk, boilerplate | JPA/jOOQ with parameterized queries |
| Missing `@Transactional` | Inconsistent data | Annotate service methods |
| N+1 queries | Performance death | `JOIN FETCH` or `@EntityGraph` |
