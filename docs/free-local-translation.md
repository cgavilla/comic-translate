# Free and local AI translation

Comic Translate has **no account system**. There is nothing to sign up for,
nothing to sign in to, and no credits anywhere in the app. Every translator and
OCR engine either runs on your machine or talks to an endpoint using your own
API key.

## Quick start (free, offline)

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

## What replaced the account system

| Removed | Replacement |
| --- | --- |
| `app/account/` (OAuth client, local server, token storage) | Nothing — there is no session |
| `app/catalog.py` (remote translator/OCR/language list) | Static lists in `app/ui/settings/settings_ui.py` and `app/ui/main_window/constants.py` |
| `modules/translation/user.py`, `modules/ocr/user_ocr.py` (credits proxy) | `modules/translation/factory.py` and `modules/ocr/factory.py` build every engine directly |
| **Settings → Account** page | Nothing — its entries now live in **Settings → Advanced** as plain key fields |
| `InsufficientCreditsException` | Gone; a provider that runs out of balance is just a normal error |

The catalog also used to supply per-language rendering rules (RTL, vertical,
no-space). Those are now local constants in
`modules/utils/language_utils.py` (`BUNDLED_RENDERING`), so Arabic, Hebrew,
Persian, Chinese, Japanese and Thai still render correctly offline.

## Your own API keys

**Settings → Advanced** exposes key fields for **Open AI GPT**,
**Anthropic Claude**, **Google Gemini**, **Deepseek** and **Microsoft Azure**.
Entering a key makes that engine work with no session and no proxy of ours
involved — the request goes straight from your machine to the provider.

## HTTP proxy

**Settings → Advanced → Network** accepts a proxy URL, for example
`http://127.0.0.1:8080`. Leave it empty to fall back to the `HTTPS_PROXY` /
`HTTP_PROXY` / `ALL_PROXY` environment variables.

- Every outbound call goes through `modules/utils/http_client.py`: all
  translators, all OCR engines, and the update check.
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

## Validation rules

`modules/utils/pipeline_config.py` is the whole gate. It refuses only two
things, and neither involves an account:

1. No OCR tool selected.
2. Translator set to **Custom** with no reachable endpoint — the message says
   to start a local server or point at a hosted free tier.

Every other translator is accepted as-is; the request fails later, with the
provider's own error, if the key is wrong.

## Behaviour notes on `Custom`

- **The API Key is optional**; `api_url` and `model` alone are enough, and an
  empty `api_url` is fine when a local server is running.
- **Page images are not sent** by default. Most free and local models are
  text-only and reject the `image_url` content part outright. Tick **Endpoint
  accepts images** to opt back in.
- **`max_tokens` is sent instead of `max_completion_tokens`.** Local runtimes
  and older compatible servers only understand the legacy name; a `400` on the
  new name still falls back, so hosted OpenAI keeps working.
- **Temperature defaults to `0.2`**. At the old hard-coded `1.0`, free models
  drift off the JSON format and lose the page. It is configurable.
- **Malformed model output no longer raises.** Text blocks are re-parsed from
  fenced markdown, surrounding prose, smart quotes, trailing commas and Python
  literals; anything unusable is reported as a failed page instead of an
  exception.
- **Requests retry** on 408/425/429/5xx with exponential backoff, honouring
  `Retry-After`. Free tiers rate-limit aggressively.
- **Timeouts are longer** (300s), since CPU inference is slow.
- **A partially translated page is no longer thrown away.** Blocks already in
  the translation cache are reused and only the missing ones are sent, then
  merged back. A rate limit halfway through a page used to cost every block it
  had already finished.
- **Engine caches key off the credentials**, so changing an API key rebuilds
  the engine instead of leaving the previous one in place.

## Architecture

| File | Role |
| --- | --- |
| `modules/utils/http_client.py` | Shared HTTP layer: proxy resolution, loopback bypass, retries, timeouts |
| `modules/utils/local_llm.py` | Discovery of local servers, endpoint fallback, model selection |
| `modules/translation/llm/custom.py` | Engine wiring: optional key, no image, auto endpoint/model |
| `modules/translation/llm/gpt.py` | OpenAI-compatible request, conditional auth header, token-field fallback |
| `modules/translation/factory.py` | Builds every engine directly; no proxy, no session |
| `modules/utils/pipeline_config.py` | The only validation gate |
| `modules/utils/translator_utils.py` | Relaxed JSON parsing of model responses |
| `modules/utils/language_utils.py` | `BUNDLED_RENDERING` replaces the catalog's per-language rules |

`Custom` inherits from `GPTTranslation`, so anything compatible with OpenAI
needs no code — only configuration.

## Limitations

- Credential fields persist only when **Save Keys** is enabled (pre-existing
  behaviour). The proxy persists regardless, as it is not a secret.
- The **Microsoft OCR** engine needs the optional `azure-ai-vision-imageanalysis`
  package; choosing it without it gives an error naming what to install.
- Adding or removing a translator or OCR engine is now a code change — there is
  no server to publish a new option to.