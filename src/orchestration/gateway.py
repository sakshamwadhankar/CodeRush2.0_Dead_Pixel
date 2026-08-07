import json
import os
import re
import urllib.request
import urllib.error
from typing import Dict, Any, Type, TypeVar, Optional
from pydantic import BaseModel, ValidationError

from src.orchestration.state_controller import StateController
from src.orchestration.state_models import LogLevel, SeverityLevel

T = TypeVar("T", bound=BaseModel)


class ModelGatewayError(Exception):
    """Custom exception raised when ModelGateway fails to produce valid structured output."""
    pass


class ModelGateway:
    """
    Multi-Model LLM Gateway for Aegis Research OS.
    Supports local Ollama (Gemma models) and Google Gemini API endpoints.
    Enforces strict JSON schema validation, automated retries, and fallback routing.
    """

    def __init__(self, state_filepath: Optional[str] = None):
        self.state_controller = StateController(state_filepath=state_filepath)

    def _get_config(self) -> Dict[str, Any]:
        """Retrieves user configuration settings from state.json."""
        state = self.state_controller.get_state()
        return state.user_config.model_dump()

    def _extract_json(self, raw_text: str) -> Dict[str, Any]:
        """
        Extracts JSON dictionary from raw model text response.
        Handles raw JSON, markdown ```json blocks, and embedded JSON objects.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty response received from LLM model endpoint.")

        cleaned = raw_text.strip()

        # 1. Try stripping markdown ```json ... ``` codeblock
        markdown_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
        if markdown_match:
            cleaned = markdown_match.group(1).strip()

        # 2. Try direct JSON parsing
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # 3. Regex fallback to isolate first '{' to last '}'
        json_bounds = re.search(r"(\{[\s\S]*\})", cleaned)
        if json_bounds:
            try:
                parsed = json.loads(json_bounds.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract valid JSON object from model output: '{raw_text[:120]}...'")

    def _build_system_prompt(self, response_model: Type[BaseModel], user_instructions: Optional[str] = None) -> str:
        """
        Wraps user instructions with strict JSON schema definitions.
        """
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        base = (
            "You are an AI research engine operating within the Aegis Research OS security framework.\n"
            "CRITICAL INSTRUCTION: You MUST output ONLY valid JSON matching the exact JSON Schema specified below.\n"
            "Do NOT include markdown explanations outside the JSON object.\n\n"
            f"REQUIRED JSON SCHEMA:\n{schema_json}\n"
        )
        if user_instructions:
            base += f"\nADDITIONAL SYSTEM INSTRUCTIONS:\n{user_instructions}\n"
        return base

    def _call_ollama(
        self, prompt: str, system_prompt: str, model_name: str, base_url: str, timeout: int = 25
    ) -> str:
        """
        Sends generation request to local Ollama instance with format='json'.
        """
        endpoint = f"{base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model_name,
            "prompt": prompt,
            "system": system_prompt,
            "format": "json",
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body.get("response", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama local endpoint connection failed ({endpoint}): {e}")

    def _call_gemini(self, prompt: str, system_prompt: str, model_name: str, timeout: int = 25) -> str:
        """
        Sends generation request to Google Gemini API free endpoint using GEMINI_API_KEY environment variable.
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Fall back to checking OS keyring if environment variable is absent
            try:
                import keyring
                api_key = keyring.get_password("aegis_research_os", "GEMINI_API_KEY")
            except Exception:
                pass

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is missing.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\nUSER PROMPT:\n{prompt}"}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                candidates = body.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
                raise ValueError("Gemini API returned an empty completion candidate.")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Gemini API request failed: {e}")

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instructions: Optional[str] = None,
        max_retries: int = 3,
        fallback_on_failure: bool = True,
    ) -> T:
        """
        Executes prompt against configured LLM provider, enforcing Pydantic schema validation.
        Includes automatic self-correcting retry loop and provider fallback handling.
        """
        cfg = self._get_config()
        provider = cfg.get("model_provider", "ollama").lower()
        ollama_model = cfg.get("ollama_model", "gemma4:latest")
        gemini_model = cfg.get("gemini_model", "gemini-1.5-flash")
        ollama_base_url = cfg.get("ollama_base_url", "http://localhost:11434")
        timeout = cfg.get("sandbox_timeout_seconds", 30)

        system_prompt = self._build_system_prompt(response_model, system_instructions)
        current_prompt = prompt

        for attempt in range(1, max_retries + 1):
            raw_response = ""
            try:
                if provider == "ollama":
                    raw_response = self._call_ollama(
                        prompt=current_prompt,
                        system_prompt=system_prompt,
                        model_name=ollama_model,
                        base_url=ollama_base_url,
                        timeout=timeout,
                    )
                elif provider == "gemini":
                    raw_response = self._call_gemini(
                        prompt=current_prompt,
                        system_prompt=system_prompt,
                        model_name=gemini_model,
                        timeout=timeout,
                    )
                else:
                    raise ValueError(f"Unsupported model provider '{provider}'. Must be 'ollama' or 'gemini'.")

                # Parse JSON and validate against Pydantic schema
                parsed_json = self._extract_json(raw_response)
                validated_obj = response_model.model_validate(parsed_json)
                
                self.state_controller.log_system_event(
                    level=LogLevel.INFO,
                    component="ModelGateway",
                    message=f"Successfully generated structured output ({response_model.__name__}) via {provider}",
                    metadata={"attempt": attempt, "provider": provider},
                )
                return validated_obj

            except (RuntimeError, ValueError, ValidationError, json.JSONDecodeError) as err:
                error_msg = f"Attempt {attempt}/{max_retries} failed via {provider}: {err}"
                self.state_controller.log_system_event(
                    level=LogLevel.WARNING,
                    component="ModelGateway",
                    message=error_msg,
                    metadata={"attempt": attempt, "error": str(err)},
                )

                if attempt < max_retries:
                    # Self-correcting retry prompt feedback
                    current_prompt = (
                        f"{prompt}\n\n"
                        f"CORRECTION FEEDBACK (Attempt {attempt} failed):\n"
                        f"Your previous JSON response was invalid. Error details: {err}\n"
                        f"Please output ONLY valid JSON matching the schema."
                    )
                else:
                    # Final attempt failed for primary provider -> Trigger Fallback
                    if fallback_on_failure and provider != "gemini":
                        self.state_controller.log_system_event(
                            level=LogLevel.WARNING,
                            component="ModelGateway",
                            message=f"Primary provider '{provider}' exhausted retries. Attempting fallback to Gemini...",
                        )
                        try:
                            gemini_raw = self._call_gemini(prompt, system_prompt, gemini_model, timeout)
                            parsed = self._extract_json(gemini_raw)
                            return response_model.model_validate(parsed)
                        except Exception as fb_err:
                            self.state_controller.log_system_event(
                                level=LogLevel.ERROR,
                                component="ModelGateway",
                                message=f"Fallback provider also failed: {fb_err}",
                            )

                    raise ModelGatewayError(
                        f"ModelGateway failed to produce valid {response_model.__name__} structured output after {max_retries} retries: {err}"
                    )
