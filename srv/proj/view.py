from srv.base import auto_try, BaseHandler, re, to_basestring
from bson.objectid import ObjectId
from srv.proj.model import Proj, ProjNote, Article, Section, Toc
from srv.proj.api import ProjBaseApi


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
        return p, editable

    @auto_try
    def get(self, oid):
        p, editable = self.check_proj(oid)
        p.update(Proj.unpack_data(p, ['created', 'updated']))
        self.render('proj_edit.html', proj=p, Article=Article, ProjNote=ProjNote, _id=str(p['_id']),
                    is_owner=p['created_by'] == self.username, editable=editable)


class MatchHandler(ProjHandler, ProjBaseApi):
    """项目段落对照页面"""
    URL = '/proj/(match|view)/@oid'
    ROLES = None

    @auto_try
    def get(self, mode, p_id, **kw):
        if mode in ['notes', 'para']:
            a = self.db.article.find_one({'_id': ObjectId(p_id)})
            assert a, '经典不存在'
            p_id = a['proj_id']
            kw['note_a'] = a
        p, editable = self.check_proj(p_id)

        col_n, max_page, all_t = 0, 0, []
        pi_s = self.get_argument('page', '1').split('-')
        pi = max(1, int(pi_s[0])) if p['cols'] == 1 else 0

        u = cur_toc = p.get('cur_toc') or {}
        if cur_toc and mode == 'match':
            self.db.proj.update_one({'_id': p['_id']}, {'$unset': {'cur_toc': 1}})

        n_a = mode in ['notes', 'para'] and kw['note_a']
        if n_a:
            kw['note_a'] = Article.unpack_data(n_a, True)
            if n_a.get('note_for'):
                kw['notes'] = [s for s in p.get('notes', []) if s['left_aid'] == str(
                    n_a['note_for']) and (not s.get('note_aid') or s['note_aid'] == str(n_a['_id']))]
                col0 = [c for c in p['columns'] if c['a_id'] == n_a['note_for']][0]  # 被注解的栏
                cn = [t for t in col0.get('notes', []) if t['a_id'] == n_a['_id']]  # 对应注解标签
                p['columns'] = [col0, dict(a_id=n_a['_id'], code=n_a['code'],  # 右栏为释文
                                           name='[%s]%s' % (cn[0]['tag'], n_a['name']) if cn else n_a['name'])]
                if mode == 'para':
                    p.pop('rows', 0)
                    p['columns'] = p['columns'][1:]
            else:
                kw['notes'] = [s for s in p.get('notes', []) if s['left_aid'] == str(n_a['_id'])]
                cn = p['columns'] = [c for c in p['columns'] if c['a_id'] == n_a['_id']][:1]
                n_a['notes'] = cn[0].get('notes', [])
                kw['note_a'] = Article.unpack_data(n_a, True)
        else:
            kw['notes'] = self.fill_notes(p) if p.get('notes') else []

        for i, c in enumerate(p['columns']):
            a = self.db.article.find_one({'_id': c['a_id']})
            if i == 0:
                max_page = pi and self.get_max_page(p, a) or 0
                pi_ = pi = min(pi, max_page) if max_page else 0
            elif max_page:
                pi_ = min(int(pi_s[i]) if i < len(pi_s) else pi, self.get_max_page(p, a))
            c.update(dict(rows=Article.get_column_rows(self, a, pi_),
                          toc=a.get('toc', [])))
            col_n += int(c.get('colspan') or 1)
            if a.get('toc'):
                all_t += [dict(a_id=str(a['_id']), toc_i=ti, name=t['name'], code=c['code'],
                               cur=int(ti == c.get('toc_i')),
                               rows=Toc.format_rows([{'rows': t['rows']}])[0]['rows'] if mode == 'download' else None,
                               new=1 if u and u['a_id'] == str(a['_id']) and u['toc_i'] == ti else 0)
                          for ti, t in enumerate(a['toc']) if t['rows']]

        kw.update(mode=mode, proj=p, _id=str(p['_id']), pi=pi, max_page=max_page)
        self.render(f"proj_{mode if mode == 'match' else 'view'}.html", P_TAGS=Section.TAGS,
                    col_w=100 * 1000 // max(1, col_n) / 1000, all_toc=all_t, cur_toc=cur_toc,
                    is_owner=p['created_by'] == self.username, editable=editable, **kw)

    def get_max_page(self, p, a):
        return len(a['sections']) if self and len(a['sections']) > 3 else 0

    def finish(self, html=None):
        if html and b'width: 1%' in html:
            html = re.sub(br'(.cell[^{]*{ width: )\d+%; }/\*([0-9.]+)\*/',
                          lambda m: b'%s%s%%; }' % (m.group(1), m.group(2)), html)
        return BaseHandler.finish(self, html)

    def fill_notes(self, p):
        ca, sec_s, def_sec = {}, {}, {'rows': []}
        for t in p['notes']:
            note, rows, aid = t.get('note', {}), [], t.get('note_aid')
            a = ca[aid] = ca.get(aid) or aid and self.db.article.find_one({'_id': ObjectId(aid)}) or {}
            note.update(a and dict(code=a['code'], name=a['name'], tag=a['note_tag']))
            right = t.pop('right') if t.get('right') and aid else []
            for r in right:
                _, sec, rs, row = self.get_one_row(
                    dict(proj=p, sections=sec_s, def_sec=def_sec, s_id=r['s_id'], line=r['line']))
                sec_s[r['s_id']] = sec
                if row is None:
                    break
                if r.get('all'):
                    rows.append(row['text'])
                elif r.get('sel'):
                    r['sel'] = [row['text'][int(s['i0']): int(s['i1'])] for s in r['sel']]
                    rows.append('\u3000'.join(r['sel']))
            note['text'] = '\n'.join(rows) if rows else note.get('text', '')
            t['note'] = note
        return [t for t in p.pop('notes') if t.get('left') and (t.get('right') or t.get('note'))]


