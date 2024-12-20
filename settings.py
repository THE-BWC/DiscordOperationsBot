import json
import os

if os.environ.get("BOT_ENV") == "development":
    from dotenv import load_dotenv

    load_dotenv()

# Discord bot token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is not set")

# Xenforo Database
XENFORO_DB_HOST = os.getenv("XENFORO_DB_HOST")
XENFORO_DB_PORT = os.getenv("XENFORO_DB_PORT")
XENFORO_DB_NAME = os.getenv("XENFORO_DB_NAME")
XENFORO_DB_USER = os.getenv("XENFORO_DB_USER")
XENFORO_DB_PASS = os.getenv("XENFORO_DB_PASS")
if (
    not XENFORO_DB_HOST
    or not XENFORO_DB_PORT
    or not XENFORO_DB_NAME
    or not XENFORO_DB_USER
    or not XENFORO_DB_PASS
):
    raise ValueError("Xenforo database settings are not set")

# Bot Database
BOT_DB_HOST = os.getenv("BOT_DB_HOST")
BOT_DB_PORT = os.getenv("BOT_DB_PORT")
BOT_DB_NAME = os.getenv("BOT_DB_NAME")
BOT_DB_USER = os.getenv("BOT_DB_USER")
BOT_DB_PASS = os.getenv("BOT_DB_PASS")
if (
    not BOT_DB_HOST
    or not BOT_DB_PORT
    or not BOT_DB_NAME
    or not BOT_DB_USER
    or not BOT_DB_PASS
):
    raise ValueError("Bot database settings are not set")

# Bot settings
GUILD_ID = int(os.getenv("GUILD_ID"))
if not GUILD_ID:
    raise ValueError("GUILD_ID is not set")

DISCORD_CLIENT_ID = int(os.getenv("DISCORD_CLIENT_ID"))
if not DISCORD_CLIENT_ID:
    raise ValueError("DISCORD_CLIENT_ID is not set")

# Statuses
STATUS = ["the operations"]

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Sentry DSN
SENTRY_DSN = os.getenv("SENTRY_DSN")
ENVIRONMENT = os.getenv("BOT_ENV", "production")
if ENVIRONMENT == "development":
    RELEASE = "development"
else:
    # TODO: Needs to be auto-incremented for each release
    RELEASE = os.getenv("RELEASE", "0.1.0")


class Settings:
    # Game/channels map data.
    OPSEC = "1"
    PUBLIC = "0"
    SETTINGS_FILENAME = "settings.json"

    opsec_channels_map: {int: {int: {int: str}}} = {}

    def __init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.SETTINGS_FILENAME):
            return

        with open(self.SETTINGS_FILENAME, encoding="utf-8") as settings_file:
            contents = json.load(settings_file)

        # move things to memory
        channels_map = contents.get("opsec_channels_map", {})
        self.opsec_channels_map = channels_map

    def save(self) -> None:
        with open(self.SETTINGS_FILENAME, "w", encoding="utf-8") as settings_file:
            settings_content = {"opsec_channels_map": self.opsec_channels_map}
            settings_file.write(json.dumps(settings_content, indent=2))

    def get_channel_notifications(self, channel_id: int) -> list[tuple[int, int, str]]:
        """Return the current notifications defined for the given channel"""
        results: list[tuple[int, int, str]] = []

        # because our json loads and saves with string ints, we have to work with str at this point
        channel_id_str = str(channel_id)
        for game_id, data in self.opsec_channels_map.items():
            for is_opsec, channels in data.items():
                results.extend(
                    [
                        (game_id, is_opsec, cron)
                        for channel, cron in channels.items()
                        if channel == channel_id_str
                    ]
                )

        return results

    def remove_notification(self, game_id: int, is_opsec: int, channel_id: int) -> bool:
        """
        Removes the notification matching the arguments
        :returns bool - True if the entry was removed
        """
        # because our json loads and saves with string ints, we have to work with str at this point
        game_id_str = str(game_id)
        is_opsec_str = str(is_opsec)
        channel_id_str = str(channel_id)
        game_map = self.opsec_channels_map.get(game_id_str, None)
        if game_map is None:
            return False

        opsec_map = game_map.get(is_opsec_str, None)
        if opsec_map is None:
            return False

        channel = opsec_map.get(channel_id_str, None)
        if channel is None:
            return False

        del self.opsec_channels_map[game_id_str][is_opsec_str][channel_id_str]
        self.save()
        return True

    def update_notification(
        self, game_id: int, is_opsec: int, channel_id: int, cron_str: str
    ) -> int:
        """
        Update or add a new entry in the channels map
        :returns int - 1 if it's new 0 if it's an old entry
        """
        # because our json loads and saves with string ints, we have to work with str at this point
        game_id_str = str(game_id)
        is_opsec_str = str(is_opsec)
        channel_id_str = str(channel_id)

        is_new = 1
        game_map = self.opsec_channels_map.get(game_id_str, None)
        if game_map is None:
            game_map = {}

        opsec_map = game_map.get(is_opsec_str, None)

        if opsec_map is None:
            opsec_map = {}
            game_map[is_opsec_str] = opsec_map

        channel = opsec_map.get(channel_id_str, None)
        if channel is not None:
            # since the channel exist we need to update this
            is_new = 0

        game_map[is_opsec_str][channel_id_str] = cron_str

        self.opsec_channels_map[game_id_str] = game_map
        self.save()
        return is_new
