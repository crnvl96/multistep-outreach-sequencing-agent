## Parent

`docs/design/multistep-outreach-sequencing-agent-mvp.md`

## Type

HITL

## User stories covered

- 6. As a reviewer, I want real LLM scoring against a documented ICP, so that the central reasoning step is not mocked.
- 12. As a developer, I want provider configuration through environment variables, so that OpenAI and OpenRouter can be swapped without changing workflow code.

Requirements covered: 19-24.

## What to build

Implement real OpenAI and OpenRouter LLM providers behind the existing provider interface. Provider selection, model selection, and credentials should come from environment variables. Real providers should support both sequential workflow calls: ICP scoring and route-specific first email generation.

This slice is HITL because full manual verification requires human-provided API keys and model choices.

## Acceptance criteria

- [ ] `LLM_PROVIDER=openai` selects the OpenAI provider.
- [ ] `LLM_PROVIDER=openrouter` selects the OpenRouter provider.
- [ ] `LLM_MODEL=<model-name>` controls the model used by the selected real provider.
- [ ] Missing `OPENAI_API_KEY` when OpenAI is selected fails with a clear configuration error.
- [ ] Missing `OPENROUTER_API_KEY` when OpenRouter is selected fails with a clear configuration error.
- [ ] Real provider scoring requests include the documented ICP, enriched lead profile, and instructions for strict structured JSON.
- [ ] Real provider email requests include the final deterministic route, selected route instructions, lead profile, scoring context, and instructions not to invent facts.
- [ ] Real provider responses flow through the same validation and repair logic as fake provider responses.
- [ ] With valid credentials, a non-insufficient fixture can complete with OpenAI and return validated scoring and email JSON.
- [ ] With valid credentials, a non-insufficient fixture can complete with OpenRouter and return validated scoring and email JSON.

## Verification

- [ ] Automated: run the project test command and confirm tests do not require real API keys or network.
- [ ] Automated: run provider configuration tests that verify provider selection and missing-key errors without making live calls.
- [ ] Manual HITL: set `LLM_PROVIDER=openai`, `LLM_MODEL`, and `OPENAI_API_KEY`; run a non-insufficient fixture and confirm validated scoring/email output.
- [ ] Manual HITL: set `LLM_PROVIDER=openrouter`, `LLM_MODEL`, and `OPENROUTER_API_KEY`; run a non-insufficient fixture and confirm validated scoring/email output.

## Blocked by

- `05-llm-validation-repair.md`

## Implementation notes

- Keep provider-specific HTTP/API details inside provider implementations; orchestration should depend only on the provider interface.
- Do not make live LLM tests part of the default automated test suite.
- Use async-capable provider methods, but preserve workflow order: scoring first, then route-specific email generation.
- The real provider prompts should reuse the same schema expectations validated by the application.
- Fail clearly on configuration errors. Do not silently fall back from a real provider to fake.
- The design accepts the tradeoff that reviewers need an API key for real LLM demo behavior.

## Review

After implementation, run the slice's verification checks and then run `/skill:review all uncommitted changes` before considering this done.
