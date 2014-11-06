from google.appengine.ext import ndb

import utils


class BookTime():
    def __init__(self, data=None):
        if data is not None:
            self.data = data
        else:
            self.data = [False for i in range(0, 48)]

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

    @classmethod
    def create_opening_hours(cls, start, end):
        data = [True] * 48
        for i in range(start * 2, end * 2):
            data[i] = False
        return BookTime(data)

    @classmethod
    def create_booking_time(cls, start, end):
        data = [False] * 48
        for i in range(start, end):
            data[i] = True
        return BookTime(data)

    def to_single_opening_hrs(self):
        flag = False
        for i in self.data:
            if i:
                flag = True
                break
        if not flag:
            return {'start': 0, 'end': 0}
        start = 0
        end = 24
        for i in range(1, 48):
            if self.data[i] is True and self.data[i - 1] is False:
                end = i / 2
            if self.data[i] is False and self.data[i - 1] is True:
                start = i / 2
        return {'start': start, 'end': end}

    def to_single_range_str_bookings(self):
        start = 0
        end = 48
        for i in range(1, 48):
            if self.data[i] is True and self.data[i - 1] is False:
                start = i
            if self.data[i] is False and self.data[i - 1] is True:
                end = i
        return {'start': utils.slot_to_str(start), 'end': utils.slot_to_str(end)}

    def to_dict_list(self):
        dict_list = {}
        if self.data[0]:
            curr_start = 0
        for i in range(1, 48):
            if self.data[i] and not self.data[i - 1]:
                curr_start = i
            if not self.data[i] and self.data[i - 1]:
                curr_end = i
                dict_list["start=%d&end=%d" % (curr_start, curr_end)] = utils.timeslot_tuple_to_js(
                    (curr_start, curr_end))
        if self.data[47]:
            dict_list["start=%d&end=%d" % (curr_start, 48)] = utils.timeslot_tuple_to_js((curr_start, 48))
        return dict_list


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

    def to_dict(self):
        return {'user_id': self.user_id, 'name': self.name, 'email': self.email, 'faculty': self.faculty,
                'year': self.year}


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
    def apply_filter(cls, location, type, capacity, date):
        query = cls.query()
        query = query.filter(cls.location == location)
        if type:
            query = query.filter(cls.type == type)
        adv_time = (date - utils.get_today_plus_8()).days
        query = query.filter(cls.min_adv_time <= adv_time)
        result = []
        for facility in query.fetch():
            if not ((facility.max_adv_time < adv_time) or (facility.capacity < capacity)):
                result.append(facility)
        return result

    def check_availability(self, date):
        bookings = Book.find_booking(self, date)
        available_time = BookTime()
        for booking in bookings:
            book_time = BookTime(booking.time)
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
        loc_list = {}
        for f in query:
            if f.location not in loc_list:
                loc_list[f.location] = []
            if f.type not in loc_list[f.location]:
                loc_list[f.location].append(f.type)
        return loc_list

    @classmethod
    def get_type_list(cls):
        query = cls.query().fetch()
        type_list = []
        for f in query:
            if f.type not in type_list:
                type_list.append(f.type)
        type_list.sort()
        return type_list

    @classmethod
    def get_by_facility_id(cls, facility_id):
        return ndb.Key(cls, facility_id).get()

    @classmethod
    def get_all(cls):
        return cls.query().order(cls.location, cls.type, cls.room_number).fetch()

    def to_string(self):
        return "%s %s (%s)" % (self.location, self.room_number, self.type)

    def construct_stat(self):
        bookings = Book.get_all_bookings(self)
        stat_dict = {'total_bookings': len(bookings), 'faculty_breakdown': {}, 'status_breakdown': {}}
        for booking in bookings:
            if booking.get_status() in stat_dict['status_breakdown']:
                stat_dict['status_breakdown'][booking.get_status()] += 1
            else:
                stat_dict['status_breakdown'][booking.get_status()] = 1
            user = booking.user_id.get()
            if user.faculty in stat_dict['faculty_breakdown']:
                stat_dict['faculty_breakdown'][user.faculty] += 1
            else:
                stat_dict['faculty_breakdown'][user.faculty] = 1
        return stat_dict

    def to_dict(self):
        return {'location': self.location, 'type': self.type, 'room_number': self.room_number,
                'is_auto_approval': self.is_auto_approval,
                'weekday_hr': BookTime(eval(self.weekday_hr)).to_single_opening_hrs(),
                'sat_hr': BookTime(eval(self.sat_hr)).to_single_opening_hrs(),
                'sun_hr': BookTime(eval(self.sun_hr)).to_single_opening_hrs(),
                'max_time_per_day': self.max_time_per_day,
                'price_per_hr': self.price_per_hr, 'min_adv_time': self.min_adv_time, 'max_adv_time': self.max_adv_time,
                'capacity': self.capacity, 'comment': self.comment, 'id': self.key.id(), 'stat': self.construct_stat()}


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
    place_time = ndb.DateTimeProperty()

    @classmethod
    def find_booking(cls, facility, date):
        query = cls.query(cls.facility_id == facility.key, cls.date == date, cls.is_cancelled != True)
        return query.fetch()

    @classmethod
    def get_all_bookings(cls, facility):
        query = cls.query(cls.facility_id == facility.key)
        return query.fetch()

    @classmethod
    def find_user_booking(cls, user):
        query = cls.query(cls.user_id == user.key).order(-cls.place_time)
        return query.fetch()

    @classmethod
    def get_by_book_id(cls, book_id):
        return ndb.Key(cls, book_id).get()

    def check(self):
        facility = self.facility_id.get()
        available_time = facility.check_availability(self.date)
        if available_time.is_conflicted(BookTime(self.time)):
            return False
        return facility.min_adv_time <= (self.date - utils.get_today_plus_8()).days <= facility.max_adv_time

    def place(self):
        if not self.check():
            return False
        else:
            self.place_time = utils.get_time_plus_8()
            if self.facility_id.get().is_auto_approval:
                self.is_approved = True
                self.is_processed = True
                self.is_cancelled = False
            else:
                self.is_approved = False
                self.is_processed = False
                self.is_cancelled = False
            self.put()
            return True

    def approve(self):
        self.is_processed = True
        self.is_approved = True
        self.is_cancelled = False
        self.put()

    def decline(self):
        self.is_processed = True
        self.is_approved = False
        self.is_cancelled = True
        self.put()

    def cancel(self):
        self.is_cancelled = True
        self.is_processed = False
        self.is_approved = False
        self.put()

    def get_status(self):
        if self.is_processed:
            if self.is_approved:
                return 'Approved'
            else:
                return 'Declined'
        else:
            if self.is_cancelled:
                return 'Cancelled'
            else:
                return 'Processing'

    def to_dict(self):
        return {'facility_str': self.facility_id.get().to_string(),
                'facility_id': self.facility_id.id(),
                'date': self.date.strftime("%d-%m-%Y"),
                'is_approved': self.is_approved, 'is_processed': self.is_processed,
                'is_cancelled': self.is_cancelled,
                'is_declined': self.is_processed and not self.is_approved,
                'id': self.key.id(), 'comment': self.comment, 'purpose': self.purpose,
                'booking_user': self.user_id.get().to_dict(),
                'time': BookTime(self.time).to_single_range_str_bookings(),
                'place_time': self.place_time.strftime("%d-%m-%Y %H:%M:%S")}
