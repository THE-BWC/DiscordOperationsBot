import os

if 'DEVELOPMENT' in os.environ:
    from dotenv import load_dotenv
    load_dotenv()

# Discord bot token
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Statuses
STATUS = ["the operations"]

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Database
XENFORO_DB_HOST = os.getenv('XENFORO_DB_HOST')
XENFORO_DB_PORT = os.getenv('XENFORO_DB_PORT')
XENFORO_DB_NAME = os.getenv('XENFORO_DB_NAME')
XENFORO_DB_USER = os.getenv('XENFORO_DB_USER')
XENFORO_DB_PASS = os.getenv('XENFORO_DB_PASS')

# Bot settings
OPSEC_CHANNELS_MAP = {
    "16": "844204862844829717"
}
BOT_DB_NAME = "botdb"
