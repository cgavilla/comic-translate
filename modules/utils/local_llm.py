"""Discovery of local, free OpenAI-compatible servers (Ollama, LM Studio, ...).

These run with no API key, no account and no internet connection, which makes
them the cheapest way to translate a comic. The app probes for them so that
"Custom" can work out of the box, and so a hosted free tier can be used as the
fallback when no local server is running.
"""

from __future__ import annotations

import requests

from .http_client import HttpError, get_json, is_loopback, list_models

# Probed in order; the first one that answers /models wins. Only the loopback
# IP is listed - "localhost" resolves to the same server and would just probe
# each port twice.
KNOWN_LOCAL_ENDPOINTS = (
    ("http://127.0.0.1:11434/v1", "Ollama"),
    ("http://127.0.0.1:1234/v1", "LM Studio"),
    ("http://127.0.0.1:8080/v1", "LocalAI / llama.cpp"),
)

# Loopback probes answer in milliseconds when something is listening. A closed
# local port is not always refused instantly (a host firewall may drop the SYN
# and wait for the timeout), so this is deliberately tight: with three
# candidates the worst case stays around a second.
DISCOVERY_TIMEOUT = 0.4

# Preferred when an endpoint lists several models: good multilingual quality
# without needing a large GPU.
MODEL_PREFERENCE = (
    "qwen3",
    "qwen2.5",
    "llama-3.1",
    "llama3.1",
    "gemma-3",
    "gemma3",
    "mistral-nemo",
    "phi-4",
    "command-r",
)


def endpoint_is_up(base_url: str, timeout: float = DISCOVERY_TIMEOUT) -> bool:
    """True when ``base_url`` answers on ``/models``."""
    try:
        get_json(f"{base_url.rstrip('/')}/models", timeout=timeout)
        return True
    except (HttpError, requests.RequestException, ValueError):
        return False


def detect_local_endpoint(timeout: float = DISCOVERY_TIMEOUT) -> str | None:
    """First known local server that is running, if any."""
    for base_url, _label in KNOWN_LOCAL_ENDPOINTS:
        if endpoint_is_up(base_url, timeout):
            return base_url
    return None


def resolve_endpoint(configured: str = "",
                     timeout: float = DISCOVERY_TIMEOUT) -> tuple[str, str]:
    """Pick the endpoint to talk to, preferring the user's explicit choice.

    Returns ``(base_url, note)`` where ``note`` explains the decision so the UI
    can surface it instead of failing silently later on.
    """
    configured = (configured or "").strip().rstrip("/")

    if configured:
        if is_loopback(configured):
            if endpoint_is_up(configured, timeout):
                return configured, f"Using local endpoint {configured}"
            found = detect_local_endpoint(timeout)
            if found:
                return found, (f"{configured} is not responding. "
                               f"Using {found} instead.")
        return configured, f"Using endpoint {configured}"

    found = detect_local_endpoint(timeout)
    if found:
        return found, f"Detected local model server at {found}"
    return "", ("No local model server found. Set an Endpoint URL to use a "
                "hosted free API (Groq, OpenRouter, Google AI Studio).")


def pick_model(base_url: str, api_key: str = "") -> str:
    """Best default model advertised by an endpoint, or '' if it won't say."""
    names = list_models(base_url, api_key, timeout=DISCOVERY_TIMEOUT)
    if not names:
        return ""
    lowered = {name.lower(): name for name in names}
    for hint in MODEL_PREFERENCE:
        for key, name in lowered.items():
            if hint in key:
                return name
    return names[0]