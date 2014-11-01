import datetime

import webapp2
from google.appengine.ext.webapp import template

import login
import models
import utils
from const import *


base_template_values = {}


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
                    {'location': facility.location, 'type': facility.type, 'capacity': facility.capacity,
                     'price': facility.price_per_hr, 'comment': facility.comment,
                     'room_number': facility.room_number, 'id': facility.key.id(),
                     'availability': facility.check_availability(date).inverted().data} for facility in facilities]
                facilities_dict_list.sort(key=lambda x: x['location'] + x['type'] + x['room_number'])
            else:
                is_querying = False
                facilities_dict_list = []
            native_values = {'location_list': models.Facility.get_loc_list(), 'query_string': self.request.query_string,
                             'type_list': models.Facility.get_type_list(), 'selected_date': date.strftime("%d-%m-%Y"),
                             'selected_location': location, 'selected_type': facility_type, 'is_querying': is_querying,
                             'selected_capacity': capacity, 'facility_list': facilities_dict_list, 'user': user}
            template_values = dict(base_template_values, **native_values)
            # self.response.out.write(template_values)

            path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/login/')


class AdminHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {'user': 'Dummy Admin System'}
        if self.request.get('do') == 'create_facility':
            path = os.path.join(os.path.dirname(__file__), 'templates/admin_create_facility.html')
        else:
            path = os.path.join(os.path.dirname(__file__), 'templates/admin_main.html')
        self.response.out.write(template.render(path, template_values))

    def post(self):
        if self.request.get('do') == 'create_facility':
            facility = models.Facility()
            facility.location = self.request.get('location')
            facility.type = self.request.get('type')
            facility.room_number = self.request.get('room_number')
            if self.request.get('is_auto_approval'):
                facility.is_auto_approval = True
            else:
                facility.is_auto_approval = False
            facility.max_time_per_day = int(self.request.get('max_time_per_day'))
            print self.request.get('price_per_hr')
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
        self.redirect('/admin/')


app = webapp2.WSGIApplication([
                                  ('/login/.*', LoginHandler),
                                  ('/logout/.*', LogoutHandler),
                                  ('/admin/.*', AdminHandler),
                                  ('/.*', MainHandler),
                              ], debug=True)
