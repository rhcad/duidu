import re
import sys
import logging
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
        filename, line, f, text = tb_info[-1]
        if isinstance(e, PyMongoError):
            msg = '数据库错误 ' + re.sub(r'[.:].+$', '', str(e))
        else:
            msg = e.__class__.__name__ + ' ' + str(e)
        logging.error('{0} {1}, in {2}: {3}'.format(path.basename(filename), line, f, msg))
        BaseHandler.send_error(self, 500, reason=msg)


def auto_try(func,):
    """Decorator for get or post function"""

    def wrapper(self, *args, **kwargs):
        try:
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
        self.username, self._data = '', None
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
            if seconds > (30 if self.request.method[0] in 'PD' else 300):
                u = self.db.user.find_one(dict(username=self.username))
                if u and u['updated'] == self.current_user['updated']:
                    self.set_secure_cookie('user_time', self.now().strftime('%Y-%m-%d %H:%M:%S'))
                else:
                    self.clear_cookie('user')
                    self.current_user = None
                    logging.info(f'{self.username} need login')
                    need_login = 're'
                
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
        kwargs = self.kwargs_render(**kwargs)
        if self._finished:
            return
        try:
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
        logging.warning(message + (f' [{self.username}]' if self.username else ''))
        if self.is_api:
            self.write(dict(status='failed', message=str(message)))
        else:
            kwargs = dict(code=code, message=message, site=self.app.site)
            super(BaseHandler, self).render('_error.html', **kwargs)
        raise Finish()

    def write_error(self, code=500, **kwargs):
        self.send_error(code, **kwargs)

    def send_error(self, code=500, **kwargs):
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
