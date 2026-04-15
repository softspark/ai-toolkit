# Mobile Accessibility — EN 301 549 & EAA

Reference for `a11y-validate` Category 8d. Platform a11y APIs and cross-platform framework patterns (React Native, Flutter).

**EAA scope includes consumer mobile apps** (Article 2(2) — electronic communications, banking, e-commerce, transport). EN 301 549 Chapter 11 covers software / native apps.

## Platform APIs

### iOS — UIAccessibility (UIKit/SwiftUI)

Core properties on `UIView` / `UIAccessibilityElement`:

- `isAccessibilityElement: Bool` — is this an atomic element for VoiceOver?
- `accessibilityLabel: String?` — concise name.
- `accessibilityValue: String?` — current value (for sliders, inputs).
- `accessibilityHint: String?` — what happens on activation.
- `accessibilityTraits: UIAccessibilityTraits` — button, link, header, selected, adjustable, etc.
- `accessibilityIdentifier: String?` — for UI testing (not user-facing).

SwiftUI modifiers:
- `.accessibilityLabel(_:)`
- `.accessibilityValue(_:)`
- `.accessibilityHint(_:)`
- `.accessibilityAddTraits(_:)` / `.accessibilityRemoveTraits(_:)`
- `.accessibilityElement(children:)`
- `.accessibilityHidden(_:)`

### Android — AccessibilityNodeInfo

Core XML attributes:
- `android:contentDescription` — equivalent to `accessibilityLabel`.
- `android:labelFor` — for inputs.
- `android:importantForAccessibility` — yes / no / auto / noHideDescendants.
- `android:accessibilityHeading` — heading level.
- `android:screenReaderFocusable` — focusable by TalkBack.
- `android:accessibilityLiveRegion` — none / polite / assertive.

Jetpack Compose modifiers:
- `Modifier.semantics { contentDescription = "..." }`
- `Modifier.clearAndSetSemantics { ... }`
- `Modifier.semantics(mergeDescendants = true) { ... }`

## React Native

```jsx
import { TouchableOpacity, Pressable, Text, Image, AccessibilityInfo } from 'react-native';

// Button equivalent
<TouchableOpacity
  accessible={true}
  accessibilityRole="button"
  accessibilityLabel="Submit form"
  accessibilityHint="Sends your data for processing"
  accessibilityState={{ disabled: loading, busy: submitting }}
  onPress={handleSubmit}
>
  <Text>Submit</Text>
</TouchableOpacity>

// Image with a11y
<Image
  source={require('./photo.jpg')}
  accessible={true}
  accessibilityLabel="Team photo from 2025 conference"
/>

// Decorative image — hide from AT
<Image
  source={require('./decorative-pattern.jpg')}
  accessibilityElementsHidden={true}
  importantForAccessibility="no"
/>

// Announce dynamic change
AccessibilityInfo.announceForAccessibility('Item added to cart');

// Check if screen reader is active
const isEnabled = await AccessibilityInfo.isScreenReaderEnabled();
```

Common React Native a11y props:
- `accessible` — whether element is a11y element (default: true for Text, Image, TouchableOpacity).
- `accessibilityLabel` — required on all interactive elements without visible text.
- `accessibilityHint` — what happens on activation.
- `accessibilityRole` — button / link / image / header / adjustable / summary / alert / checkbox / radio / togglebutton / tab / tablist / search / combobox / menu / menuitem / menubar / progressbar / radiogroup / scrollbar / spinbutton / switch / timer / toolbar.
- `accessibilityState` — `{ disabled, selected, checked, busy, expanded }`.
- `accessibilityValue` — `{ min, max, now, text }` for sliders/progress.
- `accessibilityLiveRegion` (Android) / `accessibilityElementsHidden` (iOS) — live updates.
- `onAccessibilityTap` — alt handler for VoiceOver double-tap.
- `onMagicTap` — iOS double-tap with two fingers.

### Common RN a11y violations (flagged by Category 8d)

```jsx
// Bad — no accessibilityLabel
<TouchableOpacity onPress={close}>
  <Icon name="close" />
</TouchableOpacity>

// Good
<TouchableOpacity
  onPress={close}
  accessibilityRole="button"
  accessibilityLabel="Close dialog"
>
  <Icon name="close" accessibilityElementsHidden importantForAccessibility="no" />
</TouchableOpacity>
```

```jsx
// Bad — decorative image announced by TalkBack
<Image source={require('./pattern.png')} />

// Good
<Image
  source={require('./pattern.png')}
  accessibilityElementsHidden={true}
  importantForAccessibility="no"
/>
```

### Key RN a11y libraries

- `@react-native-community/hooks` — `useAccessibilityInfo()`.
- `react-native-reanimated` — respects `reduceMotion` via `useReducedMotion()`.
- `@testing-library/react-native` — has `getByRole`, `getByA11yLabel` queries for testing.

### Testing

- **iOS**: Xcode Accessibility Inspector (⌥⌘8 in Simulator).
- **Android**: Accessibility Scanner app + TalkBack.
- **Automated**: Lighthouse for WebView content; platform-specific tools for native.

## Flutter

