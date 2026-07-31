from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:8501",
    "http://127.0.0.1:8501",
)
DEFAULT_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
SUPPORTED_UPLOAD_SUFFIXES = {".pdf"}
INVALID_FILENAME_CHARS = set('<>:"/\\|?*\x00')


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class RuntimeSettings:
    data_dir: Path
    upload_dir: Path
    allowed_origins: tuple[str, ...]
    max_upload_bytes: int

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "RuntimeSettings":
        base = (base_dir or Path(__file__).resolve().parent).resolve()
        origins = tuple(
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
            if origin.strip()
        )
        return cls(
            data_dir=_resolve_path(os.getenv("DATA_DIR", "./data"), base),
            upload_dir=_resolve_path(os.getenv("UPLOAD_DIR", "./temp_uploads"), base),
            allowed_origins=origins or DEFAULT_ALLOWED_ORIGINS,
            max_upload_bytes=_positive_int(
                os.getenv("MAX_UPLOAD_BYTES"), DEFAULT_MAX_UPLOAD_BYTES
            ),
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload_path(self, filename: str | None) -> Path:
        raw_name = (filename or "").strip()
        if not raw_name:
            raise ValueError("A filename is required.")
        if any(char in INVALID_FILENAME_CHARS or ord(char) < 32 for char in raw_name):
            raise ValueError("The filename contains unsupported characters.")
        if Path(raw_name).name != raw_name:
            raise ValueError("The filename must not contain a directory path.")
        if Path(raw_name).suffix.lower() not in SUPPORTED_UPLOAD_SUFFIXES:
            raise ValueError("Only PDF uploads are supported.")

        destination = (self.upload_dir / raw_name).resolve()
        if destination.parent != self.upload_dir.resolve():
            raise ValueError("The upload path is outside the configured directory.")
        return destination

