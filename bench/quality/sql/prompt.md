Write SQL migrations (PostgreSQL 18) for a library: `authors`, `books` (ISBN-13 unique and checked, at least one author per book through `book_authors`), and `loans` (a book can have at most one open loan; `returned_at` after `loaned_at`). Add a view `overdue_loans` for open loans older than 21 days. Put them in `migrations/001_*.sql` and up.

Work autonomously: nobody will answer questions.
