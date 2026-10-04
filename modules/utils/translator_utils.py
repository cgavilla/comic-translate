import base64
import json
import logging
import re
import numpy as np
from .textblock import TextBlock
import imkit as imk

logger = logging.getLogger(__name__)


MODEL_MAP = {
    "Custom": "",  
    "Deepseek": "deepseek-v4-flash", 
    "GPT-4.1": "gpt-4.1",
    "GPT-4.1-mini": "gpt-4.1-mini",
    "Claude-4.6-Sonnet": "claude-sonnet-4-6",
    "Claude-4.5-Haiku": "claude-haiku-4-5-20251001",
    "Gemini-2.5-Flash-Lite": "gemini-2.5-flash-lite",
    "Gemini-3.1-Flash-Lite": "gemini-3.1-flash-lite",
    "Gemini-2.5-Pro": "gemini-2.5-pro"
}

def encode_image_array(img_array: np.ndarray):
    img_bytes = imk.encode_image(img_array, ".png")
    return base64.b64encode(img_bytes).decode('utf-8')

def get_raw_text(blk_list: list[TextBlock]):
    rw_txts_dict = {}
    for idx, blk in enumerate(blk_list):
        block_key = f"block_{idx}"
        rw_txts_dict[block_key] = blk.text
    
    raw_texts_json = json.dumps(rw_txts_dict, ensure_ascii=False, indent=4)
    
    return raw_texts_json

def get_raw_translation(blk_list: list[TextBlock]):
    rw_translations_dict = {}
    for idx, blk in enumerate(blk_list):
        block_key = f"block_{idx}"
        rw_translations_dict[block_key] = blk.translation
    
    raw_translations_json = json.dumps(rw_translations_dict, ensure_ascii=False, indent=4)
    
    return raw_translations_json

def _repair_json(text: str) -> str:
    """Undo the syntax slips language models make most often.

    Only ever applied after a strict parse failed, so it can be blunt.
    """
    repaired = text
    # Smart quotes used as JSON delimiters
    repaired = repaired.replace("\u201c", '"').replace("\u201d", '"')
    # Python literals JSON does not accept
    repaired = re.sub(r"\bNone\b", "null", repaired)
    repaired = re.sub(r"\bTrue\b", "true", repaired)
    repaired = re.sub(r"\bFalse\b", "false", repaired)
    # Trailing commas before a closing brace or bracket
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired


def _loads_relaxed(response: str) -> dict | None:
    """Parse the JSON an LLM returned for a batch of text blocks.

    Free and local models wrap the object in prose or markdown, use smart
    quotes, or leave a trailing comma. Each of those costs a whole page, so
    try a few shapes before giving up.
    """
    candidates = [response.strip()]

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", response, re.IGNORECASE)
    if fenced:
        candidates.append(fenced.group(1).strip())

    # Prefer the outermost object when the response also contains commentary.
    braced = re.search(r"\{[\s\S]*\}", response)
    if braced:
        candidates.append(braced.group(0))

    for candidate in candidates:
        if not candidate:
            continue
        for attempt in (candidate, _repair_json(candidate)):
            try:
                parsed = json.loads(attempt)
            except (ValueError, TypeError):
                continue
            if isinstance(parsed, dict):
                return parsed
    return None


def set_texts_from_json(blk_list: list[TextBlock], json_string: str) -> bool:
    """Apply the model's JSON translation back onto the blocks.

    Returns False when nothing usable could be parsed, so the caller can report
    the failure instead of silently rendering empty bubbles.
    """
    translation_dict = _loads_relaxed(json_string)
    if translation_dict is None:
        logger.warning("No JSON translation found in the model response")
        return False

    missing = 0
    for idx, blk in enumerate(blk_list):
        block_key = f"block_{idx}"
        if block_key in translation_dict:
            value = translation_dict[block_key]
            blk.translation = value if isinstance(value, str) else str(value)
        else:
            missing += 1

    if missing:
        logger.warning("%d of %d blocks missing from the model response",
                       missing, len(blk_list))
    return missing < len(blk_list)

def set_upper_case(blk_list: list[TextBlock], upper_case: bool):
    for blk in blk_list:
        translation = blk.translation
        if translation is None:
            continue
        if upper_case and not translation.isupper():
            blk.translation = translation.upper() 
        elif not upper_case and translation.isupper():
            blk.translation = translation.lower().capitalize()
        else:
            blk.translation = translation

def format_translations(blk_list: list[TextBlock], trg_lng_cd: str, upper_case: bool = True):
    for blk in blk_list:
        translation = blk.translation
        if translation is None:
            continue
        if upper_case and not translation.isupper():
            blk.translation = translation.upper()
        elif not upper_case and translation.isupper():
            blk.translation = translation.lower().capitalize()
        else:
            blk.translation = translation

def is_there_text(blk_list: list[TextBlock]) -> bool:
    return any(blk.text for blk in blk_list)

def has_translatable_content(text: str | None) -> bool:
    """True when source text contains a letter or number worth translating."""
    if not text:
        return False
    return any(ch.isalnum() for ch in text)

def is_renderable_translation(translation: str | None) -> bool:
    """True if the render stage should draw this translation.

    Punctuation-only translations (an echoed "?", "!?", "...") aren't worth
    redrawing — the original artwork already shows the same thing. Anything
    gated on rendering (like inpainting) must skip them too, otherwise the
    bubble gets cleaned with nothing drawn over it. Unlike a length check,
    this keeps legitimate single-character translations (e.g. "何", "5").
    """
    return has_translatable_content(translation)
