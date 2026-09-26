"""Filesystem repository; replace this interface for SQLite/Firebase later."""
import json
from pathlib import Path
from uuid import UUID


class ResultStore:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def directory(self, report_id):
        # Canonical UUID prevents path traversal in report and artifact routes.
        return self.root / str(UUID(str(report_id)))

    def save(self, result):
        directory = self.directory(result["report_id"])
        temporary = directory / "result.tmp"
        temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
        temporary.replace(directory / "result.json")

    def load(self, report_id):
        return json.loads((self.directory(report_id) / "result.json").read_text(encoding="utf-8"))
