from srv.base import auto_try, BaseHandler, re, to_basestring
from bson.objectid import ObjectId
from srv.proj.model import Proj, Article, Section


class ProjHandler(BaseHandler):
    """项目修改页面"""
    URL = '/proj/edit/@oid'
    ROLES = None

    def check_proj(self, oid):
        p = self.db.proj.find_one({'_id': ObjectId(oid)})
        if p is None:
            self.send_raise_failed('项目不存在', 404)
        p['short_name'] = self.util.trim_bracket(p['name'])
        p['_cloned'] = p.get('cloned') or (self.db.proj.find_one(
            {'cloned': p['_id']}, projection={'name': 1}) and p['_id'])

        editable = self.username == p['created_by'] or self.username in p['editors']
        view = not editable and not p.get('public')
        if view and not editable and not p.get('published'):
            self.send_raise_failed(f"项目 {p['code']} 还未发布，不能查看", 404)
        return p

    @auto_try
    def get(self, oid):
        p = self.check_proj(oid)
        p.update(Proj.unpack_data(p, ['created', 'updated']))
        self.render('proj_edit.html', proj=p, Article=Article, _id=str(p['_id']),
                    is_owner=p['created_by'] == self.username)


class MatchHandler(ProjHandler):
    """项目段落对照页面"""
    URL = '/proj/(match|view)/@oid'
    ROLES = None

    @auto_try
    def get(self, mode, p_id):
        p = self.check_proj(p_id)
        col_n, max_page, all_t = 0, 0, []
        pi = max(1, int(self.get_argument('page', '1'))) if p['cols'] == 1 else 0

        u = cur_toc = p.get('cur_toc') or {}
        if cur_toc and mode == 'match':
            self.db.proj.update_one({'_id': p['_id']}, {'$unset': {'cur_toc': 1}})
        for c in p['columns']:
            a = self.db.article.find_one({'_id': c['a_id']})
            max_page = len(a['sections']) if pi and len(a['sections']) > 3 else 0
            pi = min(pi, max_page) if max_page else 0
            c.update(dict(rows=Article.get_column_rows(self, a, pi),
                          toc=a.get('toc', [])))
            col_n += int(c.get('colspan') or 1)
            if a.get('toc'):
                all_t += [dict(a_id=str(a['_id']), toc_i=ti, name=t['name'], code=c['code'],
                               cur=int(ti == c.get('toc_i')),
                               new=1 if u and u['a_id'] == str(a['_id']) and u['toc_i'] == ti else 0)
                          for ti, t in enumerate(a['toc']) if t['rows']]

        self.render(f"proj_{'view' if mode == 'view' else 'match'}.html",
                    TAGS=Section.TAGS, proj=p, _id=str(p['_id']), pi=pi, max_page=max_page,
                    col_w=100 * 1000 // max(1, col_n) / 1000, all_toc=all_t, cur_toc=cur_toc,
                    is_owner=p['created_by'] == self.username,
                    editable=self.username == p['created_by'] or self.username in p['editors'])

    def finish(self, html=None):
        if html and b'width: 1%' in html:
            html = re.sub(br'(.cell[^{]*{ width: )\d+%; }/\*([0-9.]+)\*/',
                          lambda m: b'%s%s%%; }' % (m.group(1), m.group(2)), html)
        return BaseHandler.finish(self, html)


class MatchRenderApi(MatchHandler):
    """项目段落对照页面的局部渲染"""
    URL = '/api/proj/(match)/@oid'

    def finish(self, html=None):
        if b'<table>' not in (html or b''):
            return BaseHandler.finish(self, html)
        html = re.search(b'<table>((.|\n)+)</table>', html).group(1)
        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.write(to_basestring(html).strip())


class ArticleHandler(BaseHandler):
    """经典页面"""
    URL = '/article/@oid'

    @auto_try
    def get(self, oid):
        a = self.db.article.find_one({'_id': ObjectId(oid)})
        if a is None:
            self.send_raise_failed('经典不存在', 404)

        proj = self.db.proj.find_one({'_id': ObjectId(a['proj_id'])})
        cell = proj and [c for c in proj['columns'] if c['a_id'] == a['_id']]
        a['short_name'] = cell[0]['name'] if cell else None
        a['colspan'] = cell[0].get('colspan', 1) if cell else None
        a['proj_name'] = proj['name'] if proj else ''

        sections = list(self.db.section.find({'_id': {'$in': [s['_id'] for s in a['sections']]}}))
        for i, sec in enumerate(a['sections']):
            sec = [s for s in sections if s['_id'] == sec['_id']][0]
            a['sections'][i] = sec

        a.update(Article.unpack_data(a, ['created', 'updated']))
        self.render('article.html', page=a, _id=a['_id'], Article=Article,
                    has_cb=[s['source'] for s in a['sections'] if 'import_cb' in s['source']])
