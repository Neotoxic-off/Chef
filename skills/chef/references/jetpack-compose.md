# Jetpack Compose

Builds on `kotlin.md`. Verified against Compose BOM 2026.09.00, slack compose-lint-checks 1.6.1, ktlint 1.x rules docs, detekt 1.23.8 (Nov 2026). Current BOM: the "BOM to library version mapping" page on developer.android.com; current lint checks: `maven-metadata.xml` of `com.slack.lint.compose:compose-lint-checks` on Maven Central.

## Build and lint

```kotlin
plugins { alias(libs.plugins.kotlin.compose) }  // org.jetbrains.kotlin.plugin.compose, same version as Kotlin

dependencies {
    val composeBom: Dependency = platform(libs.androidx.compose.bom)
    implementation(composeBom)
    androidTestImplementation(composeBom)
    lintChecks(libs.compose.lint.checks)  // com.slack.lint.compose:compose-lint-checks
}
```

- Versions only through the BOM; override one library only with a reason.
- Android Lint gates warnings as errors (`kotlin.md`); the Compose lint checks run inside it.
- House-rule clashes, fixed in config with the reason on the line:
  ```ini
  # .editorconfig: house rule writes every return type, including Unit
  ktlint_standard_no-unit-return = disabled
  ```
  ```yaml
  # config/detekt.yml: composables are PascalCase by Compose convention
  naming:
    FunctionNaming:
      ignoreAnnotated: ['Composable']
  ```
- Leave detekt `OptionalUnit` off (its default).

## Code

- State hoisting: a stateful route reads the ViewModel; a stateless screen takes state and callbacks. Only the screen is previewed and tested.
  ```kotlin
  @Composable
  fun ProfileRoute(viewModel: ProfileViewModel, modifier: Modifier = Modifier): Unit {
      val state: ProfileUiState by viewModel.uiState.collectAsStateWithLifecycle()
      ProfileScreen(state = state, onSave = viewModel::save, modifier = modifier)
  }
  ```
- Every public composable that emits UI takes `modifier: Modifier = Modifier` as its first optional parameter and applies it to the root only.
- Collect flows with `collectAsStateWithLifecycle()`, not `collectAsState()`.
- Local state: `var name: String by rememberSaveable { mutableStateOf("") }` when it must survive rotation and process death.
- Side effects only in `LaunchedEffect` / `DisposableEffect` keyed on what they read; never launch work from the composable body.
- UI state is immutable: `data class` or `sealed interface`, read-only collections (`kotlinx.collections.immutable` if the project has it).
- Strong skipping is on by default since Kotlin 2.0.20: do not add `@Stable`/`@Immutable` or `remember` around lambdas without a measured recomposition problem (Layout Inspector counts).
- Sizes and colors from `MaterialTheme` and named `Dp` constants, never inline literals.
- Accessibility: `contentDescription` on every meaningful icon (`null` only for decorative ones); merge semantics for clickable rows.

## Tests

- ViewModels: local JVM tests with `runTest` and a test dispatcher (`kotlin.md`).
- UI: Compose UI test against the stateless screen, find nodes by text, content description or semantics, not by test tags unless there is no other handle:
  ```kotlin
  @get:Rule
  val composeTestRule: ComposeContentTestRule = createComposeRule()

  @Test
  fun saveButton_whenNameBlank_isDisabled(): Unit {
      composeTestRule.setContent { ProfileScreen(state = ProfileUiState(name = ""), onSave = {}) }
      composeTestRule.onNodeWithText("Save").assertIsNotEnabled()
  }
  ```
- Test names: backticked sentences in local tests; in instrumented tests use `subject_condition_result`, because Android runs names with spaces only from API 30.
- Run Compose UI tests on the JVM with Robolectric where possible; keep instrumented runs for flows that need a device.
