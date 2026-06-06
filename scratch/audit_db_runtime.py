import os
import sys

from src.config import settings
from src.database.connection import engine

print("1. ENV DATABASE_URL:", os.getenv("DATABASE_URL"))
print("2. settings.DATABASE_URL:", settings.DATABASE_URL)
print("3. Engine dialect:", engine.dialect.name)
print("4. Engine URL:", str(engine.url).replace(settings.DATABASE_URL.split("://")[1].split("@")[0], "*****") if "@" in str(engine.url) else str(engine.url))

# Check connection pool
print("5. Engine Pool:", engine.pool)
