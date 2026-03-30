# Go Testing Patterns

## Table-Driven Tests

```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 1, 2, 3},
        {"negative", -1, -2, -3},
        {"zero", 0, 0, 0},
    }
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d, want %d", tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

## Mocking (testify)

```go
type MockRepo struct { mock.Mock }
func (m *MockRepo) Find(id string) (*User, error) {
    args := m.Called(id)
    return args.Get(0).(*User), args.Error(1)
}

func TestService(t *testing.T) {
    repo := new(MockRepo)
    repo.On("Find", "1").Return(&User{Name: "Test"}, nil)
    svc := NewService(repo)
    user, _ := svc.GetUser("1")
    assert.Equal(t, "Test", user.Name)
}
```

## Running

```bash
go test ./...                  # All tests
go test -cover ./...           # With coverage
go test -run TestAdd ./pkg/    # Specific test
go test -v ./...               # Verbose
```
