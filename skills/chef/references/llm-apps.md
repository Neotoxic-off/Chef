# LLM applications

Provider-neutral. Builds on the language reference (`python.md`, `typescript.md`). Security list checked November 2026: OWASP Top 10 for LLM Applications 2026 (prompt injection stays LLM01). SDKs and model IDs change monthly: read the provider's current docs and changelog before writing calls.

## Prompts are code

- Prompts live in versioned template files in the repo, reviewed like code, rendered by one typed function. No prompt strings scattered through the code.
- Each prompt has an ID and version; log them with every call.
- Model ID, temperature, max output tokens and timeouts come from config. Pin dated model snapshots, not floating aliases, in production.
- Wrap the provider SDK behind a small interface you own, so logic and tests do not depend on one vendor.

```python
TRIAGE_PROMPT_VERSION: Final[str] = "triage-v3"


class TicketTriage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Literal["bug", "feature", "question"]
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredCompletion(Protocol):
    def complete_json(self, prompt: RenderedPrompt, schema: dict[str, object]) -> str: ...


def triage(client: StructuredCompletion, prompts: PromptStore, ticket_text: str) -> TicketTriage:
    prompt: RenderedPrompt = prompts.render(TRIAGE_PROMPT_VERSION, ticket=ticket_text)
    raw_json: str = client.complete_json(prompt, TicketTriage.model_json_schema())
    return TicketTriage.model_validate_json(raw_json)
```

## Structured outputs

- Use the provider's JSON-schema output mode or tool calling. Never parse free text with regexes.
- Validate every response with the schema anyway (Pydantic, Zod). A validation failure is an error: retry a bounded number of times or fail, never guess.

## Retries, timeouts, limits

- Set the SDK's `timeout` and `max_retries` explicitly. Retry only 429, 5xx and timeouts, with exponential backoff and jitter, honoring `Retry-After`.
- Never retry a call that triggered a side effect unless the side effect is idempotent.
- Cap concurrency (semaphore or queue) below the account's rate limits.

## Cost and latency

- Log per call: prompt ID, model, input and output tokens, latency, cache hits. Never log raw prompts or responses that contain personal data or secrets; log IDs and counts.
- Put the stable part of the prompt first so provider prompt caching applies. Cap `max_tokens`.
- Stream responses for interactive UX; use batch APIs for offline jobs; route easy tasks to smaller models, decided by evals.
- Set a budget alert per environment.

## Evals

- A versioned eval set (inputs, expected outputs or rubric) lives in the repo, including past failures and attack cases.
- Grade with code checks first; LLM-as-judge only with a written rubric checked against human labels.
- Run evals in CI on every prompt, model or retrieval change; fail below a named pass-rate threshold. Tools: Inspect, promptfoo, or a pytest suite.

## Tests

- Unit tests use a fake `StructuredCompletion`; no network calls. Assert on properties (schema, labels), not exact wording.

## Prompt injection and output handling

- Treat everything not written by you as untrusted data: user input, retrieved documents, web pages, file contents, tool results.
- Delimiting untrusted text helps but is not a defense. Rely on privilege limits:
  - tools get least privilege and allow-listed arguments, validated in code;
  - actions with side effects (payments, emails, deletes) need human confirmation;
  - the model never sees secrets; credentials stay in the tool layer.
- Treat model output as untrusted input: escape before rendering HTML or Markdown (block remote images and links that can exfiltrate data), parameterize SQL, never `eval` or run it as a shell command.
- Agents with tools: also read the OWASP Top 10 for Agentic Applications.
