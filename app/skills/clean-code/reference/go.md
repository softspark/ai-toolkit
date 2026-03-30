# Go Clean Code Patterns

## Patterns

```go
// Use gofmt (automatic), go vet, golangci-lint
// Error handling - always check errors
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// Use meaningful receiver names (not `this` or `self`)
func (s *Service) Search(query string) ([]Result, error) { ... }

// Return early to avoid deep nesting
func validate(input string) error {
    if input == "" {
        return errors.New("input cannot be empty")
    }
    // ... continue with valid input
}
```
