import datetime


def get_today_plus_8():
    return get_time_plus_8().date()


def get_time_plus_8():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)


def timeslot_tuple_to_js(t):
    return "new Date(0, 0, 0, %d, %d, 0), new Date(0, 0, 0, %d, %d, 0)" % (
        t[0] / 2, t[0] % 2 * 30, t[1] / 2, t[1] % 2 * 30)
