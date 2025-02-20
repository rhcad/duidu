from srv.base import BaseHandler


class Page404Handler(BaseHandler):
    """404页面"""

    def prepare(self):
        pass

    def get(self):
        self.log(f'{self.request.path} not found', 'W')
        self.set_status(404, reason='Not found')
        if self.is_api:
            return self.finish()
        self.render('_404.html')

    def post(self):
        return self.get()
