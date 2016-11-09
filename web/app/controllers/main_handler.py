# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import render
from . import csrf_protected, db, get_session, put_session
from app.tools.utils import auth_user


class Index:
    def GET(self):
        l = locals()
        del l['self']
        return render.login(**l)

    @csrf_protected
    def POST(self):
        session = get_session()
        params = web.input(username="", password="")
        username = params.username
        password = params.password
        r = auth_user(db, username, password)
        if r[0]:
            session.loggedin = True
            info = r[1]
            session.username = info.firstname + " " + info.lastname
            session.sesid = info.id
            session.role = info.role
            put_session(session)

            l = locals()
            del l['self']
            if info.role == 'Warehouse Manager':
                return web.seeother("/warehousedata")
            elif info.role == 'Micro Planning':
                return web.seeother("/reporters")
            else:
                return web.seeother("/dashboard")
        else:
            session.loggedin = False
            session.logon_err = r[1]
        l = locals()
        del l['self']
        return render.logon(**l)


class Logout:
    def GET(self):
        session = get_session()
        session.kill()
        return web.seeother("/")
