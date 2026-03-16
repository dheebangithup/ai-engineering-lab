import json
import os
import time
from typing import List, Dict, Any, Optional
from config import logger

class SessionManager:
    """
    Manages persistence of conversation sessions, including titles, 
    timestamps, and full event history (messages and flow steps).
    """
    def __init__(self, storage_path: str = "sessions.json"):
        self.storage_path = storage_path
        self.sessions = self._load_sessions()

    def _load_sessions(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
                return {}
        return {}

    def _save_sessions(self):
        try:
            with open(self.storage_path, "w") as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def create_or_update_session(self, session_id: str, title: str = None):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "title": title or "New Conversation",
                "created_at": time.time(),
                "updated_at": time.time(),
                "history": []
            }
        else:
            if title:
                self.sessions[session_id]["title"] = title
            self.sessions[session_id]["updated_at"] = time.time()
        self._save_sessions()

    def add_event(self, session_id: str, event: Dict[str, Any]):
        if session_id not in self.sessions:
            self.create_or_update_session(session_id)
        
        self.sessions[session_id]["history"].append(event)
        self.sessions[session_id]["updated_at"] = time.time()
        
        # Simple heuristic to auto-generate title if it's the first user message
        if event.get("type") == "user_question" and self.sessions[session_id]["title"] == "New Conversation":
            # Trim the question for the title
            title = event["content"][:40] + ("..." if len(event["content"]) > 40 else "")
            self.sessions[session_id]["title"] = title
            
        self._save_sessions()

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Returns a list of sessions sorted by most recent."""
        session_list = [
            {
                "id": s["id"],
                "title": s["title"],
                "updated_at": s["updated_at"]
            }
            for s in self.sessions.values()
        ]
        return sorted(session_list, key=lambda x: x["updated_at"], reverse=True)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            self._save_sessions()
