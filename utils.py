import datetime


def get_today_plus_8():
    return get_time_plus_8().date()


def get_time_plus_8():
    return datetime.datetime.utcnow() + datetime.timedelta(hours=8)


def ending_time_fix(slotid):
    if slotid % 2 == 0:
        return slotid / 2 - 1, 59
    else:
        return slotid / 2, 29


def timeslot_tuple_to_js(t):
    return "new Date(0, 0, 0, %d, %d, 0), new Date(0, 0, 0, %d, %d, 59)" % (
        t[0] / 2, t[0] % 2 * 30, ending_time_fix(t[1])[0], ending_time_fix(t[1])[1])


def slot_to_str(slot):
    if slot % 2 == 0:
        return "%d:00" % (slot / 2)
    else:
        return "%d:30" % (slot / 2)


def str_to_slot(time_str):
    return 2 * int(time_str[:2]) + (1 if time_str[-2:] == '30' else 0)
