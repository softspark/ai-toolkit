---
language: ruby
category: coding-style
version: "1.0.0"
---

# Ruby Coding Style

## Naming
- PascalCase: classes, modules.
- snake_case: methods, variables, file names, directories.
- UPPER_SNAKE: constants (`MAX_RETRIES = 3`).
- Prefix boolean methods with predicate: `empty?`, `valid?`, `admin?`.
- Suffix dangerous methods with `!`: `save!`, `sort!`, `strip!`.
- Use `_` prefix for intentionally unused variables: `_unused`.

## Methods
- Keep methods short: 5-10 lines ideal. Extract helper methods.
- Use keyword arguments for methods with >2 parameters.
- Use default parameter values instead of checking for nil.
- Use `def method_name = expression` (Ruby 3.0+) for one-liners.
- Prefer `each` over `for` loops. Use block-style iteration.
- Return values implicitly (last expression). Use explicit `return` only for early exit.

## Blocks, Procs, Lambdas
- Use `{ }` for single-line blocks. Use `do...end` for multi-line blocks.
- Use `&:method` shorthand: `names.map(&:upcase)`.
- Use lambdas for strict argument checking. Use procs for flexible arity.
- Use `yield` for single-block methods. Use explicit `&block` for storing/forwarding.

## Classes
- Use `attr_reader`, `attr_writer`, `attr_accessor` for simple getters/setters.
- Use `Struct` for simple data containers. Use `Data.define` (Ruby 3.2+) for immutable.
- Use modules for mixins: `include` for instance methods, `extend` for class methods.
- Use `frozen_string_literal: true` magic comment at the top of every file.
- Use `private` / `protected` keywords to control method visibility.

## Collections
- Use `map`, `select`, `reject`, `reduce`, `flat_map` for transformations.
- Use `each_with_object` over `inject` when accumulating into a mutable object.
- Use `dig` for safe nested hash/array access: `data.dig(:user, :address, :city)`.
- Use `Hash#fetch` with default for explicit missing-key handling.
- Use `Enumerable#lazy` for large collection processing.

## Pattern Matching (Ruby 3+)
- Use `case/in` for structural pattern matching on hashes and arrays.
- Use `=>` pin operator to match against existing variables.
- Use `in` pattern for conditional deconstruction in `if` statements.
- Use pattern matching for API response parsing and validation.

## Formatting
- Use RuboCop for automated style enforcement.
- Use `.rubocop.yml` committed to the repository for project conventions.
- Max line length: 120 characters.
- Two-space indentation. No tabs.
- Use trailing commas in multi-line arrays and hashes.
