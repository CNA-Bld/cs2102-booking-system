import webapp2

import login
from const import *


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
        pass

app = webapp2.WSGIApplication([
                                  ('/', MainHandler),
                                  ('/login/.*', LoginHandler)
                              ], debug=True)
