import json
from pathlib import Path

from jarvis.memory.models import Memory
from jarvis.memory.serialization import memory_from_dict, memory_to_dict


class FileMemoryStore:
    def __init__(self, directory: Path):
        self._directory = directory
        self._directory.mkdir(parents=True, exist_ok=True)

    def save(self, memory: Memory) -> None:
        path = self._path_for(memory.memory_id)

        data = memory_to_dict(memory)

        path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def get(self, memory_id: str) -> Memory | None:
        path = self._path_for(memory_id)

        if not path.exists():
            return None

        data = json.loads(
            path.read_text(encoding="utf-8")
        )

        return memory_from_dict(data)

    def exists(self, memory_id: str) -> bool:
        return self._path_for(memory_id).exists()

    def delete(self, memory_id: str) -> None:
        path = self._path_for(memory_id)

        if path.exists():
            path.unlink()

    def _path_for(self, memory_id: str) -> Path:
        return self._directory / f"{memory_id}.json"