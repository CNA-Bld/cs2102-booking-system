import datetime
from google.appengine.ext import ndb

import utils

class BookTime():
    def __init__(self, data=None):
        if data is not None:
            self.data = data
        else:
            self.data = {i: False for i in range(0, 48)}

    def __repr__(self):
        return repr(self.data)

    def is_conflicted(self, other):
        for i in range(0, 48):
            if self.data[i] and other.data[i]:
                return True
        return False

    def union(self, other):
        union = BookTime()
        for i in range(0, 48):
            if self.data[i] or other.data[i]:
                union.data[i] = True
            else:
                union.data[i] = False
        return union

    def inverted(self):
        inv = BookTime()
        for i in range(0, 48):
            inv.data[i] = not self.data[i]
        return inv

    def to_list(self):
        l = []
        for i in range(0, 48):
            l.append(self.data[i])
        return l

    @classmethod
    def create_opening_hours(cls, start, end):
        data = {i: False for i in range(0, 48)}
        for i in range(start*2, end*2):
            data[i] = True
        return BookTime(data).inverted()


class User(ndb.Model):
    user_id = ndb.StringProperty()
    name = ndb.StringProperty()
    faculty = ndb.StringProperty()
    year = ndb.IntegerProperty()
    email = ndb.StringProperty()

    @classmethod
    def get_user_by_id(cls, user_id):
        try:
            user = cls.query(cls.user_id == user_id).get()
            return user
        except IndexError:
            return None

    @classmethod
    def create_new_user(cls, user_id, name, faculty, year, email):
        user = User(user_id=user_id, name=name, faculty=faculty, year=year, email=email)
        user.put()
        return user

    @classmethod
    def update_user(cls, user_id, name, faculty, year, email):
        year = int(year)
        user = cls.get_user_by_id(user_id)
        if user is not None:
            user.name = name
            user.faculty = faculty
            user.year = year
            user.email = email
            return user
        else:
            return cls.create_new_user(user_id, name, faculty, year, email)


class Facility(ndb.Model):
    location = ndb.StringProperty()
    type = ndb.StringProperty()
    room_number = ndb.StringProperty()
    is_auto_approval = ndb.BooleanProperty()
    weekday_hr = ndb.JsonProperty()
    sat_hr = ndb.JsonProperty()
    sun_hr = ndb.JsonProperty()
    max_time_per_day = ndb.IntegerProperty()
    price_per_hr = ndb.FloatProperty()
    min_adv_time = ndb.IntegerProperty()
    max_adv_time = ndb.IntegerProperty()
    capacity = ndb.IntegerProperty()
    comment = ndb.StringProperty()

    @classmethod
    def init(cls):
        ins = cls()
        ins.location = 'COM1'
        ins.type = 'Programming Lab'
        ins.room_number = 'B111'
        ins.is_auto_approval = False
        ins.weekday_hr = repr(BookTime())
        ins.sat_hr = repr(BookTime())
        ins.sun_hr = repr(BookTime())
        ins.max_time_per_day = 8
        ins.price_per_hr = 0.0
        ins.min_adv_time = 0
        ins.max_adv_time = 7
        ins.capacity = 40
        ins.comment = '?'
        ins.put()

    @classmethod
    def apply_filter(cls, location, type, capacity, date):
        query = cls.query()
        query = query.filter(cls.location == location)
        if type:
            query = query.filter(cls.type == type)
        adv_time = (date - utils.get_today_plus_8()).days
        query = query.filter(cls.min_adv_time <= adv_time)
        result = query.fetch()
        for facility in result:
            if facility.max_adv_time < adv_time or facility.capacity < capacity:
                result.remove(facility)
        return result

    def check_availability(self, date):
        bookings = Book.find_booking(self, date)
        available_time = BookTime()
        for booking in bookings:
            book_time = BookTime(eval(booking.time))
            available_time = available_time.union(book_time)
        if date.weekday() == 5:
            available_time = available_time.union(BookTime(eval(self.sat_hr)))
        elif date.weekday() == 6:
            available_time = available_time.union(BookTime(eval(self.sun_hr)))
        else:
            available_time = available_time.union(BookTime(eval(self.weekday_hr)))
        return available_time

    @classmethod
    def get_loc_list(cls):
        query = cls.query().fetch()
        loc_list = []
        for f in query:
            if f.location not in loc_list:
                loc_list.append(f.location)
        return loc_list

    @classmethod
    def get_type_list(cls):
        query = cls.query().fetch()
        type_list = []
        for f in query:
            if f.type not in type_list:
                type_list.append(f.type)
        return type_list


class Book(ndb.Model):
    date = ndb.DateProperty()
    time = ndb.JsonProperty()
    purpose = ndb.StringProperty()
    comment = ndb.StringProperty()
    is_cancelled = ndb.BooleanProperty()
    is_approved = ndb.BooleanProperty()
    is_processed = ndb.BooleanProperty()
    facility_id = ndb.KeyProperty()
    user_id = ndb.KeyProperty()

    @classmethod
    def init(cls):
        b = Book()
        b.date = utils.get_today_plus_8()
        tmp = {i: False for i in range(0, 48)}
        tmp[16] = True
        b.time = repr(tmp)
        b.purpose = 'purpose'
        b.comment = 'comment'
        b.facility_id = Facility.query().get().key
        b.user_id = User.query().get().key
        b.place()

    @classmethod
    def find_booking(cls, facility, date):
        query = cls.query(cls.facility_id == facility.key, cls.date == date, cls.is_cancelled != True)
        return query.fetch()

    def check(self):
        facility = self.facility_id.get()
        available_time = facility.check_availability(self.date)
        if available_time.is_conflicted(BookTime(eval(self.time))):
            return False
        return facility.min_adv_time <= (self.date - utils.get_today_plus_8()).days <= facility.max_adv_time

    def place(self):
        if not self.check():
            return False
        else:
            if self.facility_id.get().is_auto_approval:
                self.is_approved = True
                self.is_processed = True
                self.is_cancelled = False
            else:
                self.is_approved = False
                self.is_processed = False
                self.is_cancelled = False
            self.put()

    def approve(self):
        self.is_processed = True
        self.is_approved = True
        self.put()

    def decline(self):
        self.is_processed = True
        self.is_approved = False
        self.is_cancelled = True
        self.put()

    def cancel(self):
        self.is_cancelled = True
        self.put()
