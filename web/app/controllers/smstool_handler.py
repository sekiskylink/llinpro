from . import require_login, render


class SMSTool:
    @require_login
    def GET(self):
        l = locals()
        del l['self']
        return render.smstool(**l)
