#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The only file which is directly executed. There's no reason to modify this
file.
"""

import web
import logging
from settings import DEBUG
from urls import URLS
from app.tools.app_processor import (header_html, notfound, internalerror)
from app.controllers import db, put_session, put_app

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/llin-web.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)

web.config.debug = DEBUG

app = web.application(URLS, globals(), autoreload=False)
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={'loggedin': False})
put_session(session)

app.notfound = notfound
app.internalerror = internalerror
app.add_processor(web.loadhook(header_html))

if __name__ == '__main__':
    put_app(app)
    app.run()

application = app.wsgifunc()
