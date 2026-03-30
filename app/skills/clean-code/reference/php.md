# PHP Clean Code Patterns

## Configuration

```yaml
# phpstan.neon
parameters:
    level: 8   # max strictness
    paths: [src]
```

## Patterns

```php
// Type declarations (PHP 8+)
function calculatePrice(float $unitPrice, int $quantity): float {
    return $unitPrice * $quantity;
}

// Use enums (PHP 8.1+)
enum UserRole: string {
    case Admin = 'admin';
    case User = 'user';
}

// Follow PSR-12 coding standard
// Use constructor promotion
public function __construct(
    private readonly string $name,
    private readonly string $email,
) {}
```
