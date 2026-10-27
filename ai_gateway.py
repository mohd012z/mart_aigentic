"""Provider-neutral, bounded text generation for approved MART marketing drafts."""
import os
import httpx
from provider_registry import REGISTRY
class GatewayError(RuntimeError):pass
def clean_text(value):
    if not isinstance(value,str) or not value.strip() or len(value)>8000:
        raise ValueError("Prompt must contain 1-8000 characters")
    return value.strip()
async def generate(prompt,provider="openai_compatible",client=None):
    prompt=clean_text(prompt)
    if provider not in REGISTRY:raise GatewayError("Provider not allowlisted")
    p=REGISTRY[provider]
    key=os.getenv(p.key_env)
    model=os.getenv(p.model_env)
    if not key or not model:raise GatewayError("Provider credentials or model not configured")
    if provider=="local_gateway" and os.getenv("MART_ENABLE_LOCAL_GATEWAY")!="1":
        raise GatewayError("Local gateway is disabled")
    owned=client is None
    if owned:client=httpx.AsyncClient(timeout=25)
    try:
        response=await client.post(p.endpoint,headers={"Authorization":"Bearer "+key},
            json={"model":model,"messages":[{"role":"system","content":"Create truthful, clearly labeled marketing drafts. Do not invent product specifications, prices, reviews or commissions. Never claim publication."},{"role":"user","content":prompt}],"max_tokens":700,"temperature":0.5})
        response.raise_for_status()
        data=response.json()
        output=data["choices"][0]["message"]["content"]
        if not isinstance(output,str) or not output.strip():raise GatewayError("Empty model output")
        return output[:6000]
    except (httpx.HTTPError,KeyError,IndexError,TypeError,ValueError) as exc:
        raise GatewayError("Model request failed: "+type(exc).__name__) from exc
    finally:
        if owned:await client.aclose()
