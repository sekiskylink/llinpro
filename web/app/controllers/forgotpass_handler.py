import web
from . import csrf_protected, db, render


class ForgotPass:
    def GET(self):
        params = web.input()
        l = locals()
        del l['self']
        return render.forgot_password(**l)

    @csrf_protected
    def POST(self):
        params = web.input(email="")

        with db.transaction():
            pass
        l = locals()
        del l['self']
        return render.forgot_password(**l)
