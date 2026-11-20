# React Native (Expo)

Builds on `typescript.md` and `react.md`. Written for Expo SDK 58, React Native 0.88, jest-expo 58, eslint-config-expo 58, @testing-library/react-native 14.1 (Nov 2026), not benchmarked. Current versions: `npm view expo version`; let `npx expo install` pick every SDK-bound package.

## Project and dependencies

- Expo with Continuous Native Generation: native changes go through `app.config.ts` and config plugins, not hand edits in `ios/` and `android/`. Do not commit those folders unless the project already does.
- Add packages with `npx expo install <pkg>`, never a bare `npm install` for native modules: it pins the version the SDK supports. CI runs `npx expo install --check` and `npx expo-doctor`.
- Check a library supports the New Architecture (reactnative.directory) before proposing it.

## Lint and config

- Add Expo's flat preset to the config from `typescript.md` (keep typescript-eslint and the React hooks plugin from `react.md`):
  ```js
  const expoConfig = require("eslint-config-expo/flat");

  module.exports = defineConfig([globalIgnores(["dist/*"]), expoConfig /* , typescript.md + react.md configs */]);
  ```
- Run it with `npx expo lint`. Type-check with `npx tsc --noEmit`.
- Expo Router: turn on typed routes so a wrong `href` fails the type check (`"experiments": { "typedRoutes": true }` in `app.json`, then `npx expo customize tsconfig.json`). Still marked beta in the docs.

## Code

- Components follow `react.md`. Styles in `StyleSheet.create`, values from named theme tokens, never raw numbers:
  ```tsx
  const styles: { readonly button: ViewStyle } = StyleSheet.create({ button: { padding: spacing.medium } });

  export function SaveButton({ onPress, disabled }: SaveButtonProps): React.JSX.Element {
    return (
      <Pressable accessibilityRole="button" accessibilityState={{ disabled }} disabled={disabled} onPress={onPress} style={styles.button}>
        <Text>Save</Text>
      </Pressable>
    );
  }
  ```
- Long lists: `FlatList` (or FlashList if the project has it) with a `keyExtractor` from the data, never `map` inside a `ScrollView`.
- Platform differences in `Platform.select` or `.ios.tsx` / `.android.tsx` files, not scattered `if (Platform.OS ...)`.
- Every touchable has `accessibilityRole` and, when it shows only an icon, `accessibilityLabel`.

## Secrets and data

- `EXPO_PUBLIC_*` variables are inlined in the bundle in plain text: never put a key or secret there. Secrets stay on a server.
- Tokens on the device: `expo-secure-store`, never AsyncStorage.
- Validate every API response with zod at the boundary (`typescript.md`), then trust the type.

## Tests

- Jest with the `jest-expo` preset (Expo's documented setup; it mocks the native side) and React Native Testing Library 14+, which Expo Router tests require. Install both with `npx expo install --dev`.
- Query by role and label (`getByRole("button", { name: "Save" })`), interact through `userEvent`. Routes: `renderRouter` from `expo-router/testing-library`.
- Coverage gate in the Jest config:
  ```json
  "jest": { "preset": "jest-expo", "coverageThreshold": { "global": { "lines": 90, "branches": 90, "functions": 90, "statements": 90 } } }
  ```
- End-to-end on a device or emulator: Maestro flows (Expo's EAS Workflows run them). Not verified here: pick it only after checking the project's CI.

Order before done: `npx expo lint` then `npx tsc --noEmit` then `npx jest --coverage` then `npx expo-doctor`.
