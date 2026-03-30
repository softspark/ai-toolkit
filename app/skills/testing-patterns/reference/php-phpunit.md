# PHP PHPUnit Patterns

## Basic Test

```php
class UserServiceTest extends TestCase
{
    public function test_creates_user_with_valid_data(): void
    {
        $service = new UserService();
        $user = $service->create(['name' => 'Test', 'email' => 't@t.com']);
        $this->assertEquals('Test', $user->name);
    }

    public function test_throws_on_invalid_email(): void
    {
        $this->expectException(ValidationException::class);
        $service = new UserService();
        $service->create(['name' => 'Test', 'email' => 'invalid']);
    }
}
```

## Mocking

```php
$mock = $this->createMock(Repository::class);
$mock->method('find')->willReturn(new User('Test'));
$service = new UserService($mock);
```

## Running

```bash
./vendor/bin/phpunit                          # All tests
./vendor/bin/phpunit --coverage-text          # With coverage
./vendor/bin/phpunit tests/Unit/UserTest.php  # Specific file
./vendor/bin/phpunit --filter testName        # Pattern match
```
