import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", "1265652628"))
    DB_PATH: str = "barbershop.db"
    TIMEZONE: str = "Asia/Tashkent"

config = Config()