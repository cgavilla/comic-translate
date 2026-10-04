"""Central HTTP client used by every outbound API call.

Three concerns live here so they stay consistent across the codebase instead of
being re-invented at each ``requests.post`` call site:

* **Proxy support** - one proxy URL, set from Settings > Advanced, falling back
  to the standard ``HTTPS_PROXY`` / ``HTTP_PROXY`` / ``ALL_PROXY`` environment
  variables. Loopback addresses are always bypassed, because a configured
  proxy otherwise breaks a local Ollama or LM Studio server.
* **Retries** - free tiers answer with 429/503 constantly, so transient
  failures are retried with exponential backoff rather than killing the page.
* **Timeouts** - one default everywhere, overridable per call.
"""

from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import requests


# Hosts that must never be routed through a proxy.
LOOPBACK_HOSTS = frozenset({
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "host.docker.internal",
})

DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3

# Status codes worth retrying: rate limits and transient gateway faults.
RETRY_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

# Explicit "no proxy" mapping. requests merges the environment with
# ``proxies.setdefault(k, v)``, so a key that is already present is never
# overwritten by HTTP_PROXY - this is what forces a direct connection.
_DIRECT = {"http": None, "https": None}

_proxy_url: str | None = None
_session: requests.Session | None = None


class HttpError(RuntimeError):
    """An HTTP request failed, carrying the status code for caller branching."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def set_proxy(url: str | None) -> None:
    """Set the proxy used by :func:`request` (Settings > Advanced).

    An empty value clears the override and restores the environment behaviour.
    """
    global _proxy_url
    _proxy_url = (url or "").strip() or None


def get_proxy() -> str | None:
    """The effective proxy URL: the Settings value wins, else the environment."""
    if _proxy_url:
        return _proxy_url
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy",
                "ALL_PROXY", "all_proxy"):
        value = (os.environ.get(var) or "").strip()
        if value:
            return value
    return None


def is_loopback(url: str) -> bool:
    """True when ``url`` points at this machine."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in LOOPBACK_HOSTS


def resolve_proxies(url: str) -> dict[str, Any] | None:
    """Build the ``proxies`` argument for ``requests`` targeting ``url``.

    Returns ``None`` to let requests apply the environment itself, an explicit
    mapping to route through the configured proxy, or a mapping that forces a
    direct connection for loopback endpoints.
    """
    if is_loopback(url):
        return dict(_DIRECT)
    proxy = get_proxy()
    if proxy:
        return {"http": proxy, "https": proxy}
    return None


def get_session() -> requests.Session:
    """Shared session, so connections are pooled across pages."""
    global _session
    if _session is None:
        session = requests.Session()
        # Honour HTTP_PROXY/HTTPS_PROXY unless a call overrides it.
        session.trust_env = True
        _session = session
    return _session


def _backoff(attempt: int, response: requests.Response | None) -> float:
    """Exponential backoff that respects ``Retry-After`` when the server sends it."""
    if response is not None:
        retry_after = response.headers.get("Retry-After", "")
        try:
            return min(float(retry_after), 60.0)
        except (TypeError, ValueError):
            pass
    return min(2.0 ** attempt, 30.0)


def describe_error(response: requests.Response) -> str:
    """Readable one-line reason for a failed response, including API error bodies."""
    detail = ""
    try:
        body = response.json()
        if isinstance(body, dict):
            error = body.get("error", body.get("message"))
            if isinstance(error, dict):
                detail = str(error.get("message") or error)
            elif error:
                detail = str(error)
            else:
                detail = str(body)[:500]
        else:
            detail = str(body)[:500]
    except Exception:
        detail = (response.text or "")[:500]

    message = f"HTTP {response.status_code} {response.reason}".strip()
    return f"{message} - {detail}" if detail else message


def request(method: str, url: str, *, headers: dict | None = None,
            json_body: Any = None, timeout: int | None = None,
            retries: int | None = None, **kwargs) -> requests.Response:
    """Perform an HTTP request, retrying transient failures.

    Returns the response even when it carries an error status, so callers can
    branch on it. Raises :class:`requests.RequestException` if every attempt
    failed to produce a response.
    """
    timeout = DEFAULT_TIMEOUT if timeout is None else timeout
    retries = DEFAULT_RETRIES if retries is None else retries

    session = get_session()
    proxies = resolve_proxies(url)
    last_exc: requests.RequestException | None = None

    for attempt in range(retries + 1):
        try:
            response = session.request(
                method, url,
                headers=headers or {},
                json=json_body,
                timeout=timeout,
                proxies=proxies,
                **kwargs,
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(_backoff(attempt, None))
            continue

        if response.status_code in RETRY_STATUS_CODES and attempt < retries:
            time.sleep(_backoff(attempt, response))
            continue
        return response

    raise last_exc


def post_json(url: str, *, headers: dict, payload: Any,
              timeout: int | None = None, retries: int | None = None) -> Any:
    """POST ``payload`` as JSON and return the parsed response body."""
    response = request("POST", url, headers=headers, json_body=payload,
                       timeout=timeout, retries=retries)
    if not response.ok:
        raise HttpError(f"API request failed: {describe_error(response)}",
                        status_code=response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise HttpError("API returned a non-JSON response") from exc


def get_json(url: str, *, headers: dict | None = None,
             timeout: int = 10, retries: int = 0) -> Any:
    """GET and parse a JSON body, raising :class:`HttpError` on failure."""
    response = request("GET", url, headers=headers or {}, timeout=timeout,
                       retries=retries)
    if not response.ok:
        raise HttpError(describe_error(response), status_code=response.status_code)
    try:
        return response.json()
    except ValueError as exc:
        raise HttpError("Endpoint returned a non-JSON response") from exc


def list_models(base_url: str, api_key: str = "", timeout: int = 5) -> list[str]:
    """Model IDs advertised by an OpenAI-compatible endpoint.

    Returns an empty list when the endpoint does not support model listing or is
    unreachable - callers treat that as "the user must type the model name".
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        body = get_json(f"{base_url.rstrip('/')}/models", headers=headers, timeout=timeout)
    except (HttpError, requests.RequestException):
        return []

    if not isinstance(body, dict):
        return []
    entries = body.get("data") or body.get("models") or []
    names = []
    for entry in entries:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict):
            name = entry.get("id") or entry.get("name")
            if name:
                names.append(str(name))
    return names


def probe(base_url: str, api_key: str = "", model: str = "",
          timeout: int = 8) -> tuple[bool, str]:
    """Check that an OpenAI-compatible endpoint is usable.

    Returns ``(ok, message)``. Probes ``/models`` when the model is unknown and
    otherwise sends a one-token request, which is the only way to catch a wrong
    model name before processing a whole comic.
    """
    base = base_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if not model:
        names = list_models(base, api_key, timeout=timeout)
        if names:
            return True, f"Endpoint reachable. Models: {', '.join(names[:5])}" + (
                " ..." if len(names) > 5 else "")
        return False, (
            f"Reached {base}, but /models returned nothing. "
            "Check the model name, or whether the server is still pulling it."
        )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    }
    try:
        post_json(f"{base}/chat/completions", headers=headers, payload=payload,
                  timeout=timeout, retries=0)
    except HttpError as exc:
        return False, str(exc)
    except requests.RequestException as exc:
        return False, f"Could not reach {base}: {exc}"
    return True, f"Connected to {base} using model '{model}'"