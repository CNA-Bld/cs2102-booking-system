import datetime


def get_today_plus_8():
    return get_time_plus_8().date()


def get_time_plus_8():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)
