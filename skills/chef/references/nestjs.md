# Node backends: NestJS, Express, Fastify

Builds on `typescript.md`. Written for NestJS 12.5, @nestjs/config 12.1, @nestjs/terminus 12.2, Express 5.3, Fastify 5.12 (Nov 2026), not benchmarked. Nest 12 packages are ESM-only: apps need Node.js 20.19+ or 22.12+; the CLI generators need 22.22.3+, 24.15+ or 26+.

## NestJS structure

- One module per feature: controller (HTTP only), service (logic), repository or client (I/O). Controllers never touch the database.
- Constructor injection with `private readonly` typed parameters. Inject the clock and outbound clients through providers so tests can override them.
- `typescript.md` turns on `@typescript-eslint/no-extraneous-class`, which flags empty decorated module classes. Configure it, do not disable it:
  ```js
  { rules: { "@typescript-eslint/no-extraneous-class": ["error", { allowWithDecorator: true }] } }  // Nest modules are empty decorated classes
  ```
- New projects from `nest new` lint with oxlint by default; keep the ESLint setup from `typescript.md` unless the project already chose oxlint.

## Validation at the boundary

Pick one style per project.

- Schema-first (Nest 12): a Standard Schema library (zod) on the route decorator, validated by a global `StandardSchemaValidationPipe`:
  ```ts
  export interface CreateUserDto { readonly email: string; readonly name: string }

  export const createUserSchema: z.ZodType<CreateUserDto> = z.object({
    email: z.email(),
    name: z.string().min(1).max(100),
  });

  @Post()
  public create(@Body({ schema: createUserSchema }) body: CreateUserDto): Promise<UserView> {
    return this.users.create(body);
  }
  ```
  `app.useGlobalPipes(new StandardSchemaValidationPipe());` (`import { StandardSchemaValidationPipe } from "@nestjs/common"`).
- Class-based: class-validator DTOs with `new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true, transform: true })`.

## Config

- `ConfigModule.forRoot({ isGlobal: true, validationSchema: envSchema })` with a zod schema (v12 accepts any Standard Schema); the app refuses to start on bad env.
- Read typed values: `ConfigService<Env, true>` and `config.get("PORT", { infer: true })`. No `process.env` outside config.

## Errors

- Services throw domain errors; one global exception filter maps them to HTTP status codes and a stable body (`application/problem+json`: `type`, `title`, `status`, `detail`). No `try`/`catch` in controllers.
- Never leak stack traces or ORM messages in responses; log them with the request id.
- Health with `@nestjs/terminus`; in v12 indicators return `indicator.up()` / `indicator.down()` instead of throwing.

## Tests

- Vitest is the default for ESM projects. Jest loads the ESM-only v12 packages only on Node.js 24.9+.
- Unit: `Test.createTestingModule(...)`, replace boundaries with `.overrideProvider(X).useValue(fake)`.
- E2E: create the app once, hit it with supertest, run against a real database from `@testcontainers/postgresql`:
  ```ts
  it("findOne_WhenMissing_Returns404", async (): Promise<void> => {
    await request(app.getHttpServer()).get("/users/999").expect(404);
  });
  ```

## Express and Fastify (without Nest)

- Express 5: rejected promises from async handlers reach the error middleware, so do not wrap handlers in `try`/`catch`. One error middleware with four parameters at the end. Parse `req.body` with zod in each handler before use. `helmet` on, explicit CORS origins.
- Fastify 5: declare a schema per route (built-in validation and serialization) through a type provider so handlers get typed input. Test with `app.inject()` instead of opening a port.
- Both: build the app in a factory (`buildApp(deps)`) separate from `listen()`, so tests inject fakes and no global state leaks.
