from typing import Any
import numpy as np
import requests

from .base import BaseLLMTranslation
from ...utils import http_client
from ...utils.translator_utils import MODEL_MAP


class GPTTranslation(BaseLLMTranslation):
    """Translation engine using OpenAI GPT models through direct REST API calls."""
    
    def __init__(self):
        super().__init__()
        self.model_name = None
        self.api_key = None
        self.api_base_url = "https://api.openai.com/v1"
        self.supports_images = True
        # OpenAI renamed max_tokens to max_completion_tokens; local servers and
        # hosted free tiers generally only understand the older name.
        self.token_param = "max_completion_tokens"
    
    def initialize(self, settings: Any, source_lang: str, target_lang: str, model_name: str, **kwargs) -> None:
        """
        Initialize GPT translation engine.
        
        Args:
            settings: Settings object with credentials
            source_lang: Source language name
            target_lang: Target language name
            model_name: GPT model name
        """
        super().initialize(settings, source_lang, target_lang, **kwargs)
        
        self.model_name = model_name
        credentials = settings.get_credentials(settings.ui.tr('Open AI GPT'))
        self.api_key = credentials.get('api_key', '')
        self.model = MODEL_MAP.get(self.model_name)
    
    def _perform_translation(self, user_prompt: str, system_prompt: str, image: np.ndarray) -> str:
        """
        Perform translation using direct REST API calls to OpenAI.
        
        Args:
            user_prompt: Text prompt from user
            system_prompt: System instructions
            image: Image as numpy array
            
        Returns:
            Translated text
        """
        headers = {
            "Content-Type": "application/json"
        }
        # Local servers reject an empty bearer token, so only send it if a key
        # was actually configured.
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        if self.supports_images and self.img_as_llm_input:
            # Use the base class method to encode the image
            encoded_image, mime_type = self.encode_image(image)
            
            messages = [
                {
                    "role": "system", 
                    "content": [{"type": "text", "text": system_prompt}]
                },
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"}}
                    ]
                }
            ]
        else:
            messages = [
                {
                    "role": "system", 
                    "content": [{"type": "text", "text": system_prompt}]
                },
                {
                    "role": "user", 
                    "content": [{"type": "text", "text": user_prompt}]
                }
            ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        return self._make_api_request(payload, headers)

    def _make_api_request(self, payload, headers):
        """
        Make API request and process response
        """
        url = f"{self.api_base_url}/chat/completions"
        body = {**payload, self.token_param: self.max_tokens}

        try:
            response = http_client.request(
                "POST", url, headers=headers, json_body=body, timeout=self.timeout
            )

            if response.status_code == 400 and self.token_param != "max_tokens":
                # Older OpenAI-compatible servers (llama.cpp, most local
                # runtimes) only understand the legacy field name.
                body = {k: v for k, v in body.items() if k != self.token_param}
                body["max_tokens"] = self.max_tokens
                response = http_client.request(
                    "POST", url, headers=headers, json_body=body, timeout=self.timeout
                )

            if not response.ok:
                raise RuntimeError(
                    f"API request failed: {http_client.describe_error(response)}")

            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg += f" - {http_client.describe_error(e.response)}"
                except Exception:
                    error_msg += f" - Status code: {e.response.status_code}"
            raise RuntimeError(error_msg)
