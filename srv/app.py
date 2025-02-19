import re
import logging
import pymongo
from tornado import web
from tornado.log import access_log as log
from srv.base import BASE_DIR, path, PyMongoError
from tornado.options import define, options
from yaml import load as load_yml, SafeLoader

define('port', default=8000, help='run port', type=int)
define('debug', default=True, help='the debug mode', type=bool)
define('test_db', default=True, help='check database connection', type=bool)


class Application(web.Application):
    def __init__(self, handlers, **p):
        with open(path.join(BASE_DIR, 'app.yml'), encoding='utf-8') as f:
            self.config = load_yml(f, Loader=SafeLoader)
        self.site = self.config['site']

        super(Application, self).__init__(
            handlers,
            debug=options.debug,
            login_url='/user/login',
            cookie_secret=self.config['cookie_secret'],
            log_function=self.log_function,
            compiled_template_cache=False,
            static_path=path.join(BASE_DIR, 'assets'),
            template_path=path.join(BASE_DIR, 'views'), **p)

        try:
            self.conn, self.db = self._connect_db(self.config['database'])
            if options.test_db:
                self.db.user.count_documents({})
        except PyMongoError as e:
            logging.error(re.sub(r'\..+$', '', str(e)))
            self.stop()

    def stop(self):
        if self.conn:
            self.conn.close()
            self.conn = self.db = None

    @staticmethod
    def log_function(handler):
        summary = handler._request_summary()
        s = handler.get_status()
        if s != 404 and not(s < 400 and re.search(r'/static', summary)):
            user = handler.current_user
            summary = re.sub(r'\(.+\)', '(' + handler.get_ip() + ')', summary)
            request_time = int(1000 * handler.request.request_time())
            cls = re.split("[.']", str(handler.__class__))[-2]
            log_method = log.info if s < 400 else log.warning if s < 500 else log.error
            log_method("%d %s %s %d ms%s", s, summary, cls, request_time,
                       user and ' [%s]' % user.get('username') or '')

    @staticmethod
    def _connect_db(d):
        usr = f"{d['user']}:{d['password']}@" if d.get('user') else ''
        uri = f"mongodb://{usr}{d['host']}:{d['port']}" + (f"/{d['name']}" if usr else '')
        conn = pymongo.MongoClient(
            uri, connectTimeoutMS=2000, serverSelectionTimeoutMS=2000,
            maxPoolSize=8, waitQueueTimeoutMS=5000, connect=False)
        return conn, conn[d['name']]
