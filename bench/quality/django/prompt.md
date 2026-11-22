In a Django 6 project, add an app `polls` with `Question` and `Choice` models, a view that records a vote with `POST /polls/<id>/vote/` (one vote per session per question, 409 on a second vote, 404 for an unknown question or choice) and a JSON results view `GET /polls/<id>/results/`. Include migrations, URLs and the views.

Work autonomously: nobody will answer questions.
