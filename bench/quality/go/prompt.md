Write a Go 1.26 package `ratelimit` with `type Limiter` created by `New(rate int, per time.Duration, clock func() time.Time) (*Limiter, error)`, and `Allow(key string) bool` implementing a fixed window per key. `rate` below 1 or `per` below one millisecond returns an error. Safe for concurrent use.

Work autonomously: nobody will answer questions.
