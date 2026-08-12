from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid


@dataclass
class SessionLogger:
    path: Path
    username: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def write(self, event: str, **fields: object) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_id": self.session_id,
            "username": self.username,
            "event": event,
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")