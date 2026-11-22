Write an ASP.NET Core 10 minimal API with `GET /weather/{city}` returning `{ "city", "celsius", "observedAt" }` from an injected `IWeatherSource`, cached for 60 seconds per city. Unknown cities return 404 with a problem detail; a city name longer than 80 characters returns 400. Provide an in-memory `IWeatherSource` for development.

Work autonomously: nobody will answer questions.