```dart
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

// Button with semantics
Semantics(
  label: 'Submit form',
  hint: 'Sends your data for processing',
  button: true,
  enabled: !loading,
  child: GestureDetector(
    onTap: handleSubmit,
    child: Container(
      child: Text('Submit'),
    ),
  ),
)

// Simpler for standard widgets — most have built-in semantics
ElevatedButton(
  onPressed: handleSubmit,
  child: Text('Submit'),  // Text becomes accessible name automatically
)

// Icon-only button (needs explicit label)
IconButton(
  icon: Icon(Icons.close),
  onPressed: close,
  tooltip: 'Close',  // Tooltip doubles as accessibility label
)

// Image with a11y
Image.asset(
  'assets/team.jpg',
  semanticLabel: 'Team photo from 2025 conference',
)

// Decorative image — exclude from semantics tree
Image.asset(
  'assets/pattern.jpg',
  excludeFromSemantics: true,
)

// Announce dynamic change
SemanticsService.announce('Item added to cart', TextDirection.ltr);

// Merge child semantics into one (for grouped interactive elements)
MergeSemantics(
  child: Row(
    children: [
      Checkbox(value: isChecked, onChanged: setChecked),
      Text('Agree to terms'),
    ],
  ),
)

// Exclude interactive semantics from child
ExcludeSemantics(
  child: AnimatedIcon(...),  // purely decorative
)
```

Key Flutter semantic properties:
- `label` — accessible name.
- `hint` — action hint.
- `value` — current value (slider / input).
- `increasedValue` / `decreasedValue` — for adjustable widgets.
- `button` / `link` / `header` / `textField` / `checked` / `selected` — role booleans.
- `enabled` / `focused` / `focusable` — state.
- `image` — is an image (for decorative vs. informative).
- `liveRegion` — announce changes.
- `hidden` — excluded from a11y tree (different from `excludeFromSemantics` which merges up).

### Common Flutter a11y violations (flagged)

```dart
// Bad — GestureDetector with no semantics
GestureDetector(
  onTap: close,
  child: Icon(Icons.close),
)

// Good
Semantics(
  label: 'Close dialog',
  button: true,
  child: GestureDetector(
    onTap: close,
    child: Icon(Icons.close),
  ),
)

// Or use IconButton which has built-in semantics
IconButton(
  icon: Icon(Icons.close),
  onPressed: close,
  tooltip: 'Close dialog',
)
```

```dart
// Bad — Image without label
Image.network('https://example.com/product.jpg')

// Good
Image.network(
  'https://example.com/product.jpg',
  semanticLabel: 'Red leather handbag, size medium',
)
```

### Flutter a11y testing

- `flutter test --tags accessibility` with `SemanticsTester`.
- `flutter_driver` with `SerializableFinder.bySemanticsLabel(...)`.
- Accessibility Inspector on iOS simulator / Accessibility Scanner on Android.

## Cross-Platform Patterns

### Reduced motion

**React Native**:
```jsx
import { useReducedMotion } from 'react-native-reanimated';

const reducedMotion = useReducedMotion();
const duration = reducedMotion ? 0 : 300;
```

**Flutter**:
```dart
final reduceMotion = MediaQuery.of(context).disableAnimations;
final duration = reduceMotion ? Duration.zero : Duration(milliseconds: 300);
```

### Font scaling

**React Native**: text scales with system font size by default. Set `allowFontScaling={false}` only with explicit reason (often inappropriate — WCAG 1.4.4).

**Flutter**: `MediaQuery.of(context).textScaler` (replaces `textScaleFactor` in Flutter 3.16+). Use `Text(..., textScaler: MediaQuery.textScalerOf(context))` explicitly or rely on default inheritance.

### Contrast mode

**iOS**: `UIAccessibilityDarkerSystemColorsEnabled` / `accessibilityContrastChanged` notification.

**Android**: `AccessibilityManager.isHighTextContrastEnabled()`.

**React Native**: `AccessibilityInfo.isHighTextContrastEnabled()` (Android only) / check `useColorScheme()` + manual high-contrast theme.

**Flutter**: `MediaQuery.of(context).highContrast`.

### Screen reader detection

**React Native**:
```jsx
AccessibilityInfo.isScreenReaderEnabled().then(enabled => { ... });
AccessibilityInfo.addEventListener('screenReaderChanged', handler);
```

**Flutter**:
```dart
MediaQuery.of(context).accessibleNavigation  // true if TalkBack/VoiceOver active
```

## EN 301 549 Mobile Chapter 11 — Key Clauses

Maps WCAG criteria to native software context:

| Clause | WCAG | Implementation |
|--------|------|----------------|
| 11.1.1.1 | 1.1.1 | All non-text content has text alternative |
| 11.1.2.1 | 1.2.1 | Prerecorded audio/video alternatives |
| 11.1.2.2 | 1.2.2 | Captions for prerecorded video |
| 11.1.3.1 | 1.3.1 | Info and relationships via accessibility API |
| 11.1.3.2 | 1.3.2 | Meaningful sequence exposed to AT |
| 11.1.4.1 | 1.4.1 | No color-only signalling |
| 11.1.4.2 | 1.4.2 | Audio control |
| 11.1.4.3 | 1.4.3 | Contrast minimum (4.5:1) |
| 11.1.4.4 | 1.4.4 | Text resize to 200% without loss |
| 11.2.1.1 | 2.1.1 | All functionality keyboard-accessible (external keyboard) |
| 11.2.1.2 | 2.1.2 | No keyboard trap |
| 11.2.2.1 | 2.2.1 | Timing adjustable |
| 11.4.1.1 | 4.1.1 | Parsing (platform UI tree correctness) |
| 11.4.1.2 | 4.1.2 | Name, role, value exposed to AT |

## References

- Apple Accessibility (iOS): https://developer.apple.com/accessibility/ios/
- Android Accessibility: https://developer.android.com/guide/topics/ui/accessibility
- React Native A11y API: https://reactnative.dev/docs/accessibility
- Flutter Semantics: https://api.flutter.dev/flutter/widgets/Semantics-class.html
- Flutter Accessibility guide: https://docs.flutter.dev/ui/accessibility-and-internationalization/accessibility
- EN 301 549 v3.2.1: https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- Mobile a11y best practices (BBC): https://www.bbc.co.uk/accessibility/forproducts/mobile/
