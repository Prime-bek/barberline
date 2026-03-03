import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"  # Замените на свой токен
    MASTER_ID: int = 1265652628
    ADMIN_ID: int = 1265652628
    DB_PATH: str = "barbershop.db"
    TIMEZONE: str = "Asia/Tashkent"

config = Config()