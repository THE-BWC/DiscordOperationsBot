import os
from dotenv import load_dotenv

from operation_message import OperationMessageOptions

load_dotenv()

# Discord bot token
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Statuses
STATUS = ["the operations"]

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "DEBUG"

# Database
XENFORO_DB_HOST = os.getenv('XENFORO_DB_HOST')
XENFORO_DB_PORT = os.getenv('XENFORO_DB_PORT')
XENFORO_DB_NAME = os.getenv('XENFORO_DB_NAME')
XENFORO_DB_USER = os.getenv('XENFORO_DB_USER')
XENFORO_DB_PASSWORD = os.getenv('XENFORO_DB_PASSWORD')

# Bot settings
OPSEC_CHANNELS_MAP = {
    "16": "1212157407598223470"
}
BOT_DB_NAME = "botdb"

NOTIFICATION_OPTIONS = {
    'UPCOMING_OPS': OperationMessageOptions(),
    '30MIN_OPS': OperationMessageOptions(show_game=False, show_date_end=False, include_timestamp=False)
}
