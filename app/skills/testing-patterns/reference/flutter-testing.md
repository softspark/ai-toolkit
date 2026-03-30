# Flutter/Dart Testing Patterns

## Widget Test

```dart
testWidgets('Counter increments', (WidgetTester tester) async {
  await tester.pumpWidget(const MyApp());
  expect(find.text('0'), findsOneWidget);
  await tester.tap(find.byIcon(Icons.add));
  await tester.pump();
  expect(find.text('1'), findsOneWidget);
});
```

## Unit Test

```dart
test('User model parses JSON', () {
  final json = {'name': 'Test', 'email': 'test@test.com'};
  final user = User.fromJson(json);
  expect(user.name, equals('Test'));
  expect(user.email, equals('test@test.com'));
});
```

## Running

```bash
flutter test                          # All tests
flutter test --coverage               # With coverage
flutter test test/widget_test.dart    # Specific file
dart test --name="pattern"            # Pattern match
```
