import os
from typing import Tuple, List
from dotenv import load_dotenv


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
GUILD_ID = 0
BOT_DB_NAME = "botdb"

# Game/channels map data.
OPSEC = 1
PUBLIC = 0
OPSEC_CHANNELS_MAP = {}


def get_channel_notifications(channel_id: int) -> List[Tuple[int, int, str]]:
    """Return the current notifications defined for the given channel"""
    results: List[Tuple[int, int]] = []
    for game_id, data in OPSEC_CHANNELS_MAP.items():
        for is_opsec, channels in data.items():
            results.extend([(game_id, is_opsec, cron) for channel, cron in channels.items() if channel == channel_id])

    return results


def remove_notification(game_id: int, is_opsec: int, channel_id: int) -> bool:
    """
    Removes the notification matching the arguments
    :returns bool - True if the entry was removed
    """
    game_map = OPSEC_CHANNELS_MAP.get(game_id, None)
    if game_map is None:
        return False

    opsec_map = game_map.get(is_opsec, None)
    if opsec_map is None:
        return False

    channel = opsec_map.get(channel_id, None)
    if channel is None:
        return False

    del OPSEC_CHANNELS_MAP[game_id][is_opsec][channel_id]
    return True


def update_notification(game_id: int, is_opsec: int, channel_id: int, cron_str: str) -> int:
    """
    Update or add a new entry in the channels map
    :returns int - 1 if it's new 0 if it's an old entry
    """
    is_new = 1
    game_map = OPSEC_CHANNELS_MAP.get(game_id, None)
    if game_map is None:
        game_map = {}

    opsec_map = game_map.get(is_opsec, None)

    if opsec_map is None:
        opsec_map = {}
        game_map[is_opsec] = opsec_map

    channel = opsec_map.get(channel_id, None)

    if channel is None:
        game_map[is_opsec] = {channel_id: cron_str}
    else:
        game_map[is_opsec][channel_id] = cron_str
        # since the channel exist we need to update this
        is_new = 0

    OPSEC_CHANNELS_MAP[game_id] = game_map
    return is_new
