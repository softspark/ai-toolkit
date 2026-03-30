---
name: csharp-patterns
description: "Loaded when user asks about C# or .NET development patterns"
effort: medium
user-invocable: false
---

# C# / .NET Patterns

## Project Structure

### Solution Layout
```
MyApp.sln
Directory.Build.props              # Shared build properties
Directory.Packages.props           # Central package management
src/
  MyApp.Api/                       # ASP.NET Core host (Controllers, Middleware, Program.cs)
  MyApp.Application/               # Use cases, MediatR handlers, Behaviors
  MyApp.Domain/                    # Entities, value objects, domain events
  MyApp.Infrastructure/            # EF Core, external services
tests/
  MyApp.UnitTests/
  MyApp.IntegrationTests/
```

### Directory.Build.props
```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <EnforceCodeStyleInBuild>true</EnforceCodeStyleInBuild>
    <AnalysisLevel>latest-recommended</AnalysisLevel>
  </PropertyGroup>
</Project>
```

### Central Package Management (Directory.Packages.props)
```xml
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="MediatR" Version="12.4.1" />
    <PackageVersion Include="FluentValidation" Version="11.11.0" />
    <PackageVersion Include="Microsoft.EntityFrameworkCore" Version="9.0.0" />
  </ItemGroup>
</Project>
```

---

## Idioms / Code Style

### Nullable Reference Types
```csharp
public class Order
{
    public required string Id { get; init; }
    public string? Notes { get; set; }               // explicitly nullable
    public required Customer Customer { get; init; }  // never null
    public string Summary => $"Order {Id}: {Notes ?? "no notes"}";
}
```

### Records
```csharp
public record Money(decimal Amount, string Currency)
{
    public Money Add(Money other) => Currency != other.Currency
        ? throw new InvalidOperationException("Currency mismatch")
        : this with { Amount = Amount + other.Amount };
}

public record CreateOrderRequest(string CustomerId, List<OrderLineDto> Lines);
public record OrderLineDto(string ProductId, int Quantity);
```

### Pattern Matching
```csharp
public decimal CalculateDiscount(Customer c) => c switch
{
    { Tier: CustomerTier.Gold, TotalSpent: > 10_000m } => 0.20m,
    { Tier: CustomerTier.Gold }                        => 0.15m,
    { Tier: CustomerTier.Silver }                      => 0.10m,
    { IsNewCustomer: true }                            => 0.05m,
    _                                                  => 0m
};

// List patterns (.NET 8+)
public string Describe(int[] v) => v switch
{
    [] => "empty", [var x] => $"one: {x}", [var f, .., var l] => $"{f}..{l}",
};
```

### LINQ
```csharp
var activeUsers = users
    .Where(u => u.IsActive)
    .OrderByDescending(u => u.LastLogin)
    .Select(u => new UserDto(u.Id, u.Name))
    .ToList();
```

### Async/Await
```csharp
// Always: Async suffix, CancellationToken parameter, never .Result/.Wait()
public async Task<Order?> GetOrderAsync(string id, CancellationToken ct = default)
    => await _db.Orders.Include(o => o.Lines).FirstOrDefaultAsync(o => o.Id == id, ct);

// Parallel independent tasks
var ordersTask = _orderRepo.GetRecentAsync(ct);
var statsTask = _statsService.ComputeAsync(ct);
await Task.WhenAll(ordersTask, statsTask);
```

### Primary Constructors (C# 12)
```csharp
public class OrderService(IOrderRepository repo, ILogger<OrderService> logger, IPublisher pub)
{
    public async Task<Order> CreateAsync(CreateOrderRequest req, CancellationToken ct)
    {
        logger.LogInformation("Creating order for {CustomerId}", req.CustomerId);
        var order = Order.Create(req);
        await repo.AddAsync(order, ct);
        await pub.Publish(new OrderCreatedEvent(order.Id), ct);
        return order;
    }
}
```

---

## Error Handling

### Result Pattern
```csharp
public sealed class Result<T>
{
    public T? Value { get; }
    public Error? Error { get; }
    public bool IsSuccess => Error is null;
    private Result(T value) => Value = value;
    private Result(Error error) => Error = error;
    public static Result<T> Success(T value) => new(value);
    public static Result<T> Failure(Error error) => new(error);
    public TOut Match<TOut>(Func<T, TOut> ok, Func<Error, TOut> err) =>
        IsSuccess ? ok(Value!) : err(Error!);
}
public record Error(string Code, string Message);
```

