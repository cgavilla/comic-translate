# Free and local AI translation

Comic Translate can translate with **no account, no credits and no API key**,
using either a model running on your own machine or a hosted free tier.

This document describes what changed, how to configure it, and what the limits
are.

## Quick start (free, offline, no account)

1. Install [Ollama](https://ollama.com) and pull a multilingual model:

   ```bash
   ollama serve
   ollama pull qwen3:8b
   ```

2. In Comic Translate, open **Settings → Tools** and set the translator to
   **Custom**.
3. Leave **API Key** and **Endpoint URL** empty.
4. Press **Test Connection** in **Settings → Advanced**.

A local server on port 11434 (Ollama), 1234 (LM Studio) or 8080 (LocalAI /
llama.cpp) is discovered automatically, and its first suitable model is
selected. You can leave the **Model** field empty too.

## Hosted free tiers

Anything speaking the OpenAI `/chat/completions` API works:

| Provider | Endpoint | Notes |
| --- | --- | --- |
| Groq | `https://api.groq.com/openai/v1` | Free tier, very fast, rate limited |
| OpenRouter | `https://openrouter.ai/api/v1` | Use models ending in `:free` |
| Google AI Studio | `https://generativelanguage.googleapis.com/v1beta/openai/` | Free tier |
| GitHub Models | `https://models.github.ai/inference` | Needs a GitHub token |
| Cloudflare Workers AI | `https://api.cloudflare.com/client/v4/ai` | Free allocation |

Set the **Endpoint URL**, the **Model** and the **API Key** in
**Settings → Advanced**.

## No account required

Nothing in the app demands an account. Signing in is optional, and only buys
access to the hosted credits:

- **Local models** - Custom translator, plus the bundled OCR engines.
- **Hosted free tiers** - Custom translator pointed at Groq, OpenRouter, etc.
- **Your own API keys** - Settings → Advanced exposes key fields for
  **Open AI GPT**, **Anthropic Claude**, **Google Gemini**, **Deepseek** and
  **Microsoft Azure**. With a key entered, those engines run without signing in.

The only remaining prompts ask for a session when a hosted credit option is
selected *and* no key of your own is configured. The message says so and points
at the alternatives.

## HTTP proxy

**Settings → Advanced → Network** accepts a proxy URL, for example
`http://127.0.0.1:8080`. Leave it empty to fall back to the `HTTPS_PROXY` /
`HTTP_PROXY` / `ALL_PROXY` environment variables.

- Every outbound call goes through `modules/utils/http_client.py`: all
  translators, all OCR engines, the client catalog and the update check. The
  only exception is the sign-in backend in `app/account/auth`, which is only
  reached by people who choose to sign in.
- **Local model servers are always contacted directly**, even when a proxy is
  configured. `requests` merges the environment with `proxies.setdefault()`, so
  loopback URLs are passed an explicit `{"http": None, "https": None}` mapping
  that the environment cannot override. Without this, configuring a proxy would
  break Ollama.
- The proxy is stored as plain settings, not as a credential, so it persists
  regardless of the **Save Keys** toggle.

## Settings reference

| Field | Required | Notes |
| --- | --- | --- |
| API Key | No | Local servers ignore it. Omit to avoid a rejected `Bearer` header |
| Endpoint URL | No | Auto-detected when empty |
| Model | No | Auto-selected from `/models` when empty, or pick it from the dropdown |
| Temperature | No | Defaults to `0.2` |
| Endpoint accepts images | No | Off by default; enable only for vision-capable endpoints |

**List Models** asks the endpoint what it serves and fills the dropdown, so the
model never has to be typed by hand. Typing in the **Model** field clears the
dropdown so it cannot silently override you.

**Test Connection** probes `/models` when no model is set, and otherwise sends a
one-token chat completion — the only way to catch a wrong model name before
processing a whole comic. It runs off the UI thread and reports which endpoint
it used.

## Behaviour changes

These affect the existing `Custom` translator, not just the free setup:

- **`Custom` no longer requires signing in.** It uses your own endpoint, so it
  is validated before the login gate and consumes no credits.
- **Local OCR engines no longer require signing in either.** The bundled
  default OCR, manga-ocr and Pororo run on your machine, so they are allowed
  while logged out. Only the remote options served through your credits
  (Gemini-2.5-Flash-Lite and Microsoft OCR) still need a session. Without this,
  OCR was validated *before* the translator and blocked the whole pipeline.
- **The API Key became optional**; `api_url` and `model` alone are enough, and
  an empty `api_url` is fine when a local server is running.
- **Page images are no longer sent** to `Custom` by default. Most free and local
  models are text-only and reject the `image_url` content part outright. Tick
  **Endpoint accepts images** to opt back in.
- **`max_tokens` is sent instead of `max_completion_tokens`.** Local runtimes
  and older compatible servers only understand the legacy name; a `400` on the
  new name still falls back, so hosted OpenAI keeps working.
- **Temperature defaults to `0.2` for `Custom`** and is configurable. At the old
  hard-coded `1.0`, free models drift off the JSON format and lose the page.
- **Malformed model output no longer raises.** Text blocks are re-parsed from
  fenced markdown, surrounding prose, smart quotes, trailing commas and Python
  literals; anything unusable is reported as a failed page instead of an
  exception.
- **Requests retry** on 408/425/429/5xx with exponential backoff, honouring
  `Retry-After`. Free tiers rate-limit aggressively.
- **Timeouts are longer for `Custom`** (300s), since CPU inference is slow.
- **A partially translated page is no longer thrown away.** Blocks already in
  the translation cache are reused and only the missing ones are sent, then
  merged back. A rate limit halfway through a page used to cost every block it
  had already finished.

## Architecture

| File | Role |
| --- | --- |
| `modules/utils/http_client.py` | Shared HTTP layer: proxy resolution, loopback bypass, retries, timeouts |
| `modules/utils/local_llm.py` | Discovery of local servers, endpoint fallback, model selection |
| `modules/translation/llm/custom.py` | Engine wiring: optional key, no image, auto endpoint/model |
| `modules/translation/llm/gpt.py` | OpenAI-compatible request, conditional auth header, token-field fallback |
| `modules/utils/pipeline_config.py` | Validates `Custom` before the login gate |
| `modules/utils/translator_utils.py` | Relaxed JSON parsing of model responses |

`Custom` inherits from `GPTTranslation`, so anything compatible with OpenAI
needs no code — only configuration.

## Verification

Covered by integration tests against a fake OpenAI-compatible server and a
fake HTTP proxy, both on loopback:

- loopback bypasses the proxy while external hosts are routed through it
- discovery of a server on Ollama's default port, and fallback when a saved
  loopback URL is dead
- a full translation with no API key, no session and no image attached
- retry across a `429`, and `max_completion_tokens` → `max_tokens` fallback
- JSON repair across fenced, prose-wrapped, and otherwise malformed responses
- settings round-trip and the Test Connection success and failure paths
- a logged-out user with local OCR and `Custom` passing the full pipeline
  validation, while account-backed OCR and credit-based translators are still
  refused

## Limitations

- Credential fields persist only when **Save Keys** is enabled (pre-existing
  behaviour). The proxy persists regardless, as it is not a secret.
- Only text is sent to `Custom` models. Vision-capable endpoints will not
  receive the page image.
- The proxy setting covers three translators; extending it to Gemini, Claude
  and the OCR engines means routing their remaining call sites through
  `http_client`.