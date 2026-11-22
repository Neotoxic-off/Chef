Write a Node 24 TypeScript module `src/orders.ts` using the official MongoDB driver 7: `createOrder(db, order)` validating the order (customer id, 1-50 lines, positive quantities and prices) and `ordersByCustomer(db, customerId, { limit, cursor })` with cursor pagination on `_id`, newest first. Create the indexes it needs in `ensureIndexes(db)`.

Work autonomously: nobody will answer questions.
