---
language: java
category: testing
version: "1.0.0"
---

# Java Testing

## Framework
- Use JUnit 5 (Jupiter) for all new tests. No JUnit 4.
- Use AssertJ for fluent, readable assertions.
- Use Mockito for mocking dependencies.
- Use Testcontainers for integration tests with databases/services.

## File Naming
- Test classes: `FooTest.java` in `src/test/java/` mirroring source package.
- Integration tests: `FooIT.java` or use `@Tag("integration")`.
- Test utilities: `src/test/java/.../support/` or `TestUtils.java`.

## Structure
- Use `@Nested` classes to group related tests within a test class.
- Use `@DisplayName` for human-readable test descriptions.
- Use `@BeforeEach` for setup, `@AfterEach` for cleanup.
- Use `@ParameterizedTest` with `@ValueSource`, `@CsvSource`, `@MethodSource`.

## Assertions (AssertJ)
- Use `assertThat(actual).isEqualTo(expected)` over JUnit assertions.
- Use `assertThatThrownBy(() -> ...).isInstanceOf(FooException.class)`.
- Use `assertThat(list).hasSize(3).extracting("name").contains("Ada")`.
- Chain assertions for readable, self-documenting tests.

## Mocking (Mockito)
- Use `@Mock` + `@ExtendWith(MockitoExtension.class)` for injection.
- Use `when().thenReturn()` for stubbing. `verify()` for interaction checking.
- Use `@InjectMocks` to auto-inject mocks into the class under test.
- Prefer constructor injection in production code for testability.
- Use `ArgumentCaptor` to inspect complex arguments.

## Integration Testing
- Use Testcontainers for PostgreSQL, Redis, Kafka, etc.
- Use `@SpringBootTest` sparingly -- it starts the full context. Prefer slices.
- Use `@WebMvcTest` for controller tests, `@DataJpaTest` for repository tests.
- Use `@TestConfiguration` for test-specific bean overrides.

## Test Data
- Use test builders or factory methods for creating test objects.
- Use `@Sql` annotation to load test data from SQL files.
- Keep test data minimal. Only set fields relevant to the behavior under test.
- Use random UUIDs for IDs in tests to avoid collision.

## Performance
- Run tests in parallel: configure `junit.jupiter.execution.parallel.enabled=true`.
- Use `@SpringBootTest` only when integration context is needed.
- Mock external dependencies in unit tests for speed.
- Keep the full test suite under 5 minutes.
