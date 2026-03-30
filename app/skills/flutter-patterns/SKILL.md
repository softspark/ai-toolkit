---
name: flutter-patterns
description: "Loaded when user asks about Flutter or Dart development patterns"
effort: medium
user-invocable: false
---

# Flutter Patterns Skill

## Project Structure

```
lib/
├── main.dart
├── app.dart
├── core/
│   ├── constants/
│   ├── errors/
│   ├── network/
│   └── utils/
├── features/
│   └── feature_name/
│       ├── data/
│       │   ├── models/
│       │   ├── repositories/
│       │   └── sources/
│       ├── domain/
│       │   ├── entities/
│       │   └── usecases/
│       └── presentation/
│           ├── bloc/
│           ├── pages/
│           └── widgets/
└── shared/
    ├── widgets/
    └── theme/
```

---

## State Management

### BLoC Pattern
```dart
// Event
abstract class AuthEvent {}
class LoginRequested extends AuthEvent {
  final String email;
  final String password;
  LoginRequested(this.email, this.password);
}

// State
abstract class AuthState {}
class AuthInitial extends AuthState {}
class AuthLoading extends AuthState {}
class AuthSuccess extends AuthState {
  final User user;
  AuthSuccess(this.user);
}
class AuthFailure extends AuthState {
  final String message;
  AuthFailure(this.message);
}

// BLoC
class AuthBloc extends Bloc<AuthEvent, AuthState> {
  AuthBloc() : super(AuthInitial()) {
    on<LoginRequested>(_onLoginRequested);
  }

  Future<void> _onLoginRequested(
    LoginRequested event,
    Emitter<AuthState> emit,
  ) async {
    emit(AuthLoading());
    try {
      final user = await authRepository.login(event.email, event.password);
      emit(AuthSuccess(user));
    } catch (e) {
      emit(AuthFailure(e.toString()));
    }
  }
}
```

### Riverpod
```dart
final userProvider = FutureProvider<User>((ref) async {
  final repository = ref.watch(userRepositoryProvider);
  return repository.getUser();
});

// Usage
Consumer(
  builder: (context, ref, child) {
    final userAsync = ref.watch(userProvider);
    return userAsync.when(
      data: (user) => Text(user.name),
      loading: () => CircularProgressIndicator(),
      error: (e, s) => Text('Error: $e'),
    );
  },
)
```

---

## Navigation (GoRouter)

```dart
final router = GoRouter(
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => HomeScreen(),
      routes: [
        GoRoute(
          path: 'details/:id',
          builder: (context, state) => DetailsScreen(
            id: state.pathParameters['id']!,
          ),
        ),
      ],
    ),
  ],
);

// Navigation
context.go('/details/123');
context.push('/details/123');
context.pop();
```

---

## Widget Patterns

### Responsive Layout
```dart
class ResponsiveLayout extends StatelessWidget {
  final Widget mobile;
  final Widget? tablet;
  final Widget desktop;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 600) {
          return mobile;
        } else if (constraints.maxWidth < 1200) {
          return tablet ?? desktop;
        }
        return desktop;
      },
    );
  }
}
```

### Sliver Patterns
```dart
CustomScrollView(
  slivers: [
    SliverAppBar(
      floating: true,
      title: Text('Title'),
    ),
    SliverPadding(
      padding: EdgeInsets.all(16),
      sliver: SliverList(
        delegate: SliverChildBuilderDelegate(
          (context, index) => ListTile(title: Text('Item $index')),
          childCount: 100,
        ),
      ),
    ),
  ],
)
```

---

## Performance

### const Constructors
```dart
// Good
const Text('Hello');
const SizedBox(height: 8);

// Widget with const constructor
class MyWidget extends StatelessWidget {
  const MyWidget({super.key});
}
```

### RepaintBoundary
```dart
RepaintBoundary(
  child: ComplexAnimatedWidget(),
)
```

### Image Optimization
```dart
Image.network(
  url,
  cacheWidth: 200,  // Resize in memory
  cacheHeight: 200,
)
```

---

## Testing

### Widget Testing
```dart
testWidgets('Counter increments', (tester) async {
  await tester.pumpWidget(MyApp());

  expect(find.text('0'), findsOneWidget);

  await tester.tap(find.byIcon(Icons.add));
  await tester.pump();

  expect(find.text('1'), findsOneWidget);
});
```

### BLoC Testing
```dart
blocTest<AuthBloc, AuthState>(
  'emits [loading, success] when login succeeds',
  build: () => AuthBloc(),
  act: (bloc) => bloc.add(LoginRequested('email', 'pass')),
  expect: () => [AuthLoading(), isA<AuthSuccess>()],
);
```

---

## Best Practices

- ✅ Use const constructors
- ✅ Extract widgets to separate files
- ✅ Use named routes
- ✅ Implement proper error handling
- ✅ Use proper state management
- ❌ Avoid setState for complex state
- ❌ Don't nest too many widgets
- ❌ Avoid magic numbers
