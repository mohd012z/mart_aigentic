"""Safe multi-platform campaign orchestration: draft -> approval -> ready.
No network requests, credentials, or automatic publishing.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4
from social_agent import PLATFORMS, draft

VALID = {"draft": {"review"}, "review": {"approved", "rejected"}, "approved": {"ready", "rejected"}, "ready": set(), "rejected": set()}

@dataclass
class Campaign:
    id: str
    owner_id: int
    product: str
    platforms: List[str]
    drafts: Dict[str, dict]
    status: str = "draft"
    history: list = field(default_factory=list)

    def transition(self, next_status: str, actor_id: int):
        if actor_id != self.owner_id:
            raise PermissionError("Only the owner can change this campaign")
        if next_status not in VALID[self.status]:
            raise ValueError("Invalid campaign state transition")
        if next_status == "ready" and any(not x["requires_review"] for x in self.drafts.values()):
            raise ValueError("Invalid approval state")
        self.history.append({"from": self.status, "to": next_status, "actor": actor_id,
                             "at": datetime.now(timezone.utc).isoformat()})
        self.status = next_status
        return self.status

def new_campaign(owner_id: int, product: str, platforms: List[str], facts: str = "", affiliate: bool = False):
    if not isinstance(owner_id, int) or owner_id <= 0:
        raise ValueError("Invalid owner")
    if not platforms or len(platforms) > len(PLATFORMS) or len(set(platforms)) != len(platforms):
        raise ValueError("Invalid platform selection")
    drafts = {p: draft(p, product, facts, affiliate) for p in platforms}
    return Campaign(uuid4().hex, owner_id, product, list(platforms), drafts)

def publish(campaign: Campaign):
    raise PermissionError("Publishing is disabled until official OAuth authorization, permission checks and live tests pass")
