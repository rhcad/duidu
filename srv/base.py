import re
import sys
import traceback
from os import path
from bson import json_util
from datetime import datetime
from tornado.web import Finish
from tornado.escape import to_basestring
from pymongo.errors import PyMongoError
from srv.cors import CorsMixin, RequestHandler
from srv import util

BASE_DIR = path.dirname(path.abspath(path.dirname(__file__)))


def on_exception(self, e):
    if not isinstance(e, Finish):
        _, _, tb = sys.exc_info()
        tb_info = traceback.extract_tb(tb)
        fn, line, f, text = tb_info[-1]
        if isinstance(e, AssertionError):
            msg = str(e) if e.args else f"内部错误 {path.basename(fn).split('.')[0]} L{line}"
        elif isinstance(e, PyMongoError):
            msg = '数据库错误 ' + re.sub(r'\.?(, |[({]).+$|\. .+$', '', str(e))
        else:
            msg = e.__class__.__name__ + ' ' + str(e)
        self.log('{0} {1}, in {2}: {3}'.format(path.basename(fn), line, f, msg), 'E')
        BaseHandler.send_error(self, 500, reason=msg,
                               print_exc=not (isinstance(e, AssertionError) and e.args))


def auto_try(func):
    """Decorator for get or post function"""

    def wrapper(self, *args, **kwargs):
        try:
            if self.request.method == 'GET' and self.URL.endswith('/@oid'):
                short = self.get_argument('use_short', 0) or self.get_argument('add_short', 0)
                if self.get_argument('use_short', 0):
                    self._short = short
                elif self.get_argument('add_short', 0):
                    assert self.current_user.get('internal') and re.match('^[a-z0-9]+$', short)
                    r = self.db.short.find_one({'id': short})
                    assert r is None or r['url'] == self.request.path, 'used by ' + r['url']
                    self.db.short.update_one({'id': short}, {'$set': dict(
                        url=self.request.path, created=self.now())}, upsert=True)
                    self._short = short
            return func(self, *args, **kwargs)
        except Exception as e:
            on_exception(self, e)

    return wrapper


