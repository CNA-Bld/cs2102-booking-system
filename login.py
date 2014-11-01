from const import *

import random
import json
import models

from google.appengine.api import memcache
from google.appengine.api import urlfetch


def generate_key():
    return ''.join(random.sample([chr(i) for i in range(48, 58) + range(65, 91) + range(97, 123)], 32))


def user_session_create(user, key=generate_key()):
    memcache.set(SESSION_PREFIX + user, key, 600)
    return key


def user_session_check(user, key):
    user_sessions = memcache.get(SESSION_PREFIX + user)
    if user_sessions == key:
        user_session_create(user, key)
        return True
    else:
        return False

def user_session_remove(user, key):
    try:
        if user_session_check(user, key):
            memcache.delete(SESSION_PREFIX + user)
    except:
        pass


def get_user_info(token):
    json_data = urlfetch.fetch(url='https://ivle.nus.edu.sg/api/Lapi.svc/Profile_View?APIKey=%s&AuthToken=%s' % (IVLE_API_KEY, token), method=urlfetch.GET).content
    data = json.loads(json_data)['Results'][0]

    user = models.User.update_user(data['UserID'], data['Name'], data['Faculty'], data['MatriculationYear'], data['Email'])
    return user
