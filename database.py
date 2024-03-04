from peewee import Model, MySQLDatabase, IntegerField, CharField, BooleanField, DateTimeField, ForeignKeyField, \
    SqliteDatabase
import settings


xenforo = MySQLDatabase(
    settings.XENFORO_DB_NAME,
    user=settings.XENFORO_DB_USER,
    password=settings.XENFORO_DB_PASSWORD,
    host=settings.XENFORO_DB_HOST,
    port=int(settings.XENFORO_DB_PORT)
)

bot = SqliteDatabase(settings.BOT_DB_NAME)


class User(Model):
    """Xenforo user model"""
    user_id = IntegerField(primary_key=True)
    username = CharField()

    class Meta:
        database = xenforo
        table_name = "xf_user"


class Game(Model):
    """Opserv game model as it currently exists in the opserv_games table"""
    game_id = IntegerField(primary_key=True)
    tag = CharField()
    game_name = CharField()
    retired = BooleanField()

    class Meta:
        database = xenforo
        table_name = "opserv_games"


class Operation(Model):
    """Opserv operation model as it currently exists in the opserv_operations table"""
    operation_id = IntegerField(primary_key=True)
    operation_name = CharField()
    is_completed = BooleanField()
    type_id = IntegerField()
    date_start = DateTimeField()
    date_end = DateTimeField()
    leader_user_id = ForeignKeyField(User)
    game_id = ForeignKeyField(Game)
    is_opsec = BooleanField()

    class Meta:
        database = xenforo
        table_name = "opserv_operations"


class Notification30(Model):
    """Notification model for the 30 reminder sent for operations"""
    operation_id = IntegerField(primary_key=True)
    date_start = DateTimeField()

    class Meta:
        database = bot


# Make sure the database exists and the schemas are created
bot.connect()
bot.create_tables([Notification30])