class BaseHandler(CorsMixin):
    CORS_HEADERS = 'Content-Type,Host,X-Forwarded-For,X-Requested-With,' \
                   'User-Agent,Cache-Control,Cookies,Set-Cookie'
    ROLES = ['user']

    def __init__(self, app, req, **p):
        self.db, self.config, self.app = app.db, app.config, app
        self.is_api = '/api/' in req.path
        self.util = util
        self.username, self._short, self._data = '', '', None
        RequestHandler.__init__(self, app, req, **p)

    def set_default_headers(self):
        CorsMixin.set_default_headers(self)
        self.set_header('Access-Control-Allow-Origin',
                        not self.app.settings.get('debug') and self.app.site.get('domain') or '*')

    def prepare(self):
        need_login = not self.current_user and self.ROLES
        if self.current_user:
            self.username = self.current_user['username']
            try:
                time = datetime.strptime(to_basestring(self.get_secure_cookie('user_time')), '%Y-%m-%d %H:%M:%S')
                seconds = (self.now() - time).seconds
            except (TypeError, ValueError, AttributeError):
                seconds = 1e5
            if self.ROLES and seconds > (30 if self.request.method[0] in 'PD' else 300):
                u = self.db.user.find_one(dict(username=self.username))
                if u and u['updated'] == self.current_user['updated']:
                    self.set_secure_cookie('user_time', self.now().strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    self.clear_cookie('user')
                    self.current_user = None
                    self.log(f'{self.username} need login')
                    need_login = 're'
        else:
            sec = '.'.join(self.get_ip().split('.')[:2])
            if sec != '127.0' and self.db.blocklist.find_one({'section': sec}):
                return self.send_error(403, reason='Forbidden')

        if need_login:
            if self.is_api:
                self.send_error(403, reason='请重新登录' if need_login == 're' else '请登录')
            else:
                url = re.search(r'\?next=[^?]+$', '?next=' + self.request.uri).group()
                self.redirect(self.get_login_url() + url)

    def get_current_user(self):
        if 'Access-Control-Allow-Origin' not in self._headers:
            return self.send_error(403, reason='Forbidden')

        user = self.get_secure_cookie('user')
        try:
            return user and json_util.loads(user) or None
        except TypeError:
            pass

    def get_ip(self):
        ip = self.request.headers.get('x-forwarded-for') or self.request.remote_ip
        return ip and re.sub(r'^::\d$', '', ip[:15]) or '127.0.0.1'

    def log(self, text, method='I'):  # I|W|E
        self.app.log(self, text + ' (ip)', 0, 'IWE'.index(method))

    def data(self):
        if self._data is None:
            if 'data' not in self.request.body_arguments:
                body = b'{"data":' in self.request.body and json_util.loads(
                    to_basestring(self.request.body)).get('data')
            else:
                body = json_util.loads(to_basestring(self.get_body_argument('data')))
            if not isinstance(body, (dict, list)):
                body = dict(self.request.arguments)
                for k, s in body.items():
                    body[k] = to_basestring(s[0])
            self._data = body if isinstance(body, (dict, list)) else {}
        return self._data

    def kwargs_render(self, **kwargs):
        kwargs['debug'] = self.app.settings['debug']
        kwargs['site'] = dict(self.app.site)
        kwargs['user'] = kwargs.get('user') or dict(self.current_user or {})
        kwargs['dumps'] = json_util.dumps
        kwargs['current_path'] = self.request.path
        kwargs['internal'] = (self.current_user or {}).get('internal')
        kwargs['handler'] = self
        return kwargs

    def render(self, template_name, **kwargs):
        kwargs, req = self.kwargs_render(**kwargs), self.request
        if self._finished:
            return
        try:
            if req.method == 'GET' and self.URL.endswith('/@oid'):
                r = not self._short and self.db.short.find_one({'url': req.path})
                self._short = r['id'] if r else self._short
            kwargs['short_url'] = f'/s/{self._short}' if self._short else ''
            super(BaseHandler, self).render(template_name, **kwargs)
        except Exception as error:
            kwargs['message'] = '页面出错(%s): %s' % (template_name, str(error) or error.__class__.__name__)
            self.send_error(**kwargs)

    def send_success(self, data=None):
        assert data is None or isinstance(data, (list, dict))
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        self.write(json_util.dumps(dict(status='success', data=data)))
        raise Finish()

    def send_raise_failed(self, message, code=0):
        self.log(message + (f' [{self.username}]' if self.username else ''), 'W')
        if self.is_api:
            self.write(dict(status='failed', message=str(message)))
        else:
            kwargs = dict(code=code, message=message, site=self.app.site)
            super(BaseHandler, self).render('_error.html', **kwargs)
        raise Finish()

    def write_error(self, code=500, **kwargs):
        self.send_error(code, **kwargs)

    def send_error(self, code=500, **kwargs):
        if code >= 500 and kwargs.get('print_exc', True):
            traceback.print_exc()
        msg = kwargs.get('message') or kwargs.get('reason') or self._reason
        exc = kwargs.get('exc_info')
        exc = exc and len(exc) == 3 and exc[1]
        msg = msg if msg != 'OK' else '无权访问' if code == 403 else \
            '后台服务出错 (%s, %s)' % (
                str(self).split('.')[-1].split(' ')[0],
                '%s(%s)' % (exc.__class__.__name__, re.sub(r"^'|'$", '', str(exc)))
            )

        if not self._finished:
            if self.is_api:
                self.write(dict(status='failed', code=code, message=msg))
            else:
                kwargs.update(dict(code=code, message=msg, site=self.app.site))
                super(BaseHandler, self).render('_error.html', **kwargs)
            if not self._finished:
                self.finish()
            if not exc:
                raise Finish()

    @staticmethod
    def now():
        return datetime.now()
