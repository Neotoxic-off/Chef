# Reference index

Find the stack, then read its file before touching code or config in it. A task that spans several stacks (e.g. a Python service with a Dockerfile and a CI workflow) reads each one. A framework file builds on its language file: read both.

Languages:

- C#, .NET, WPF, WinUI: `csharp.md`
- TypeScript, JavaScript, Node: `typescript.md`
- Python: `python.md`
- Rust: `rust.md`
- Go: `go.md`
- C: `c.md`
- C++: `cpp.md`
- Java: `java.md`
- Kotlin, Android: `kotlin.md`
- Swift: `swift.md`
- Dart, Flutter: `dart.md`
- PHP: `php.md`
- Ruby: `ruby.md`
- Scala: `scala.md`
- Elixir: `elixir.md`
- Lua: `lua.md`
- Bash, sh: `bash.md`
- PowerShell: `powershell.md`
- SQL, migrations: `sql.md`

DevOps and tools:

- Docker, Dockerfile, Compose: `docker.md`
- Kubernetes, Helm: `kubernetes.md`
- Terraform, OpenTofu: `terraform.md`
- CI/CD, GitHub Actions, GitLab CI: `ci.md`
- Ansible: `ansible.md`
- Git, commits, hooks: `git.md`

Frameworks:

- React, TanStack Query, Zustand: `react.md`
- Next.js: `nextjs.md`
- Vue, Nuxt, Pinia: `vue.md`
- Angular: `angular.md`
- Svelte, SvelteKit: `svelte.md`
- Tailwind CSS: `tailwind.md`
- ASP.NET Core: `aspnetcore.md`
- NestJS, Express, Fastify: `nestjs.md`
- Django, DRF: `django.md`
- FastAPI, Flask: `fastapi.md`
- Spring Boot: `spring-boot.md`
- Laravel: `laravel.md`
- Rails: `rails.md`

Observability:

- OpenTelemetry, Collector: `opentelemetry.md`
- Prometheus, alerting rules: `prometheus.md`
- Grafana, dashboards: `grafana.md`
- Loki, Alloy: `loki.md`
- Tracing, Tempo, Jaeger: `tracing.md`
- Application logging: `logging.md`
- SLOs, error budgets: `slo.md`

Data and messaging:

- PostgreSQL, PgBouncer: `postgres.md`
- Redis, Valkey: `redis.md`
- MongoDB: `mongodb.md`
- Kafka, RabbitMQ, outbox: `messaging.md`
- Elasticsearch, OpenSearch: `elasticsearch.md`
- ORMs: EF Core, Prisma, SQLAlchemy, Hibernate: `orm.md`

More languages and platforms:

- Zig: `zig.md`
- Haskell: `haskell.md`
- OCaml: `ocaml.md`
- F#: `fsharp.md`
- Clojure: `clojure.md`
- Erlang/OTP: `erlang.md`
- R: `r.md`
- Julia: `julia.md`
- Perl: `perl.md`
- Objective-C: `objective-c.md`
- Solidity, smart contracts: `solidity.md`
- WebAssembly, WASI: `wasm.md`
- CUDA: `cuda.md`
- Embedded C/C++, Arduino, RTOS: `embedded.md`
- VHDL, Verilog, SystemVerilog: `hdl.md`

Mobile, desktop, games:

- React Native, Expo: `react-native.md`
- Jetpack Compose: `jetpack-compose.md`
- SwiftUI: `swiftui.md`
- .NET MAUI: `maui.md`
- Avalonia: `avalonia.md`
- Electron: `electron.md`
- Tauri: `tauri.md`
- Qt, QML: `qt.md`
- Unity: `unity.md`
- Godot: `godot.md`
- Unreal Engine: `unreal.md`

More web:

- Astro: `astro.md`
- React Router, Remix: `react-router.md`
- SolidJS: `solidjs.md`
- Qwik: `qwik.md`
- htmx: `htmx.md`
- Blazor: `blazor.md`
- Vite, webpack, esbuild, Rolldown: `bundlers.md`
- Playwright, Cypress: `e2e-testing.md`
- Storybook: `storybook.md`
- Symfony: `symfony.md`
- Phoenix, LiveView: `phoenix.md`
- Axum, Actix, Tokio: `rust-web.md`
- Go web: net/http, chi, Gin, Echo: `go-web.md`
- Ktor: `ktor.md`
- Quarkus, Micronaut: `quarkus.md`
- Deno, Bun, Hono: `deno-bun.md`

Cloud and infrastructure:

- AWS: `aws.md`
- Azure: `azure.md`
- Google Cloud: `gcp.md`
- Serverless: Lambda, Functions, Cloud Run: `serverless.md`
- Pulumi: `pulumi.md`
- Bicep, ARM: `bicep.md`
- AWS CDK, CloudFormation: `aws-cdk.md`
- GitOps: Argo CD, Flux: `gitops.md`
- Secrets: Vault, SOPS, External Secrets: `secrets.md`
- Nginx, Caddy, Traefik, HAProxy: `reverse-proxy.md`
- Linux, systemd, SSH: `linux.md`
- Nix, NixOS: `nix.md`
- Service mesh: Istio, Linkerd, Cilium: `service-mesh.md`
- Make, just, Task: `makefile.md`
- YAML, JSON, TOML config: `config-files.md`
- Monorepos: Nx, Turborepo, Bazel: `monorepo.md`

Cross-cutting:

- REST, OpenAPI: `api-design.md`
- GraphQL: `graphql.md`
- gRPC, protobuf: `grpc.md`
- Security, OWASP, auth: `security.md`
- Accessibility, WCAG: `accessibility.md`
- i18n, l10n: `i18n.md`
- WebSockets, SSE: `websockets.md`

Data and AI:

- pandas, Polars: `dataframes.md`
- Jupyter notebooks: `notebooks.md`
- ML: PyTorch, scikit-learn: `ml.md`
- LLM and AI apps: `llm-apps.md`
- Airflow, Dagster, dbt, Spark: `data-engineering.md`
- Flink, Kafka Streams: `streaming.md`

Transformations (used by `/chef:transform`):

- .NET Framework to .NET, .NET majors: `dotnet-upgrade.md`
- TypeScript strict, TypeScript, Node and framework majors: `ts-strict.md`
- Raise coverage to the 90% gate: `test-coverage.md`
- Java 8/11/17 to 21/25, Spring Boot majors: `java-upgrade.md`
- Python minor upgrades: `python-upgrade.md`
