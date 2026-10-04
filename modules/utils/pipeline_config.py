from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from typing import TYPE_CHECKING
from modules.inpainting.lama import LaMa
from modules.inpainting.mi_gan import MIGAN
from modules.inpainting.aot import AOT
from modules.inpainting.schema import Config
from modules.utils.local_llm import resolve_endpoint
from modules.ocr.user_ocr import UserOCR
from app.ui.messages import Messages
from app.ui.settings.settings_page import SettingsPage

if TYPE_CHECKING:
    from controller import ComicTranslate

inpaint_map = {
    "LaMa": LaMa,
    "MI-GAN": MIGAN,
    "AOT": AOT,
}

# OCR options that are served by the user's account and therefore need a
# session. Everything else is a local engine.
ACCOUNT_OCR_KEYS = UserOCR.LLM_OCR_KEYS | UserOCR.FULL_PAGE_OCR_KEYS

# Which credential service holds the user's own API key for each hosted
# option. Supplying one of these lets the engine run without an account, so
# signing in is never mandatory.
OWN_KEY_SERVICES = {
    "GPT-4.1": "Open AI GPT",
    "GPT-4.1-mini": "Open AI GPT",
    "Claude-4.6-Sonnet": "Anthropic Claude",
    "Claude-4.5-Haiku": "Anthropic Claude",
    "Gemini-3.1-Flash-Lite": "Google Gemini",
    "Gemini-2.5-Pro": "Google Gemini",
    "Deepseek": "Deepseek",
    "Microsoft OCR": "Microsoft Azure",
    "Gemini-2.5-Flash-Lite": "Google Gemini",
}


def has_own_key(settings_page: SettingsPage, option: str) -> bool:
    """True when the user configured their own API key for ``option``."""
    service = OWN_KEY_SERVICES.get(option)
    if not service:
        return False
    creds = settings_page.get_credentials(settings_page.ui.tr(service))
    return bool((creds.get('api_key') or '').strip())


def get_inpainter_backend(inpainter_key: str) -> str:
    inpainter_cls = inpaint_map[inpainter_key]
    return getattr(inpainter_cls, "preferred_backend", "onnx")

def get_config(settings_page: SettingsPage):
    strategy_settings = settings_page.get_hd_strategy_settings()
    if strategy_settings['strategy'] == settings_page.ui.tr("Resize"):
        config = Config(hd_strategy="Resize", hd_strategy_resize_limit = strategy_settings['resize_limit'])
    elif strategy_settings['strategy'] == settings_page.ui.tr("Crop"):
        config = Config(hd_strategy="Crop", hd_strategy_crop_margin = strategy_settings['crop_margin'],
                        hd_strategy_crop_trigger_size = strategy_settings['crop_trigger_size'])
    else:
        config = Config(hd_strategy="Original")

    return config


def validate_ocr(main: ComicTranslate):
    """Ensure the selected OCR tool is usable.

    The bundled local engines (default OCR, manga-ocr, Pororo...) run locally
    and need no account. Only the remote options proxied through the user's
    credits require a session.
    """
    settings_page = main.settings_page
    settings = settings_page.get_all_settings()
    ocr_tool = settings['tools']['ocr']

    if not ocr_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Text Recognition model"))
        return False

    if not settings_page.is_logged_in() and ocr_tool in ACCOUNT_OCR_KEYS:
        # The user's own key needs no account.
        if not has_own_key(settings_page, ocr_tool):
            Messages.show_not_logged_in_error(main)
            return False

    return True


def validate_translator(main: ComicTranslate, target_lang: str):
    """Ensure either API credentials are set or the user is authenticated, plus check compatibility."""
    settings_page = main.settings_page
    tr = settings_page.ui.tr
    settings = settings_page.get_all_settings()
    credentials = settings.get('credentials', {})
    translator_tool = settings['tools']['translator']

    if not translator_tool:
        Messages.show_missing_tool_error(main, QCoreApplication.translate("Messages", "Translator"))
        return False

    # Custom talks straight to the user's own endpoint - a local Ollama /
    # LM Studio server or a hosted free OpenAI-compatible API. It needs neither
    # a session nor credits, so it is checked before the login gate.
    if "Custom" in translator_tool:
        service = tr('Custom')
        creds = credentials.get(service, {})
        # api_key is optional: local servers ignore it and free tiers differ.
        # An empty api_url is fine too - a local server is auto-detected. This
        # runs on the UI thread, so discovery uses a tight timeout: a closed
        # local port is not always refused instantly.
        if creds.get('model') and resolve_endpoint(creds.get('api_url'),
                                                   timeout=0.25)[0]:
            return True
        Messages.show_custom_not_configured_error(main)
        return False

    # A user who brought their own API key needs no account either.
    if has_own_key(settings_page, translator_tool):
        return True

    if not settings_page.is_logged_in():
        Messages.show_not_logged_in_error(main)
        return False

    return True

def font_selected(main: ComicTranslate):
    if not main.render_settings().font_family:
        Messages.select_font_error(main)
        return False
    return True

def validate_settings(main: ComicTranslate, target_lang: str):
    if not validate_ocr(main):
        return False
    if not validate_translator(main, target_lang):
        return False
    if not font_selected(main):
        return False
    
    return True