### FluentValidation + MediatR Pipeline
```csharp
public class CreateOrderValidator : AbstractValidator<CreateOrderRequest>
{
    public CreateOrderValidator()
    {
        RuleFor(x => x.CustomerId).NotEmpty().MaximumLength(36);
        RuleForEach(x => x.Lines).ChildRules(line =>
        {
            line.RuleFor(l => l.ProductId).NotEmpty();
            line.RuleFor(l => l.Quantity).GreaterThan(0).LessThanOrEqualTo(1000);
        });
    }
}

public class ValidationBehavior<TReq, TRes>(IEnumerable<IValidator<TReq>> validators)
    : IPipelineBehavior<TReq, TRes> where TReq : IRequest<TRes>
{
    public async Task<TRes> Handle(TReq req, RequestHandlerDelegate<TRes> next, CancellationToken ct)
    {
        var failures = validators.Select(v => v.Validate(req)).SelectMany(r => r.Errors).ToList();
        return failures.Count > 0 ? throw new ValidationException(failures) : await next();
    }
}
```

### IAsyncDisposable
```csharp
public sealed class TempFileHandle(string path) : IAsyncDisposable
{
    public async ValueTask DisposeAsync()
    {
        if (File.Exists(path)) await Task.Run(() => File.Delete(path));
    }
}
// Usage: await using var handle = new TempFileHandle("/tmp/export.csv");
```

---

## Testing Patterns

### xUnit + NSubstitute + FluentAssertions
```csharp
public class OrderServiceTests
{
    private readonly IOrderRepository _repo = Substitute.For<IOrderRepository>();
    private readonly IPublisher _pub = Substitute.For<IPublisher>();
    private readonly OrderService _sut;
    public OrderServiceTests() => _sut = new(_repo, Substitute.For<ILogger<OrderService>>(), _pub);

    [Fact]
    public async Task CreateAsync_ValidRequest_ReturnsOrder()
    {
        var order = await _sut.CreateAsync(new("cust-1", [new("prod-1", 2)]), CancellationToken.None);
        order.Should().NotBeNull();
        order.Lines.Should().ContainSingle().Which.Quantity.Should().Be(2);
        await _repo.Received(1).AddAsync(Arg.Any<Order>(), Arg.Any<CancellationToken>());
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-1)]
    public async Task CreateAsync_InvalidQuantity_Throws(int qty)
    {
        var act = () => _sut.CreateAsync(new("cust-1", [new("prod-1", qty)]), CancellationToken.None);
        await act.Should().ThrowAsync<ValidationException>();
    }
}
```

### WebApplicationFactory (Integration)
```csharp
public class OrdersApiTests(WebApplicationFactory<Program> factory)
    : IClassFixture<WebApplicationFactory<Program>>
{
    [Fact]
    public async Task PostOrder_Returns201()
    {
        var client = factory.WithWebHostBuilder(b => b.ConfigureServices(s =>
        {
            s.RemoveAll<DbContext>();
            s.AddDbContext<AppDbContext>(o => o.UseInMemoryDatabase("test"));
        })).CreateClient();

        var response = await client.PostAsJsonAsync("/api/orders",
            new { CustomerId = "cust-1", Lines = new[] { new { ProductId = "prod-1", Quantity = 2 } } });
        response.StatusCode.Should().Be(HttpStatusCode.Created);
    }
}
```

### Testcontainers
```csharp
public class PostgresFixture : IAsyncLifetime
{
    private readonly PostgreSqlContainer _pg = new PostgreSqlBuilder().WithDatabase("testdb").Build();
    public string ConnectionString => _pg.GetConnectionString();
    public Task InitializeAsync() => _pg.StartAsync();
    public Task DisposeAsync() => _pg.DisposeAsync().AsTask();
}
```

---

## Common Frameworks

### ASP.NET Core Minimal API
```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(typeof(Program).Assembly));
var app = builder.Build();

app.MapGet("/api/orders/{id}", async (string id, ISender sender, CancellationToken ct) =>
    await sender.Send(new GetOrderQuery(id), ct) is { } order ? Results.Ok(order) : Results.NotFound());

app.MapPost("/api/orders", async (CreateOrderRequest req, ISender sender, CancellationToken ct) =>
    (await sender.Send(new CreateOrderCommand(req), ct)).Match(
        o => Results.Created($"/api/orders/{o.Id}", o),
        e => Results.Problem(e.Message, statusCode: 400)));
app.Run();
```

### Entity Framework Core
```csharp
public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<Order> Orders => Set<Order>();
    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.Entity<Order>(b =>
        {
            b.HasKey(o => o.Id);
            b.Property(o => o.Id).HasMaxLength(36);
            b.HasMany(o => o.Lines).WithOne().HasForeignKey(l => l.OrderId);
            b.HasIndex(o => o.CustomerId);
            b.Property(o => o.Total).HasPrecision(18, 2);
        });
        mb.ApplyConfigurationsFromAssembly(typeof(AppDbContext).Assembly);
    }
}
```

### MediatR (CQRS)
```csharp
public record CreateOrderCommand(CreateOrderRequest Request) : IRequest<Result<Order>>;

public class CreateOrderHandler(IOrderRepository repo, IPublisher pub)
    : IRequestHandler<CreateOrderCommand, Result<Order>>
{
    public async Task<Result<Order>> Handle(CreateOrderCommand cmd, CancellationToken ct)
    {
        var order = Order.Create(cmd.Request);
        await repo.AddAsync(order, ct);
        await pub.Publish(new OrderCreatedEvent(order.Id), ct);
        return Result<Order>.Success(order);
    }
}
```

