# Angular

Builds on `typescript.md`. Written for Angular 22.3, angular-eslint 22.8 (Nov 2026), not benchmarked.

## Setup

- New projects: `ng new` (standalone components, zoneless change detection and Vitest are the defaults). Add lint with `ng add angular-eslint --tseslint-preset=strictTypeChecked`.
- `tsconfig.json`: keep the strict compiler options and set them explicitly:
  ```json
  {
    "angularCompilerOptions": {
      "strictTemplates": true,
      "strictInjectionParameters": true,
      "strictInputAccessModifiers": true
    }
  }
  ```
- Keep `angular.configs.templateRecommended` and `templateAccessibility` on `**/*.html`.

## Code

- Standalone components only, no `NgModule`. `ChangeDetectionStrategy.OnPush` on every component.
- Signals for state: `signal<T>()`, `computed<T>()`, `linkedSignal`; `effect` only for side effects outside Angular (logging, DOM APIs).
- Signal inputs and outputs, not decorators:
  ```ts
  @Component({ selector: "app-user-card", changeDetection: ChangeDetectionStrategy.OnPush, templateUrl: "./user-card.html" })
  export class UserCard {
    readonly user: InputSignal<User> = input.required<User>();
    readonly selected: OutputEmitterRef<string> = output<string>();
    readonly label: Signal<string> = computed((): string => this.user().name.trim());
  }
  ```
- `inject()` for dependencies, not constructor parameters.
- Built-in control flow (`@if`, `@for` with `track`, `@switch`), not `*ngIf` / `*ngFor`. `@defer` for heavy parts below the fold.
- HTTP data: `httpResource()` or `HttpClient` in a service; convert observables with `toSignal`. Validate responses at the boundary.
- Forms: Signal Forms (`form()` from `@angular/forms/signals`) for new forms; Reactive Forms stay fine in existing code. No template-driven forms for anything with validation.
- Never bypass sanitization (`bypassSecurityTrust*`) with user content.

## Tests

- `ng test` runs Vitest (jsdom by default). `TestBed` is zoneless by default: after a state change, `await fixture.whenStable()` instead of `fakeAsync` / `tick`.
- Test through the DOM: set inputs with `fixture.componentRef.setInput("user", user)`, query rendered elements by role or text.
- Replace HTTP with `provideHttpClientTesting()` and `HttpTestingController`; never hit the network.
- Playwright for end-to-end.
