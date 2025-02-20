import re
from srv.util import md5
from srv.base import auto_try, BaseHandler
from bson import json_util

re_sign = re.compile(r'[~!@#$%_;,.]')
re_lower, re_upper, re_digit = re.compile(r'[a-z]'), re.compile(r'[A-Z]'), re.compile(r'\d')


class LoginApi(BaseHandler):
    """登录接口"""
    URL = '/api/user/login'
    ROLES = None

    @auto_try
    def post(self):
        d = self.data()
        assert d['username'] and d['password']
        u = self.db.user.find_one(dict(username=d['username']))
        if u is None:
            self.send_raise_failed(f"用户 {d['username']} 不存在")
        if u['password'] != md5(d['password']):
            self.send_raise_failed('密码不对，请重新输入')

        self.log(f"{d['username']} login")
        LoginApi.send_user(self, u)

    @staticmethod
    def send_user(self, user):
        ret = {'_id': str(user['_id'])}
        for k in ['username', 'nickname', 'updated', 'internal']:
            if k in user:
                ret[k] = user[k]
        self.current_user = ret
        self.set_secure_cookie('user_time', self.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.set_secure_cookie('user', json_util.dumps(self.current_user), expires_days=5)
        self.send_success(ret)


class RegisterApi(BaseHandler):
    """注册用户接口"""
    URL = '/api/user/register'
    ROLES = None

    @auto_try
    def post(self):
        u = self.data()
        assert u['username'] and u['password'] and u['nickname'] and u['verification']
        password = md5(u['password'])
        RegisterApi.check_password(self, u['password'])
        if self.db.user.find_one(dict(username=u['username'])):
            self.send_raise_failed(f"用户名 {u['username']} 已存在")

        u = dict(username=u['username'], password=password,
                 nickname=u['nickname'],
                 verification=u['verification'],
                 created=self.now(), updated=self.now())
        r = self.db.user.insert_one(u)
        u['_id'] = r.inserted_id

        self.log(f"{u['username']} registered")
        LoginApi.send_user(self, u)

    @staticmethod
    def check_password(self, password):
        n = 0
        for r in [re_lower, re_upper, re_digit, re_sign]:
            if r.search(password):
                n += 1
        if n < 3:
            self.send_raise_failed('密码要有大写字母、小写字母、数字、特殊符号中至少三种')


class LogoutApi(BaseHandler):
    """注销接口"""
    URL = '/api/user/logout'

    @auto_try
    def get(self):
        if self.current_user:
            self.clear_cookie('user')
            self.current_user = None
            self.log(f'{self.username} logout')
        if self.get_query_argument('redirect', ''):
            return self.redirect('/')
        self.send_success()


class ProfileApi(BaseHandler):
    """修改个人信息接口"""
    URL = '/api/user/profile'

    @auto_try
    def post(self):
        u, upd = self.data(), {}
        password = md5(u['password'])
        old = self.db.user.find_one(dict(username=self.username, password=password))
        if old is None:
            self.send_raise_failed('密码不对，请重新输入')

        for k in ['nickname', 'verification']:
            if u.get(k) and u[k] != old[k]:
                upd[k] = u[k]
        if not upd:
            self.send_raise_failed('个人信息没有改变')
        upd['updated'] = self.now()

        self.db.user.update_one(dict(username=self.username), {'$set': upd})
        self.log(f"{self.username} profile changed: {','.join(list(upd.keys()))}")
        LoginApi.send_user(self, self.db.user.find_one(dict(username=self.username)))


class PasswordApi(BaseHandler):
    """修改密码接口"""
    URL = '/api/user/password'

    @auto_try
    def post(self):
        u = self.data()
        if self.db.user.find_one(dict(username=self.username, password=md5(u['password_old']))) is None:
            self.send_raise_failed('原密码不对')
        RegisterApi.check_password(self, u['password'])

        upd = dict(updated=self.now(), password=md5(u['password']))
        self.db.user.update_one(dict(username=self.username), {'$set': upd})
        self.log(f"{self.username} password changed")
        LoginApi.send_user(self, self.db.user.find_one(dict(username=self.username)))


class ForgotApi(BaseHandler):
    """重置密码接口"""
    URL = '/api/user/forgot'
    ROLES = None

    @auto_try
    def post(self):
        u = self.data()
        RegisterApi.check_password(self, u['password'])

        old = self.db.user.find_one(dict(username=u['username']))
        if old is None:
            self.send_raise_failed('用户名不存在')
        if u['verification'] != old['verification']:
            self.send_raise_failed('备忘不匹配')

        upd = dict(updated=self.now(), password=md5(u['password']))
        self.db.user.update_one(dict(username=u['username']), {'$set': upd})
        self.log(f"{u['username']} password reset")
        self.send_success()
