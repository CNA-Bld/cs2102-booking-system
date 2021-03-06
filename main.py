import datetime

import webapp2
import jinja2

import login
import models
import utils
from const import *


base_template_values = {}

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates/')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


class LoginHandler(webapp2.RequestHandler):
    def get(self):
        if 'callback' in self.request.path:
            user = login.get_user_info(self.request.get('token'))
            key = login.user_session_create(user.user_id)
            self.response.headers.add_header('Set-Cookie', str('user=' + user.user_id + '; path=/'))
            self.response.headers.add_header('Set-Cookie', str('session_key=' + key + '; path=/'))
            self.response.out.write('<script type="text/javascript">window.location.href="/";</script>')
        else:
            self.redirect('https://ivle.nus.edu.sg/api/login/?apikey=%s&url=%s' % (
                IVLE_API_KEY, APP_PATH + 'login/callback/'))


class LogoutHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        login.user_session_remove(user, key)
        self.redirect('/')


class MainHandler(webapp2.RequestHandler):
    def get(self):
        if self.request.get('offset'):
            date = datetime.datetime.strptime(self.request.get('date'), "%d-%m-%Y").date()
            date += datetime.timedelta(days=int(self.request.get('offset')))
            self.redirect("/?date=%s&location=%s&type=%s&capacity=%s" % (
                date.strftime("%d-%m-%Y"), self.request.get("location"), self.request.get("type"),
                self.request.get("capacity")))
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            try:
                date = datetime.datetime.strptime(self.request.get('date'), "%d-%m-%Y").date()
            except ValueError:
                date = utils.get_today_plus_8()
            location = self.request.get('location')
            facility_type = self.request.get('type')
            try:
                capacity = int(self.request.get('capacity'))
            except ValueError:
                capacity = 0
            if location:
                is_querying = True
                facilities = models.Facility.apply_filter(location, facility_type, capacity, date)
                facilities_dict_list = [
                    dict(facility.to_dict(),
                         **{'availability': facility.check_availability(date).inverted().to_dict_list()})
                    for facility in facilities]
                facilities_dict_list = [facility for facility in facilities_dict_list if facility['availability']]
                facilities_dict_list.sort(key=lambda x: x['location'] + x['type'] + x['room_number'])
            else:
                is_querying = False
                facilities_dict_list = []
            location_list = models.Facility.get_loc_list()
            sorted_location_list = sorted(location_list.keys())
            sorted_type_list = []
            for types in location_list.values():
                sorted_type_list += types
            sorted_type_list = sorted(list(set(sorted_type_list)))
            native_values = {'location_list': location_list, 'sorted_location_list': sorted_location_list,
                             'type_list': sorted_type_list, 'selected_date': date.strftime("%d-%m-%Y"),
                             'selected_location': location, 'selected_type': facility_type, 'is_querying': is_querying,
                             'selected_capacity': capacity, 'facility_list': facilities_dict_list,
                             'weekday': date.strftime("%A"), 'query_string': self.request.query_string,
                             'error': self.request.get('error'), 'user': user}
            template_values = dict(base_template_values, **native_values)
            # self.response.out.write(template_values)

            template = JINJA_ENVIRONMENT.get_template('user_main.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')


class ManageHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            if self.request.get('cancel'):
                booking = models.Book.get_by_book_id(int(self.request.get('cancel')))
                if booking.user_id.get().user_id != user:
                    self.response.set_status(403, "Unauthorized!")
                    return
                else:
                    booking.cancel()
            bookings = models.Book.find_user_booking(models.User.get_user_by_id(user))
            bookings_dict_list = [booking.to_dict() for booking in bookings]

            native_values = {'booking_list': bookings_dict_list, 'user': user}
            template_values = dict(base_template_values, **native_values)
            # self.response.out.write(template_values)

            template = JINJA_ENVIRONMENT.get_template('user_manage_bookings.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')


class ViewBookingHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            booking = models.Book.get_by_book_id(int(self.request.get('id')))
            if booking.user_id.get().user_id != user:
                self.response.set_status(403, "Unauthorized!")
                return
            native_values = {'user': user, 'booking': booking.to_dict(), 'is_admin': False}

            template_values = dict(base_template_values, **native_values)

            template = JINJA_ENVIRONMENT.get_template('shared_booking_details.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')

    def post(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            booking = models.Book.get_by_book_id(int(self.request.get('id')))
            if booking.user_id.get().user_id != user:
                self.response.set_status(403, "Unauthorized!")
                return
            else:
                booking.purpose = self.request.get('purpose')
                booking.comment = self.request.get('comment')
                booking.put()
                self.redirect('./?id=%s' % self.request.get('id'))
        else:
            self.redirect('/login/')


class NewBookingHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            facility = models.Facility.get_by_facility_id(int(self.request.get('id')))
            date = datetime.datetime.strptime(self.request.get('date'), "%d-%m-%Y").date()

            start_slot = int(self.request.get('start'))
            end_slot = int(self.request.get('end'))

            native_values = {'user': user, 'date': date.strftime("%d-%m-%Y"), 'facility': facility.to_dict(),
                             'facility_str': facility.to_string(), 'start_slot': start_slot, 'end_slot': end_slot,
                             'max_slot': facility.max_time_per_day * 2, 'id': self.request.get('id'),
                             'price': facility.price_per_hr, 'is_auto_approval': facility.is_auto_approval}

            template_values = dict(base_template_values, **native_values)

            template = JINJA_ENVIRONMENT.get_template('user_new_booking.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')

    def post(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            facility = models.Facility.get_by_facility_id(int(self.request.get('id')))
            date = datetime.datetime.strptime(self.request.get('date'), "%d-%m-%Y").date()

            start_slot = utils.str_to_slot(self.request.get('start_time'))
            end_slot = utils.str_to_slot(self.request.get('end_time'))

            time = models.BookTime.create_booking_time(start_slot, end_slot)

            booking = models.Book(date=date, purpose=self.request.get('purpose'), comment=self.request.get('comment'),
                                  facility_id=facility.key, user_id=models.User.get_user_by_id(user).key,
                                  time=time.data)

            if booking.place():
                self.redirect('/manage/')
            else:
                self.redirect('/?error=Something went wrong, please try again.')
        else:
            self.redirect('/login/')


class FacilityDetailsHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            facility = models.Facility.get_by_facility_id(int(self.request.get('id')))
            native_values = {'user': user, 'facility': facility.to_dict()}

            template_values = dict(base_template_values, **native_values)

            template = JINJA_ENVIRONMENT.get_template('user_facility_details.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')


class FacilityListHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):

            native_values = {'user': user,
                             'is_admin': False,
                             'facility_list': [facility.to_dict() for facility in models.Facility.get_all()]}

            template_values = dict(base_template_values, **native_values)

            template = JINJA_ENVIRONMENT.get_template('user_facilities.html')
            self.response.write(template.render(template_values))
        else:
            self.redirect('/login/')


class AdminHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {'user': 'Dummy Admin System', 'is_admin': True}
        if self.request.get('do') == 'create_facility':
            template_values['facility'] = models.Facility()
            template = JINJA_ENVIRONMENT.get_template('admin_create_facility.html')
        elif self.request.get('do') == 'manage_facilities':
            template_values['facility_list'] = [facility.to_dict() for facility in models.Facility.get_all()]
            template = JINJA_ENVIRONMENT.get_template('admin_manage_facilities.html')
        elif self.request.get('do') == 'update_facility':
            template_values['facility'] = models.Facility.get_by_facility_id(int(self.request.get('id'))).to_dict()
            template = JINJA_ENVIRONMENT.get_template('admin_update_facility.html')
        elif self.request.get('do') == 'approve_booking':
            models.Book.get_by_book_id(int(self.request.get('id'))).approve()
            self.redirect('./?do=manage_bookings')
            return
        elif self.request.get('do') == 'decline_booking':
            models.Book.get_by_book_id(int(self.request.get('id'))).decline()
            self.redirect('./?do=manage_bookings')
            return
        elif self.request.get('do') == 'manage_bookings':
            template_values['booking_list'] = [book.to_dict() for book in
                                               models.Book.query().order(-models.Book.place_time).fetch()]
            template = JINJA_ENVIRONMENT.get_template('admin_manage_bookings.html')
        elif self.request.get('do') == 'view_booking':
            template_values['booking'] = models.Book.get_by_book_id(int(self.request.get('id'))).to_dict()
            template = JINJA_ENVIRONMENT.get_template('shared_booking_details.html')
        elif self.request.get('do') == 'manage_users':
            template_values['user_list'] = [
                dict(user.to_dict(), **{'booking_count': len(models.Book.find_user_booking(user))}) for user in
                models.User.query().fetch()]
            template = JINJA_ENVIRONMENT.get_template('admin_manage_users.html')
        elif self.request.get('do') == 'view_user':
            user = models.User.get_user_by_id(self.request.get('id'))
            template_values['user_info'] = user.to_dict()
            template_values['booking_list'] = [booking.to_dict() for booking in models.Book.find_user_booking(user)]
            template = JINJA_ENVIRONMENT.get_template('admin_view_user.html')
        else:
            template = JINJA_ENVIRONMENT.get_template('admin_main.html')
        self.response.write(template.render(template_values))

    def post(self):
        if self.request.get('do') == 'update_facility':
            if self.request.get('id'):
                facility = models.Facility.get_by_facility_id(int(self.request.get('id')))
            else:
                facility = models.Facility()
            facility.location = self.request.get('location')
            facility.type = self.request.get('type')
            facility.room_number = self.request.get('room_number')
            if self.request.get('is_auto_approval'):
                facility.is_auto_approval = True
            else:
                facility.is_auto_approval = False
            facility.max_time_per_day = int(self.request.get('max_time_per_day'))
            facility.price_per_hr = float(self.request.get('price_per_hr'))
            facility.min_adv_time = int(self.request.get('min_adv_time'))
            facility.max_adv_time = int(self.request.get('max_adv_time'))
            facility.capacity = int(self.request.get('capacity'))
            facility.comment = self.request.get('comment')
            facility.weekday_hr = repr(models.BookTime.create_opening_hours(int(self.request.get('weekday_hr_start')),
                                                                            int(self.request.get('weekday_hr_end'))))
            facility.sat_hr = repr(models.BookTime.create_opening_hours(int(self.request.get('sat_hr_start')),
                                                                        int(self.request.get('sat_hr_end'))))
            facility.sun_hr = repr(models.BookTime.create_opening_hours(int(self.request.get('sun_hr_start')),
                                                                        int(self.request.get('sun_hr_end'))))
            facility.put()
            self.redirect('/admin/?do=manage_facilities')


app = webapp2.WSGIApplication([
                                  ('/login/.*', LoginHandler),
                                  ('/logout/.*', LogoutHandler),
                                  ('/manage/booking/.*', ViewBookingHandler),
                                  ('/manage/.*', ManageHandler),
                                  ('/new_booking/.*', NewBookingHandler),
                                  ('/facilities/details/.*', FacilityDetailsHandler),
                                  ('/facilities/.*', FacilityListHandler),
                                  ('/admin/.*', AdminHandler),
                                  ('/.*', MainHandler),
                              ], debug=True)
