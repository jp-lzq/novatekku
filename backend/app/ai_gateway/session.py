from datetime import date
from typing import Dict, Any

AI_SESSION_MAX = 10
AI_HISTORY_MAX_MESSAGES = 8
AI_SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_session_state(session_id: str) -> Dict[str, Any]:
    today = date.today().isoformat()
    state = AI_SESSIONS.get(session_id)
    if not state or state.get("date") != today:
        state = {"date": today, "count": 0, "history": []}
        AI_SESSIONS[session_id] = state
    return state
