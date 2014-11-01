import os

if os.environ['SERVER_SOFTWARE'].startswith('Development'):
    APP_PATH = 'http://localhost:8080/'
else:
    APP_PATH = 'http://booking.softstar.org/'

SESSION_PREFIX = 'session_'

IVLE_API_KEY = "rZ43ZYiyDPeEHlzz40zJS"
