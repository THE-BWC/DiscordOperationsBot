from peewee import (
    Model,
    MySQLDatabase,
    IntegerField,
    CharField,
    BooleanField,
    ForeignKeyField,
    TextField,
)
import settings


db = MySQLDatabase(
    settings.XENFORO_DB_NAME,
    user=settings.XENFORO_DB_USER,
    password=settings.XENFORO_DB_PASS,
    host=settings.XENFORO_DB_HOST,
    port=int(settings.XENFORO_DB_PORT),
)


class User(Model):
    """XenForo user model"""

    user_id = IntegerField(primary_key=True)
    username = CharField()

    class Meta:
        database = db
        table_name = "xf_user"


class Game(Model):
    """Opserv game model as it currently exists in the opserv_games table"""

    game_id = IntegerField(primary_key=True)
    tag = CharField()
    game_name = CharField()
    retired = BooleanField()

    class Meta:
        database = db
        table_name = "opserv_games"


class Operation(Model):
    """Opserv operation model as it currently exists in the opserv_operations table"""

    operation_id = IntegerField(primary_key=True)
    operation_name = CharField()
    is_completed = BooleanField()
    date_start = IntegerField()
    date_end = IntegerField()
    leader_user_id = ForeignKeyField(User)
    game_id = ForeignKeyField(Game)
    description = TextField()
    discord_voice_channel_id = CharField()
    discord_event_location = CharField()
    is_opsec = BooleanField()
    edited_date = IntegerField()

    class Meta:
        database = db
        table_name = "opserv_operations"
