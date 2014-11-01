import datetime

def get_today_plus_8():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).date()
