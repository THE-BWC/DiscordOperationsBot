import datetime


class OpservTimezone(datetime.tzinfo):
    def utcoffset(self, __dt: datetime.datetime | None) -> datetime.timedelta | None:
        return datetime.timedelta(hours=-5)

    def dst(self, __dt: datetime.datetime | None) -> datetime.timedelta | None:
        return datetime.timedelta(hours=-1)

    def tzname(self, __dt: datetime.datetime | None) -> str | None:
        return 'America/New York'
