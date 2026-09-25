"""ChainForge custom provider; install Mini Jev's service package on PYTHONPATH.

The prompt is a JSON Mini Jev request, not a new model prompt template. All
typed fields and provenance are returned to ChainForge as an inspectable string.
Only the local API is used. This adapter does not generate or estimate scores.
"""
import json
import os
from dataclasses import asdict

from chainforge.providers import provider
from service import Client
from service.schema import decode_json, validate_request


@provider(name="Mini Jev typed API", emoji="🔎", rate_limit="sequential")
def mini_jev_typed_api(prompt: str, model=None, chat_history=None, **kwargs) -> str:
    if chat_history:
        raise ValueError("This stateless typed API adapter does not accept chat history")
    if model:
        raise ValueError("Set the model in the typed request, not a ChainForge model setting")
    if kwargs:
        raise ValueError("Unsupported settings: " + ", ".join(sorted(kwargs)))
    payload = decode_json(prompt.encode("utf-8"))
    validate_request(payload)
    with Client(os.environ.get("MINI_JEV_API_URL", "http://127.0.0.1:8765"), timeout=120) as client:
        result = client.system_one(**payload)
    return json.dumps({"request": payload, "response": asdict(result)},
                      ensure_ascii=False, allow_nan=False, sort_keys=True)
