Write a FastAPI service `app/main.py` with `POST /items` (Pydantic model `name` 1-100 characters, `price` > 0 with 2 decimals), `GET /items/{id}` (404 when missing) and `GET /items?limit=&offset=` (limit 1-100, default 20). Store items in memory behind an injected repository.

Work autonomously: nobody will answer questions.
