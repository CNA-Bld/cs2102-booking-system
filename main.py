import os
import datetime

import webapp2
from google.appengine.ext.webapp import template

import login
import models
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


class MainHandler(webapp2.RequestHandler):
    def get(self):
        user = self.request.cookies.get('user')
        key = self.request.cookies.get('session_key')
        if user is None:
            self.redirect('/login/')
        elif login.user_session_check(user, key):
            path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
            try:
                date = datetime.datetime.strptime(self.request.get('date'), "%d-%m-%Y").date()
            except ValueError:
                date = datetime.date.today()
            location = self.request.get('location')
            facility_type = self.request.get('type')
            try:
                capacity = int(self.request.get('capacity'))
            except ValueError:
                capacity = 0
            if location:
                facilities = models.Facility.apply_filter(location, facility_type, capacity)
                facilities_dict_list = []
                for facility in facilities:
                    f_dict = {'location': facility.location, 'type': facility.type, 'capacity': facility.capacity,
                              'price': facility.price_per_hr, 'comment': facility.comment,
                              'room_number': facility.room_number, 'id': facility.key.id()}
                    f_dict['availability'] = facility.check_availability(date).inverted().data
                    facilities_dict_list.append(f_dict)
            else:
                facilities_dict_list = []
            native_values = {'location_list': models.Facility.get_loc_list(),
                             'type_list': models.Facility.get_type_list(), 'selected_date': date.strftime("%d-%m-%y"),
                             'selected_location': location, 'selected_type': facility_type,
                             'selected_capacity': capacity, 'facility_list': facilities_dict_list}
            template_values = dict(base_template_values, **native_values)
            print template_values
            self.response.out.write(template.render(path, template_values))
        else:
            self.redirect('/login/')


class InitHandler(webapp2.RequestHandler):
    def get(self):
        models.Book.init()


app = webapp2.WSGIApplication([
                                  ('/login/.*', LoginHandler),
                                  ('/init/.*', InitHandler),
                                  ('/.*', MainHandler),
                              ], debug=True)
