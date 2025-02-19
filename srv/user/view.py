from srv.base import auto_try, BaseHandler


class LoginHandler(BaseHandler):
    """登录页面"""
    URL = '/user/login'
    ROLES = None

    @auto_try
    def get(self):
        self.render('user_login.html', next=self.get_query_argument('next', '/'))


class RegisterHandler(BaseHandler):
    """注册页面"""
    URL = '/user/register'
    ROLES = None

    @auto_try
    def get(self):
        self.render('user_register.html', next=self.get_query_argument('next', '/'))


class ProfileHandler(BaseHandler):
    """个人信息页面"""
    URL = '/user/profile'

    @auto_try
    def get(self):
        user = self.db.user.find_one(dict(username=self.username))
        if user is None:
            self.clear_cookie('user')
            return self.redirect(self.get_login_url())
        self.render('user_profile.html', user=user)


class PasswordHandler(BaseHandler):
    """密码修改页面"""
    URL = '/user/password'

    @auto_try
    def get(self):
        self.render('user_password.html')


class ForgotHandler(BaseHandler):
    """重置密码页面"""
    URL = '/user/forgot'
    ROLES = None

    @auto_try
    def get(self):
        self.render('user_forgot.html')
