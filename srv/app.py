import re
import logging
import pymongo
from tornado import web
from tornado.log import access_log as log
from srv.base import BASE_DIR, path, DbError
from tornado.options import define, options
from yaml import load as load_yml, SafeLoader

define('port', default=8000, help='run port', type=int)
define('debug', default=True, help='the debug mode', type=bool)
define('test_db', default=True, help='check database connection', type=bool)


class Application(web.Application):
    def __init__(self, handlers, **p):
        fn, fn0 = path.join(BASE_DIR, 'app.yml'), path.join(BASE_DIR, 'app_.yml')
        with open(fn if path.exists(fn) else fn0, encoding='utf-8') as f:
            self.config = load_yml(f, Loader=SafeLoader)
        self.site = self.config['site']
        self.version = '0.1.0316'

        super(Application, self).__init__(
            handlers,
            debug=options.debug,
            login_url='/user/login',
            cookie_secret=self.config['cookie_secret'],
            log_function=self.log_function,
            compiled_template_cache=False,
            static_path=path.join(BASE_DIR, 'assets'),
            template_path=path.join(BASE_DIR, 'views'), **p)

        self.conn = self.db = None
        self._init_db(self.config['database'])

    def _init_db(self, db_cfg):
        try:
            self.conn, self.db = self._connect_db(db_cfg)
            if options.test_db:
                self.db.user.count_documents({})
        except DbError as e:
            mock = db_cfg.get('mock')
            logging.error('database ' + re.sub(r'\.?(, |[({]).+$|\. .+$', '', str(e)) + (
                ', mocked data in %s used' % mock if mock else ''))
            self.stop()
            if mock:
                from glob import glob
                mock_path = path.join(BASE_DIR, db_cfg['mock'])
                self.conn, self.db = self._connect_db(db_cfg, mock_path)
                self.site['mock'] = True
                if self.db.user.find_one({}) is None:  # first run
                    from montydb.types.bson import json_loads
                    for fn in glob(path.join(BASE_DIR, 'doc/examples/db', '*.json')):
                        coll = path.basename(fn).split('.')[0]
                        with open(fn, encoding='utf-8') as f:
                            rs = json_loads(f.read())
                        for i, r in enumerate(rs):
                            try:
                                self.db[coll].insert_one(r)
                            except DbError:
                                pass

    def stop(self):
        if self.conn:
            self.conn.close()
            self.conn = self.db = None

    @staticmethod
    def log_function(handler):
        summary = handler._request_summary()
        s = handler.get_status()
        if s != 404 and not(s < 400 and re.search(r'/static', summary)):
            Application.log(handler, summary, s, 0 if s < 400 else 'W' if 1 < 500 else 2)

    @staticmethod
    def log(handler, summary='', code=0, method=0):
        user = handler.current_user
        summary = re.sub(r'\(.+\)', '(' + handler.get_ip() + ')', summary)
        request_time = int(1000 * handler.request.request_time())
        cls = re.split("[.']", str(handler.__class__))[-2]
        log_method = [log.info, log.warning, log.error][method]
        log_method("%s%s %s %d ms%s", '%03d ' % code if code else '',
                   summary, cls, request_time,
                   user and ' [%s]' % user.get('username') or '')

    @staticmethod
    def _connect_db(d, mock_path=''):
        if mock_path:
            from montydb import set_storage, MontyClient
            set_storage(
                repository=mock_path,  # dir path for database to live on disk
                mongo_version='4.2',  # try matching behavior with this mongodb version
                cache_modified='2',  # seconds, the only setting that flat-file have
                use_bson=True,  # will import pymongo's bson
            )
            conn = MontyClient(mock_path)
            return conn, conn[d['name']]
        usr = f"{d['user']}:{d['password']}@" if d.get('user') else ''
        uri = f"mongodb://{usr}{d['host']}:{d['port']}" + (f"/{d['name']}" if usr else '')
        conn = pymongo.MongoClient(
            uri, connectTimeoutMS=2000, serverSelectionTimeoutMS=2000,
            maxPoolSize=8, waitQueueTimeoutMS=5000, connect=False)
        return conn, conn[d['name']]
