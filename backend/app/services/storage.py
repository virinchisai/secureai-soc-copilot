import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    relative_path: str
    size_bytes: int
    sha256: str


class UploadStorage:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        user_id: str,
        document_id: str,
        filename: str,
        content: bytes,
    ) -> StoredUpload:
        user_dir = self.root_dir / self._safe_component(user_id)
        document_dir = user_dir / self._safe_component(document_id)
        document_dir.mkdir(parents=True, exist_ok=False)

        safe_filename = Path(filename).name
        destination = document_dir / safe_filename
        temporary = document_dir / f".{safe_filename}.{uuid4().hex}.tmp"

        try:
            with temporary.open("xb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            temporary.replace(destination)
        except Exception:
            shutil.rmtree(document_dir, ignore_errors=True)
            raise

        return StoredUpload(
            path=destination,
            relative_path=str(destination.relative_to(self.root_dir)),
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    def delete_document(self, user_id: str, document_id: str) -> None:
        document_dir = (
            self.root_dir
            / self._safe_component(user_id)
            / self._safe_component(document_id)
        )
        shutil.rmtree(document_dir, ignore_errors=True)

    @staticmethod
    def _safe_component(value: str) -> str:
        safe_value = "".join(
            character for character in value if character.isalnum() or character in "-_"
        )
        if not safe_value:
            raise ValueError("Invalid storage path component")
        return safe_value
