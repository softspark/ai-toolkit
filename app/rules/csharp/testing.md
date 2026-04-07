---
language: csharp
category: testing
version: "1.0.0"
---

# C# Testing

## Framework
- Use xUnit as the primary test framework (modern, extensible).
- Use NSubstitute for mocking (clean syntax, no setup boilerplate).
- Use FluentAssertions for readable, expressive assertions.
- Use Testcontainers for integration tests with databases and services.

## File Naming
- Test files: `FooTests.cs` in a separate `*.Tests` project.
- Mirror source project namespace structure in test project.
- Integration tests: separate `*.IntegrationTests` project.
- Use `[Collection("Database")]` for shared fixtures across test classes.

## Structure
- Use `[Fact]` for single test cases. Use `[Theory]` for parameterized tests.
- Use `[InlineData]` or `[MemberData]` for test data in theories.
- Use constructor injection for per-test setup. Use `IClassFixture<T>` for shared setup.
- Name tests: `MethodName_Scenario_ExpectedResult`.

## Assertions (FluentAssertions)
- Use `result.Should().Be(expected)` for value assertions.
- Use `action.Should().Throw<InvalidOperationException>()` for exception testing.
- Use `collection.Should().ContainSingle(x => x.Id == 1)` for collection assertions.
- Use `result.Should().BeEquivalentTo(expected)` for deep object comparison.
- Use `execution.Should().CompleteWithinAsync(5.Seconds())` for timeout assertions.

## Mocking (NSubstitute)
- Create mocks: `var repo = Substitute.For<IUserRepository>()`.
- Stub returns: `repo.GetAsync(1).Returns(user)`.
- Verify calls: `repo.Received(1).SaveAsync(Arg.Any<User>())`.
- Use `Arg.Is<T>(predicate)` for argument matching.
- Use `ReturnsForAnyArgs()` for lenient stubs in arrangement-focused tests.

## Integration Testing
- Use `WebApplicationFactory<Program>` for ASP.NET Core integration tests.
- Override services with `WithWebHostBuilder(b => b.ConfigureServices(...))`.
- Use `HttpClient` from factory for endpoint testing.
- Use `Respawn` for database cleanup between tests.
- Use `[Collection]` attribute to prevent parallel execution of shared-resource tests.

## Test Data
- Use Builder pattern for complex test data: `new UserBuilder().WithName("Ada").Build()`.
- Use `AutoFixture` for auto-generated test data.
- Use `Bogus` library for realistic fake data generation.
- Keep test data creation close to the test, not in distant shared files.

## Best Practices
- Test behavior, not implementation. Avoid testing private methods.
- Keep tests independent. No shared mutable state between tests.
- Use `CancellationToken.None` explicitly in async test calls.
- Run tests in CI with `dotnet test --blame-hang-timeout 60s`.
