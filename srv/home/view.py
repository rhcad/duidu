from bson.objectid import ObjectId
from srv.base import auto_try, BaseHandler
from srv.proj.model import Proj


class HomeHandler(BaseHandler):
    """首页"""
    URL = '/'
    ROLES = None

    @auto_try
    def get(self):
        cond = [{'published': {'$ne': None}}, {'public': True},
                {'created_by': {'$ne': None} if self.username == 'admin' else self.username or '-'},
                {'editors': {'$elemMatch': {'$eq': self.username or '-'}}}]
        p = dict(code=1, name=1, comment=1, published=1, updated=1, cols=1,
                 created_by=1, editors=1, public=1, char_n=1, toc_n=1)
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
        dict(id='view', caption='预览', url='/proj/view/@_id')
    ]

    @auto_try
    def get(self, p_id):
        p_id = ObjectId(p_id)
        p = dict(code=1, name=1, comment=1, published=1, created=1, updated=1, cols=1,
                 created_by=1, public=1)
        rows = list(self.db.proj.find({'$or': [{'_id': p_id}, {'cloned': p_id}], 'tmp': None},
                                      projection=p, sort=[('created', 1)]))
        rows = [r for r in rows if r['cols'] or self.username in (r['editors'] + [r['created_by']])]
        self.render('home_cloned.html', model=self, rows=Proj.format_rows(rows))
