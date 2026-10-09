from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class BotConfig:
    token: str = field(repr=False)
    models: Path = Path("models")
    work: Path = Path(".cache/jobs")
    queue_size: int = 10
    cooldown: float = 5
    history_limit: int = 50
    download_timeout: float = 20
    process_timeout: float = 60
    upload_timeout: float = 30
    max_download: int = 25*1024*1024
    max_output: int = 8*1024*1024
    max_side: int = 1024
    max_people: int = 20
    guild_ids: frozenset[int] = frozenset()
    channel_ids: frozenset[int] = frozenset()

    @classmethod
    def from_env(cls):
        def number(name, default, minimum, maximum, converter=int):
            try:
                value = converter(os.getenv(name, str(default)))
                if not minimum <= value <= maximum:
                    raise ValueError()
                return value
            except ValueError:
                raise ValueError(f"Invalid value for {name}.") from None

        def ids(name):
            try:
                values = frozenset(int(value.strip()) for value in os.getenv(name, "").split(",") if value.strip())
                if any(value <= 0 for value in values):
                    raise ValueError()
                return values
            except ValueError:
                raise ValueError(f"{name} must be a list of positive IDs.") from None

        token = os.getenv("DISCORD_TOKEN", "").strip()
        if not token:
            raise ValueError("DISCORD_TOKEN is missing. Set it in .env or as an environment variable.")
        return cls(token=token, models=Path(os.getenv("MODEL_DIR", "models")).resolve(),
                   work=Path(os.getenv("WORK_DIR", ".cache/jobs")).resolve(),
                   queue_size=number("QUEUE_SIZE", 10, 1, 100),
                   cooldown=number("USER_COOLDOWN_SECONDS", 5, 0, 3600, float),
                   history_limit=number("HISTORY_LIMIT", 50, 1, 200),
                   download_timeout=number("DOWNLOAD_TIMEOUT_SECONDS", 20, 1, 120, float),
                   process_timeout=number("PROCESS_TIMEOUT_SECONDS", 60, 1, 600, float),
                   upload_timeout=number("UPLOAD_TIMEOUT_SECONDS", 30, 1, 120, float),
                   max_download=number("MAX_DOWNLOAD_BYTES", 25*1024*1024, 1024, 25*1024*1024),
                   max_output=number("MAX_OUTPUT_BYTES", 8*1024*1024, 1024, 25*1024*1024),
                   max_side=number("DETECTION_MAX_SIDE", 1024, 128, 2048),
                   max_people=number("MAX_PEOPLE", 20, 1, 50),
                   guild_ids=ids("ALLOWED_GUILD_IDS"), channel_ids=ids("ALLOWED_CHANNEL_IDS"))
