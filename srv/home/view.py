from bson.objectid import ObjectId
from srv.base import auto_try, BaseHandler
from srv.proj.model import Proj
from srv.user.model import User


class HomeHandler(BaseHandler):
    """首页"""
    URL = r'/(:\d+)?'
    ROLES = None

    @auto_try
    def get(self, _=0):
        cond = [{'published': {'$ne': None}}, {'public': True},
                {'created_by': {'$ne': None} if self.username == 'admin' else self.username or '-'},
                {'editors': {'$elemMatch': {'$eq': self.username or '-'}}}]
        p = dict(code=1, name=1, comment=1, published=1, updated=1, cols=1,
                 created_by=1, editors=1, public=1, char_n=1, toc_n=1, note_n=1)
        rows = list(self.db.proj.find({'$or': cond, 'tmp': None}, projection=p,
                                      sort=[('code', 1), ('name', 1)]))
        rows = [r for r in rows if r['cols'] or self.username in (r['editors'] + [r['created_by']])]
        for r in rows:
            r['char_k'] = round(r['char_n'] / 1000)
        self.render('home.html', model=Proj, rows=Proj.format_rows(rows, time_format='%Y-%m-%d'))


class ClonedHandler(BaseHandler, Proj):
    """首页"""
    URL = '/cloned/@oid'
    ROLES = None
    hidden_fields = ['editors', 'public', 'published', 'columns', 'char_n', 'char_k']
    actions = [
        dict(id='view', caption='预览', url='/proj/view/@_id', default=True)
    ]

    @auto_try
    def get(self, p_id):
        p_id = ObjectId(p_id)
        p = dict(code=1, name=1, comment=1, published=1, created=1, updated=1, cols=1,
                 created_by=1, public=1, toc_n=1, note_n=1)
        rows = list(self.db.proj.find({'$or': [{'_id': p_id}, {'cloned': p_id}], 'tmp': None},
                                      projection=p, sort=[('created', 1)]))
        rows = [r for r in rows if r['cols'] or self.username in (r['editors'] + [r['created_by']])]
        self.render('home_cloned.html', model=self, rows=Proj.format_rows(rows))


class UsersHandler(BaseHandler):
    """用户管理"""
    URL = '/users'

    @auto_try
    def get(self):
        if self.username != 'admin' and len(self.username) > 2:
            return self.send_error(403, reason='Forbidden')
        rows = list(self.db.user.find({}, projection=dict(
            username=1, nickname=1, created=1, updated=1, ip=1)))
        blocked = [r['ip'] for r in self.db.blocklist.find(
            {}, projection=dict(ip=1, _id=0), sort=[('created', -1)])]

        self.render('users.html', blocked=blocked, model=User,
                    rows=User.format_rows(rows, time_format='%Y-%m-%d'))


class ShortHandler(BaseHandler):
    """短地址"""
    URL = '/s/([a-z0-9]+)'
    ROLES = None

    @auto_try
    def get(self, num):
        r = self.db.short.find_one({'id': num})
        if r is None:
            self.send_raise_failed('地址不存在', 404)
        self.redirect(r['url'] + f'?use_short={num}&v={int(self.now().timestamp())}')
