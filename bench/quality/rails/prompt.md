In a Rails 8 app, add a `Bookmark` resource (`url`, `title`) with a JSON API: `POST /bookmarks` (201), `GET /bookmarks` (newest first, 20 per page, `?page=`), `DELETE /bookmarks/:id` (204, 404 when missing). URLs must be http(s) and unique; failures return 422 with the errors. Include the migration, model, controller and routes.

Work autonomously: nobody will answer questions.
