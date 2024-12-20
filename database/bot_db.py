from peewee import (
    Model,
    MySQLDatabase,
    IntegerField,
    CharField,
)
import settings


db = MySQLDatabase(
    settings.BOT_DB_NAME,
    user=settings.BOT_DB_USER,
    password=settings.BOT_DB_PASS,
    host=settings.BOT_DB_HOST,
    port=int(settings.BOT_DB_PORT),
)


class DiscordEvents(Model):
    """Discord events model"""

    event_id = CharField(null=False)
    operation_id = IntegerField(primary_key=True)
    operation_edited_date = IntegerField(null=False)

    class Meta:
        database = db
        table_name = "discord_events"


class Operations(Model):
    """Operations model"""

    operation_id = IntegerField(primary_key=True)
    operation_name = CharField(null=False)
    is_completed = IntegerField(null=False)
    type_name = CharField(null=False)
    date_start = IntegerField(null=False)
    date_end = IntegerField(null=False)
    leader_username = CharField(null=False)
    tag = CharField(null=False)
    game_id = IntegerField(null=False)
    game_name = CharField(null=False)
    edited_date = IntegerField(null=False)
    notified = IntegerField(null=False, default=0)

    class Meta:
        database = db


# Make sure the database exists and the schemas are created
db.connect()
db.create_tables([DiscordEvents])
