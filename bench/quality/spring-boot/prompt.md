Write a Spring Boot 4 REST service with `POST /todos` (JSON `{ "title": string }`, 201 with the created todo `{ "id", "title", "done" }`), `GET /todos/{id}` (404 when missing) and `PATCH /todos/{id}` with `{ "done": boolean }`. Titles are 1 to 200 characters after trimming, otherwise 400 with a problem detail (RFC 9457). Store todos in memory. Gradle or Maven build.

Work autonomously: nobody will answer questions.
