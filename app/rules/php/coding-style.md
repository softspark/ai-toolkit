---
language: php
category: coding-style
version: "1.0.0"
---

# PHP Coding Style

## Standards
- Follow PSR-12 extended coding style.
- Use `declare(strict_types=1)` at the top of every file.
- Use PHP 8.1+ features: enums, fibers, readonly properties, intersection types.
- Use PHP CS Fixer or Pint for automated formatting.

## Naming
- PascalCase: classes, interfaces, traits, enums.
- camelCase: methods, functions, variables.
- UPPER_SNAKE: class constants (`public const MAX_RETRIES = 3`).
- snake_case: not used for methods. PSR convention is camelCase.
- Suffix interfaces with `Interface` or prefix with contract name (project convention).

## Type System
- Use typed properties: `private readonly string $name;`.
- Use union types: `string|int`. Use intersection types: `Countable&Iterator`.
- Use `enum` (PHP 8.1) for fixed sets of values. Use backed enums for persistence.
- Use `readonly` classes (PHP 8.2) for immutable DTOs.
- Use constructor promotion: `public function __construct(private string $name)`.
- Use `never` return type for functions that throw or exit.

## Functions
- Use typed parameters and return types on all functions/methods.
- Use named arguments for readability: `new User(name: 'Ada', age: 36)`.
- Use null-safe operator: `$user?->address?->city`.
- Use match expression over switch for value mapping.
- Use first-class callable syntax: `array_map($this->transform(...), $items)`.

## Imports and Namespaces
- Use PSR-4 autoloading via Composer.
- Group `use` statements: classes, functions, constants.
- Never use `require`/`include` for class loading. Use Composer autoloader.
- Use one class per file. File name matches class name.

## Error Handling
- Use exceptions for error conditions. Never return error codes.
- Create domain exception hierarchies extending `RuntimeException` or `LogicException`.
- Use `match` with `throw` for exhaustive error mapping.
- Log exceptions with context using PSR-3 logger.

## Configuration
- Use PHPStan at level 8+ for static analysis.
- Use Rector for automated code upgrades and refactoring.
- Use `.php-cs-fixer.dist.php` for formatting rules.
- Run `composer analyse` (PHPStan) and `composer format` (Pint) in CI.
