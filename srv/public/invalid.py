import re
from srv.base import BaseHandler, PyMongoError

re_err = re.compile(r'\.(yml|yaml|env|git|json|secret)|'
                    r'(config|settings|credential|secrets)\.js', re.I)


class Page404Handler(BaseHandler):
    """404页面"""

    def prepare(self):
        pass

    def get(self):
        try:
            sec = '.'.join(self.get_ip().split('.')[:2])
            if sec != '127.0' and self.db.blocklist.find_one({'section': sec}):
                self.send_raise_failed('page not found', code=404)
            self.log(f'{self.request.path} not found', 'W')
            if sec != '127.0' and re_err.search(self.request.path):
                count = self.db.blocklist.count_documents({})
                if count == 0:
                    self.db.blocklist.create_index('section', name='sec', unique=True)
                self.db.blocklist.update_one({'section': sec}, {'$set': dict(
                    ip=self.get_ip(), created=self.now(), path=self.request.path)}, upsert=True)
                self.log(f'{self.get_ip()} and {count} sections blocked')
        except PyMongoError:
            pass
        self.set_status(404, reason='Not found')
        if self.is_api:
            return self.finish()
        self.render('_404.html')

    def post(self):
        return self.get()
