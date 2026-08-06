"""Multi-agent market hunt: global LONG/SHORT scouts → AI specialists → orchestrator."""

from app.agents.orchestrator import AgentOrchestrator, orchestrator
from app.agents.scouts import build_scout_roster
from app.agents.universes import default_universes

__all__ = [
    "AgentOrchestrator",
    "orchestrator",
    "build_scout_roster",
    "default_universes",
]
