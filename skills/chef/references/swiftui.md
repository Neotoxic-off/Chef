# SwiftUI

Builds on `swift.md`. Verified against the SwiftLint rule docs (`redundant_void_return`), swift-format `main` rule registry, and Apple's Observation docs (Nov 2026). Current toolchain: `swift --version`; current SwiftLint: its GitHub releases page.

## Lint: house-rule clashes

Both tools strip `-> Void`, which the house rule writes. Turn them off in config, with the reason:

```yaml
# .swiftlint.yml: house rule writes every return type, including Void
disabled_rules:
  - redundant_void_return
```

In `.swift-format` (JSON allows no comments, so state the reason in the PR or a README line), set `"rules": { "NoVoidReturnOnFunctionSignature": false }` next to the rules `swift.md` turns on.

## State and data flow

- Models are `@Observable` classes (Observation, iOS 17 / macOS 14+), `@MainActor` (or the target's default isolation). Use `ObservableObject` / `@Published` only to support older OS versions.
- Ownership: the view that creates a model holds it in `@State`; children receive it as a plain `let` or `@Bindable` when they need bindings; app-wide services go in `@Environment`.
  ```swift
  struct ProfileView: View {
      @State private var model: ProfileModel

      init(service: ProfileService) {
          _model = State(initialValue: ProfileModel(service: service))
      }

      var body: some View {
          Form {
              TextField("Name", text: $model.name)
              Button("Save") { model.save() }
                  .disabled(!model.canSave)
          }
          .task { await model.load() }
      }
  }
  ```
- `@State` is always `private` and holds only state this view owns. Never pass a value in and copy it into `@State`.
- Async work in `.task` / `.task(id:)`: it is cancelled when the view goes away. No `Task {}` in `onAppear`.
- Keep `body` small: extract subviews as separate `View` structs, not computed properties or functions returning `some View`.
- Navigation: `NavigationStack` with a typed path (`[Route]` where `Route: Hashable`) and `navigationDestination(for:)`.
- Layout values (spacing, padding, sizes) are named constants or come from the design system, never literals in modifiers.
- Lists: `ForEach` over `Identifiable` data with stable IDs, never `id: \.self` on values that can repeat.

## Accessibility

- Every icon-only control gets `.accessibilityLabel`. Use system text styles (`.font(.body)`) so Dynamic Type works.
- Group composite rows with `.accessibilityElement(children: .combine)`.

## Previews

- `#Preview` with fake services injected through `init`; previews never hit the network.

## Tests

- Test the `@Observable` models with Swift Testing (`swift.md`); views stay thin, so logic coverage comes from model tests.
- Model tests run on the main actor: mark the suite `@MainActor`.
- UI flows: XCUITest, locating elements by accessibility label or identifier.
- Coverage counts model and service code; exclude view bodies only if the project's coverage config says so, with the reason in that config.
