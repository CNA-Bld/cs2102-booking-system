import datetime

from google.appengine.ext import ndb


class BookTime():
    def __init__(self, data={i: False for i in range(0, 48)}, reversed=False):
        self.data = data
        if reversed:
            self.data = {i: not self.data[i] for i in range(0, 48)}

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
        return union


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
    def apply_filter(cls, location, type, capacity):
        query = cls.query()
        if location:
            query = query.filter(cls.location == location)
        if type:
            query = query.filter(cls.type == type)
        if capacity:
            query = query.filter(cls.capacity >= capacity)
        return query

    def check_availability(self, date):
        bookings = Book.find_booking(self, date)
        available_time = BookTime()
        for booking in bookings:
            book_time = BookTime(booking.time)
            available_time = available_time.union(book_time)
        if date.weekday() == 5:
            available_time = available_time.union(self.sat_hr)
        elif date.weekday() == 6:
            available_time = available_time.union(self.sun_hr)
        else:
            available_time = available_time.union(self.weekday_hr)
        return available_time


class Book(ndb.Model):
    date = ndb.DateProperty()
    time = ndb.JsonProperty()
    purpose = ndb.StringProperty()
    comment = ndb.StringProperty()
    is_cancelled = ndb.BooleanProperty()
    is_approved = ndb.BooleanProperty()
    is_processed = ndb.BooleanProperty()
    managed_by = ndb.StringProperty()
    facility_id = ndb.KeyProperty()
    user_id = ndb.KeyProperty()

    @classmethod
    def find_booking(cls, facility, date):
        query = cls.query(cls.facility_id == facility, cls.date == date, is_cancelled == False)
        return query

    def check(self):
        facility = self.facility_id.get()
        available_time = facility.check_availability(self.date)
        if available_time.is_conflicted(BookTime(self.time)):
            return False
        return facility.min_adv_time <= (datetime.date.today() - self.date).days <= facility.max_adv_time

    def place(self):
        if not self.check():
            return False
        else:
            if self.facility_id.get().is_auto_approval:
                self.is_approved = True
                self.is_processed = True
            self.put()
