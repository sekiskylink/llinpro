#!/usr/bin/python
# Author: Samuel Sekiwere <sekiskylink@gmail.com>

import os
import sys
import web
import urllib
import logging
# import requests
from web.contrib.template import render_jinja

filedir = os.path.dirname(__file__)
sys.path.append(os.path.join(filedir))


class AppURLopener(urllib.FancyURLopener):
    version = "LLIN /1.0"

urllib._urlopener = AppURLopener()

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/llin_sms.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)
urls = (
    "/cgi-bin/sendsms", "Sendsms",
    "/test", "Test"
)

app = web.application(urls, globals())

# web.config.smtp_server = 'mail.mydomain.com'
web.config.debug = False
render = render_jinja(
    'templates',
    encoding='utf-8'
)


class Sendsms:
    def GET(self):
        params = web.input(fuuid='', district='')
        print params
        return "Accepted"

    def POST(self):
        pass


class Test:
    def GET(self):
        web.header('Content-Type', 'application/json')
        return '{"id": "6Wb675BHMU", "name": "Samuel"}'


if __name__ == "__main__":
    app.run()

# makes sure apache wsgi sees our app
application = web.application(urls, globals()).wsgifunc()
