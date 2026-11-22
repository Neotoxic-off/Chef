Write a C17 library `strbuf.h` / `strbuf.c`: a growable string buffer with `strbuf_init`, `strbuf_append(strbuf *, const char *)`, `strbuf_appendf(strbuf *, const char *fmt, ...)`, `strbuf_cstr` and `strbuf_free`. Appends return 0 on success and -1 on allocation failure or size overflow, leaving the buffer unchanged. CMake build.

Work autonomously: nobody will answer questions.
