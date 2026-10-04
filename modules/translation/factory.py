import json
import hashlib

from .base import TranslationEngine
from .microsoft import MicrosoftTranslation
from .deepl import DeepLTranslation
from .yandex import YandexTranslation
from .llm.gpt import GPTTranslation
from .llm.claude import ClaudeTranslation
from .llm.gemini import GeminiTranslation
from .llm.deepseek import DeepseekTranslation
from .llm.custom import CustomTranslation
from .user import UserTranslator
from app.account.auth.token_storage import get_token


class TranslationFactory:
    """Factory for creating appropriate translation engines based on settings."""
    
    _engines = {}  # Cache of created engines
    
    # Map traditional translation services to their engine classes
    TRADITIONAL_ENGINES = {
        "Microsoft Translator": MicrosoftTranslation,
        "DeepL": DeepLTranslation,
        "Yandex": YandexTranslation
    }
    
    # Map LLM identifiers to their engine classes
    LLM_ENGINE_IDENTIFIERS = {
        "GPT": GPTTranslation,
        "Claude": ClaudeTranslation,
        "Gemini": GeminiTranslation,
        "Deepseek": DeepseekTranslation,
        "Custom": CustomTranslation
    }
    
    DEFAULT_LLM_ENGINE = GPTTranslation

    # Providers whose own API key can be entered in Settings > Advanced. When
    # the user supplied one they are paying their own way, so their key must
    # win over the account's credits.
    OWN_KEY_SERVICES = {
        "GPT": "Open AI GPT",
        "Claude": "Anthropic Claude",
        "Gemini": "Google Gemini",
        "Deepseek": "Deepseek",
    }
    
    @classmethod
    def create_engine(cls, settings, source_lang: str, target_lang: str, translator_key: str) -> TranslationEngine:
        """
        Create or retrieve an appropriate translation engine based on settings.
        
        Args:
            settings: Settings object with translation configuration
            source_lang: Source language name
            target_lang: Target language name
            translator_key: Key identifying which translator to use
            
        Returns:
            Appropriate translation engine instance
        """
        # Create a cache key based on translator and language pair
        cache_key = cls._create_cache_key(translator_key, source_lang, target_lang, settings)
        
        # Return cached engine if available
        if cache_key in cls._engines:
            return cls._engines[cache_key]
        
        # Determine engine class and create engine
        engine_class = cls._get_engine_class(settings, translator_key)
        engine = engine_class()
        
        # Initialize with appropriate parameters
        if translator_key not in cls.TRADITIONAL_ENGINES or isinstance(engine, UserTranslator):
            engine.initialize(settings, source_lang, target_lang, translator_key)
        else:
            engine.initialize(settings, source_lang, target_lang)
        
        # Cache the engine
        cls._engines[cache_key] = engine
        return engine
    

    @classmethod
    def _has_own_key(cls, settings, translator_key: str) -> bool:
        """True when the user configured their own API key for this provider."""
        for identifier, service in cls.OWN_KEY_SERVICES.items():
            if identifier in translator_key:
                creds = settings.get_credentials(settings.ui.tr(service))
                if (creds.get('api_key') or '').strip():
                    return True
        return False

    @classmethod
    def _get_engine_class(cls, settings, translator_key: str):
        """Get the appropriate engine class based on translator key."""

        access_token = get_token("access_token")
        # The credits proxy only applies when the user has no key of their own.
        # Routing around a supplied key is what turns a free setup into a
        # login/credits prompt.
        if access_token and translator_key not in ['Custom'] \
                and not cls._has_own_key(settings, translator_key):
            return UserTranslator

        # First check if it's a traditional translation engine (exact match)
        if translator_key in cls.TRADITIONAL_ENGINES:
            return cls.TRADITIONAL_ENGINES[translator_key]
        
        # Otherwise look for matching LLM engine (substring match)
        for identifier, engine_class in cls.LLM_ENGINE_IDENTIFIERS.items():
            if identifier in translator_key:
                return engine_class
        
        # Default to LLM engine if no match found
        return cls.DEFAULT_LLM_ENGINE
    
    @classmethod
    def _own_key_service(cls, translator_key: str) -> str | None:
        """Credential service holding this translator's own key, if any."""
        for identifier, service in cls.OWN_KEY_SERVICES.items():
            if identifier in translator_key:
                return service
        return None

    @classmethod
    def _create_cache_key(cls, translator_key: str,
                        source_lang: str,
                        target_lang: str,
                        settings) -> str:
        """
        Build a cache key for all translation engines.

        - Always includes per-translator credentials (if available),
          so changing any API key, URL, region, etc. triggers a new engine.
        - For LLM engines, also includes all LLM-specific settings
          (temperature, context, etc.).
        - The cache key is a hash of these dynamic values, combined with
          the translator key and language pair.
        - If no dynamic values are found, falls back to a simple key
          based on translator and language pair.
        """
        base = f"{translator_key}_{source_lang}_{target_lang}"

        # Gather any dynamic bits we care about:
        extras = {}

        # Always grab credentials for this service (if any). The translator key is
        # the *option* name ("GPT-4.1"), not the credential service
        # ("Open AI GPT"), so resolve it before looking anything up -
        # otherwise a changed API key leaves a stale engine cached.
        creds = settings.get_credentials(translator_key)
        own_service = cls._own_key_service(translator_key)
        if own_service:
            creds = dict(creds or {})
            creds["own"] = settings.get_credentials(settings.ui.tr(own_service))
        if creds:
            extras["credentials"] = creds

        # If it's an LLM, also grab the llm settings
        is_llm = any(identifier in translator_key
                     for identifier in cls.LLM_ENGINE_IDENTIFIERS)
        if is_llm:
            extras["llm"] = settings.get_llm_settings()

        if not extras:
            return base

        # Otherwise, hash the combined extras dict
        extras_json = json.dumps(
            extras,
            sort_keys=True,
            separators=(",", ":"),
            default=str
        )
        digest = hashlib.sha256(extras_json.encode("utf-8")).hexdigest()

        # Append the fingerprint
        return f"{base}_{digest}"
