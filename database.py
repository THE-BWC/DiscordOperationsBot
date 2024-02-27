import settings
from peewee import Model, MySQLDatabase, IntegerField, CharField, BooleanField, DateTimeField


xenforo = MySQLDatabase(
    settings.XENFORO_DB_NAME,
    user=settings.XENFORO_DB_USER,
    password=settings.XENFORO_DB_PASSWORD,
    host=settings.XENFORO_DB_HOST,
    port=int(settings.XENFORO_DB_PORT)
)


class Operation(Model):
    operation_id = IntegerField(primary_key=True)
    operation_name = CharField()
    is_completed = BooleanField()
    type_id = IntegerField()
    date_start = DateTimeField()
    date_end = DateTimeField()
    leader_user_id = IntegerField()
    game_id = IntegerField()
    is_opsec = BooleanField()

    class Meta:
        database = xenforo
        table_name = "opserv_operations"
