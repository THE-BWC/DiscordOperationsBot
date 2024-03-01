import settings
from peewee import Model, MySQLDatabase, IntegerField, CharField, BooleanField, DateTimeField, ForeignKeyField


xenforo = MySQLDatabase(
    settings.XENFORO_DB_NAME,
    user=settings.XENFORO_DB_USER,
    password=settings.XENFORO_DB_PASSWORD,
    host=settings.XENFORO_DB_HOST,
    port=int(settings.XENFORO_DB_PORT)
)

# TODO: need to set the correct table_name override and complete with other relevant fields
class User(Model):
    id = IntegerField(primary_key=True)
    name = CharField()

    class Meta:
        database = xenforo


class Operation(Model):
    operation_id = IntegerField(primary_key=True)
    operation_name = CharField()
    is_completed = BooleanField()
    type_id = IntegerField()
    date_start = DateTimeField()
    date_end = DateTimeField()
    leader_user_id = ForeignKeyField(User)
    game_id = IntegerField()
    is_opsec = BooleanField()

    class Meta:
        database = xenforo
        table_name = "opserv_operations"
