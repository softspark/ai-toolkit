# Dart/Flutter Clean Code Patterns

## Patterns

```dart
// Use dart analyze with strict rules
// analysis_options.yaml: include: package:lints/recommended.yaml

// Null safety
String? getName() => _name;  // nullable return
final name = getName() ?? 'default';  // null coalescing

// Named parameters for clarity
Widget buildCard({required String title, String? subtitle, VoidCallback? onTap}) { ... }

// Use const constructors
const EdgeInsets.all(16.0)
```
