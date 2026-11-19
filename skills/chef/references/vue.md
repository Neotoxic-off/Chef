# Vue and Nuxt

Builds on `typescript.md`. Verified against Vue 3.5, Nuxt 4.6, Pinia 4.1, vue-tsc 3.3, eslint-plugin-vue 10.12, @vue/eslint-config-typescript 14.9, Vue Test Utils 2.6 (Nov 2026).

## Lint and type check

- Vue: `@vue/eslint-config-typescript` with `withVueTs` (v14.9+). Every `<script>` block must be `lang="ts"`:
  ```js
  import pluginVue from "eslint-plugin-vue";
  import { withVueTs, vueTsConfigs } from "@vue/eslint-config-typescript";

  export default withVueTs(
    pluginVue.configs["flat/recommended"],
    vueTsConfigs.strictTypeChecked,
    vueTsConfigs.stylisticTypeChecked,
  );
  ```
- Nuxt: the `@nuxt/eslint` module generates the config; extend it in `eslint.config.mjs` with `withNuxt(...)` from `./.nuxt/eslint.config.mjs`.
- Type check with `vue-tsc --noEmit` (Nuxt: `nuxt typecheck`). `tsc` alone does not check `.vue` files. Run it in CI.

## Components

- Composition API with `<script setup lang="ts">` only. No Options API, no mixins.
- Type-based macros:
  ```vue
  <script setup lang="ts">
  import { computed } from "vue";

  const props = defineProps<{ readonly user: User }>();
  const emit = defineEmits<{ select: [id: string] }>();
  const model = defineModel<string>({ required: true });
  const label = computed((): string => props.user.name.trim());
  </script>
  ```
- `ref<T>()` with an explicit type argument; `useTemplateRef<T>("name")` for template refs.
- `computed` for derived state, `watch` only for side effects. Never mutate props.
- Reusable logic goes in `use*` composables that return refs, not reactive objects to destructure.
- `v-for` always has a stable `:key`; never `v-if` and `v-for` on the same element.
- No `v-html` with user content.

## State

- Pinia setup stores (Pinia 4 is ESM only):
  ```ts
  export const useCartStore = defineStore("cart", () => {
    const items: Ref<CartItem[]> = ref<CartItem[]>([]);
    const count: ComputedRef<number> = computed((): number => items.value.length);
    return { items, count };
  });
  ```
  Destructure with `storeToRefs(store)` to keep reactivity.
- Nuxt: never create `ref()` at module level, it leaks state across requests on the server. Use `useState` or Pinia (`@pinia/nuxt`).
- Nuxt data fetching: `useFetch` / `useAsyncData` in setup, not bare `$fetch`, so the server result is reused on hydration. Validate responses at the boundary.

## Tests

- Vitest + `@vue/test-utils` `mount`. Interact through the DOM (`await wrapper.get("button").trigger("click")`) and assert on rendered output and emitted events, not on internal state.
- Stores in component tests: `createTestingPinia` from `@pinia/testing`. Test stores directly with `setActivePinia(createPinia())`.
- Nuxt: `@nuxt/test-utils` with `defineVitestProject({ test: { environment: "nuxt" } })` in a Vitest `projects` list; `mountSuspended` for components using auto-imports.
- Playwright for end-to-end.
