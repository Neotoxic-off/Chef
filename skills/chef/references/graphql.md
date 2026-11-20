# GraphQL

Written for the GraphQL spec (September 2026 edition), the GraphQL over HTTP draft, @graphql-eslint/eslint-plugin 4.4, GraphQL Inspector 7.0 and the OWASP GraphQL Cheat Sheet (Nov 2026), not benchmarked.

## Schema

- Commit the SDL (schema-first, or printed from code-first types in CI) and review it like code.
- Fail CI on breaking schema changes: `graphql-inspector diff <base-schema> schema.graphql`.
- Non-null (`!`) only when the server can always return the value; a null in a non-null field nulls the whole parent.
- Mutations take one input and return a payload: `createOrder(input: CreateOrderInput!): CreateOrderPayload!`.
- Input unions: `@oneOf` input objects (in the spec since September 2025), not ad hoc nullable fields.
- Lists that can grow use cursor connections (Relay Cursor Connections spec) with a capped `first`.
- Deprecate with `@deprecated(reason: "...")`. Remove only after usage metrics show no clients.

## Lint

```js
import graphqlPlugin from "@graphql-eslint/eslint-plugin";

export default [
  {
    files: ["**/*.graphql"],
    languageOptions: { parser: graphqlPlugin.parser },
    plugins: { "@graphql-eslint": graphqlPlugin },
    rules: graphqlPlugin.configs["flat/schema-recommended"].rules,
  },
];
```

- `schema-recommended` turns on `require-description`. Keep it for a schema other teams or third parties consume: that is a public API. For a schema only your own frontend uses, turn the rule off in this config (never inline): the house rule keeps doc comments to public APIs.
- Lint client operations with `flat/operations-recommended`.

## Errors

- Expected domain failures are part of the schema: `union CreateOrderResult = Order | OutOfStock | InvalidAddress`. Clients switch on `__typename`.
- The top-level `errors` array is for unexpected failures. Mask messages in production; send a code in `extensions`, never a stack trace.

## Resolvers

- Resolvers stay thin and call services. Authorization lives in the service layer, checked per object, not only at the gateway.
- Batch with a DataLoader created per request; never share one across users.
- Validate arguments at the boundary beyond what scalars give (length, range, format) with custom scalars or a schema library.

## Security (OWASP GraphQL Cheat Sheet)

- Limit query depth, aliases and batch size, and enforce a query cost limit. Keep each limit in a named constant.
- Set timeouts and rate limits per user.
- Production: turn off GraphiQL and, for private APIs, introspection.
- First-party clients: allow only persisted operations (trusted documents) when the clients are known.
- GraphQL over HTTP (draft): serve `application/graphql-response+json`; mutations only over `POST`.

## Tests

- Run real operations against the built schema with real resolvers and test doubles only at I/O boundaries.
- Assert both `data` and `errors`: `createOrder with out-of-stock item returns OutOfStock`.
- Snapshot the printed schema so any change shows up in review.
