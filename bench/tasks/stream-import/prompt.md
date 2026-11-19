The statement importer (the code in this folder) falls over on the yearly exports from our new bank: the files are 2 to 3 GB and the import job runs out of memory. Today it reads the whole file and keeps every transaction in memory before writing them.

Please make it stream:

- Read the CSV incrementally, never the whole file at once, and hand valid rows to the sink in batches as soon as a batch is full instead of all at the end. The last batch can be smaller; never write an empty batch.
- Batch size is configurable: a `batch_size` field on `ImportOptions` (default 500) and a `--batch-size` flag on the CLI. Zero or a negative size is invalid.
- Everything else must behave exactly as today: same report (counts, totals, rejected rows and their line numbers), duplicates still detected across the whole file, same `--max-errors` rule, same handling of the files our banks send.
- An import that is aborted or fails midway, for any reason, must still leave the ledger unchanged: all of a file or nothing.

Work autonomously: nobody will answer questions.
