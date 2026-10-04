from typing import Any

from .gpt import GPTTranslation
from ...utils.local_llm import pick_model, resolve_endpoint


class CustomTranslation(GPTTranslation):
    """Translation engine using any OpenAI-compatible API.

    This is the free path: point it at a local Ollama / LM Studio server (no
    key, no account, works offline) or at a hosted free tier such as Groq or
    OpenRouter. If no endpoint is configured, a local server is auto-detected.
    """

    def __init__(self):
        super().__init__()
        self.endpoint_note = ""

    def initialize(self, settings: Any, source_lang: str, target_lang: str, tr_key: str, **kwargs) -> None:
        """
        Initialize custom translation engine.

        Args:
            settings: Settings object with credentials
            source_lang: Source language name
            target_lang: Target language name
        """
        # Call BaseLLMTranslation's initialize, not GPTTranslation's
        # to avoid the GPT-specific credential loading
        super(GPTTranslation, self).initialize(settings, source_lang, target_lang, **kwargs)

        # Get custom credentials instead of OpenAI credentials
        credentials = settings.get_credentials(settings.ui.tr(tr_key))
        self.api_key = (credentials.get('api_key') or '').strip()

        # Low temperature by default: free and local models drift off the JSON
        # format at 1.0, which loses the whole page's translation.
        try:
            self.temperature = float(credentials.get('temperature') or 0.2)
        except (TypeError, ValueError):
            self.temperature = 0.2

        # Resolve the endpoint: the configured one wins, otherwise fall back to
        # whichever local server is running.
        self.api_base_url, self.endpoint_note = resolve_endpoint(
            credentials.get('api_url') or '')

        # Free/local servers are text-only by default; sending a page image
        # makes most of them reject the request outright.
        self.supports_images = False

        # Most OpenAI-compatible servers only know the legacy token field.
        self.token_param = "max_tokens"

        self.model = (credentials.get('model') or '').strip()
        if not self.model and self.api_base_url:
            # Let the server pick: ask it which models it has.
            self.model = pick_model(self.api_base_url, self.api_key)

        # Local models on CPU are far slower than a hosted API.
        self.timeout = 300