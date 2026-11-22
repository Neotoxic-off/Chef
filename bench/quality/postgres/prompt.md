Write a PostgreSQL 18 function `transfer(from_account bigint, to_account bigint, amount numeric)` over a table `accounts(id bigint primary key, balance numeric not null check (balance >= 0))` that moves money atomically, locks both rows in a fixed order to avoid deadlocks, and raises distinct errors for an unknown account, a non-positive amount, the same account twice and insufficient funds. Include the table and function in `schema.sql`.

Work autonomously: nobody will answer questions.