### Polly (Resilience)
```csharp
builder.Services.AddHttpClient("Payments", c => c.BaseAddress = new Uri("https://api.payments.com"))
.AddResilienceHandler("default", p =>
{
    p.AddRetry(new() { MaxRetryAttempts = 3, Delay = TimeSpan.FromMilliseconds(500),
        BackoffType = DelayBackoffType.Exponential,
        ShouldHandle = new PredicateBuilder<HttpResponseMessage>()
            .HandleResult(r => r.StatusCode >= HttpStatusCode.InternalServerError) });
    p.AddCircuitBreaker(new() { FailureRatio = 0.5, SamplingDuration = TimeSpan.FromSeconds(30),
        BreakDuration = TimeSpan.FromSeconds(15) });
    p.AddTimeout(TimeSpan.FromSeconds(5));
});
```

### MassTransit (Messaging)
```csharp
builder.Services.AddMassTransit(x =>
{
    x.AddConsumer<OrderCreatedConsumer>();
    x.UsingRabbitMq((ctx, cfg) => { cfg.Host("rabbitmq://localhost"); cfg.ConfigureEndpoints(ctx); });
});
```

---

## Performance Tips

### Span<T> -- Zero-Allocation Parsing
```csharp
public static ReadOnlySpan<char> ExtractDomain(ReadOnlySpan<char> email)
{
    int at = email.IndexOf('@');
    return at >= 0 ? email[(at + 1)..] : ReadOnlySpan<char>.Empty;
}
// Stack-allocated buffer: Span<byte> buf = stackalloc byte[256];
```

### ValueTask -- Cache-Hit Fast Path
```csharp
public ValueTask<Product?> GetProductAsync(string id, CancellationToken ct)
{
    if (_cache.TryGetValue(id, out var cached)) return ValueTask.FromResult<Product?>(cached);
    return new ValueTask<Product?>(LoadFromDbAsync(id, ct));
}
```

### Source Generators
```csharp
// JSON -- avoids runtime reflection
[JsonSerializable(typeof(Order))]
[JsonSourceGenerationOptions(PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase)]
public partial class AppJsonContext : JsonSerializerContext;

// Logging -- avoids boxing
public static partial class Log
{
    [LoggerMessage(Level = LogLevel.Information, Message = "Order {OrderId} created")]
    public static partial void OrderCreated(ILogger logger, string orderId);
}
```

### BenchmarkDotNet
```csharp
[MemoryDiagnoser, SimpleJob(RuntimeMoniker.Net90)]
public class ParsingBenchmarks
{
    private readonly string _email = "user@example.com";
    [Benchmark(Baseline = true)] public string Sub() => _email[(_email.IndexOf('@') + 1)..];
    [Benchmark] public ReadOnlySpan<char> Span() => ExtractDomain(_email.AsSpan());
}
// dotnet run -c Release --project Benchmarks
```

---

## Build / Package Management

### dotnet CLI
```bash
dotnet new sln -n MyApp && dotnet new webapi -n MyApp.Api -o src/MyApp.Api
dotnet build -c Release
dotnet test -c Release --collect:"XPlat Code Coverage"
dotnet publish src/MyApp.Api -c Release -o ./publish
dotnet ef migrations add Init --project src/MyApp.Infrastructure --startup-project src/MyApp.Api
```

### .editorconfig
```ini
[*.cs]
dotnet_sort_system_directives_first = true
csharp_style_namespace_declarations = file_scoped:error
csharp_prefer_primary_constructors = true:suggestion
dotnet_diagnostic.CA1848.severity = warning
```

### CI (GitHub Actions)
```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-dotnet@v4
    with: { dotnet-version: '9.0.x' }
  - run: dotnet restore
  - run: dotnet build --no-restore -c Release -warnaserror
  - run: dotnet test --no-build -c Release --collect:"XPlat Code Coverage"
  - run: dotnet publish src/MyApp.Api -c Release -o publish --no-build
```

### Dockerfile
```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src
COPY . .
RUN dotnet publish src/MyApp.Api -c Release -o /app
FROM mcr.microsoft.com/dotnet/aspnet:9.0
COPY --from=build /app /app
WORKDIR /app
ENTRYPOINT ["dotnet", "MyApp.Api.dll"]
```

---

## Anti-Patterns
- `async void` outside event handlers -- always return `Task`
- Blocking with `.Result` / `.Wait()` -- deadlock risk
- Missing `CancellationToken` propagation through the call chain
- Catching bare `Exception` without re-throw or structured logging
- Service locator via `IServiceProvider.GetService` in business logic
- Exposing `IQueryable` from repositories -- leaks persistence details
- Public setters on domain entities -- use methods + private setters
- String concatenation in hot paths -- use `StringBuilder` or string handlers
