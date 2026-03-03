import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    MASTER_ID: int = int(os.getenv("MASTER_ID", "0"))
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
    DB_PATH: str = os.getenv("DB_PATH", "barbershop.db")
    TIMEZONE: str = "Asia/Tashkent"

config = Config()