"""Load a dossier file: {"company", "session_date", "evidence": [...]}"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..schemas import Evidence


def load_dossier(path: Path) -> tuple[str, date, list[Evidence]]:
    data = json.loads(Path(path).read_text())
    return (data["company"], date.fromisoformat(data["session_date"]),
            [Evidence.model_validate(e) for e in data["evidence"]])
