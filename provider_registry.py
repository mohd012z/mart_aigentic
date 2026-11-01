"""Explicit allowlisted providers; no credential discovery or automatic access."""
import os
from dataclasses import dataclass
@dataclass(frozen=True)
class Provider:
    name:str
    endpoint:str
    key_env:str
    model_env:str
    capabilities:tuple
REGISTRY={
 "openai_compatible":Provider("openai_compatible","https://api.openai.com/v1/chat/completions","MART_LLM_API_KEY","MART_LLM_MODEL",("text","chat")),
 "local_gateway":Provider("local_gateway","http://127.0.0.1:8317/v1/chat/completions","MART_LOCAL_GATEWAY_KEY","MART_LOCAL_MODEL",("text","chat")),
}
def configured(name):
    if name not in REGISTRY:raise ValueError("Provider not allowlisted")
    p=REGISTRY[name]
    return bool(os.getenv(p.key_env) and os.getenv(p.model_env))
def status():
    return {name:{"configured":configured(name),"capabilities":p.capabilities} for name,p in REGISTRY.items()}