class MatchRenderApi(MatchHandler):
    """项目段落对照页面的局部渲染"""
    URL = '/api/proj/(match|para)/@oid'

    def finish(self, html=None):
        if b'<table>' not in (html or b''):
            return BaseHandler.finish(self, html)
        html = re.search(b'<table>((.|\n)+)</table>', html).group(1)
        self.set_header('Content-Type', 'text/html; charset=UTF-8')
        self.write(to_basestring(html).strip())


class MergeNotesHandler(MatchHandler):
    """合并注解页面"""
    URL = '/proj/(notes|para)/@oid'

    def render(self, template_name, **kwargs):
        BaseHandler.render(self, f"proj_{'notes' if kwargs['mode'] == 'notes' else 'match'}.html", **kwargs)


class DownloadHtmlApi(MatchHandler):
    """下载对读网页"""
    URL = '/api/proj/download/@oid'

    @auto_try
    def post(self, _id):
        return MatchHandler.get(self, 'download', _id)

    def get_max_page(self, p, a):
        if p['cols'] < 2 and p['toc_n'] < 1:
            self.send_raise_failed('多栏对读或有科判的才需要下载')
        if len(a['sections']) > 5:
            self.send_raise_failed('多页内容目前不能下载')
        if a.get('toc'):
            p['all_toc'] = p.get('all_toc', []) + [
                dict(a_id=str(a['_id']), toc_i=i, **Proj.unpack_data(t, True))
                for i, t in enumerate(a['toc'])]
        return 0


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
        a['short_name'] = cell[0]['name'] if cell else ''
        a['colspan'] = cell[0].get('colspan', 1) if cell else None
        a['proj_name'] = proj['name'] if proj else ''

        sections = list(self.db.section.find({'_id': {'$in': [s['_id'] for s in a['sections']]}}))
        for i, sec in enumerate(a['sections']):
            sec = [s for s in sections if s['_id'] == sec['_id']][0]
            a['sections'][i] = sec

        a.update(Article.unpack_data(a, ['created', 'updated']))
        self.render('article.html', page=a, _id=a['_id'], Article=Article,
                    has_cb=[s['source'] for s in a['sections'] if 'import_cb' in s['source']])
