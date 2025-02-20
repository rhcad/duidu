from srv.base import auto_try, BaseHandler, json_util, re
from bson.objectid import ObjectId
from srv.proj.model import Proj, Article, Section

re_long_word = re.compile('[A-Za-z0-9]{12,}')


class ProjBaseApi(BaseHandler):
    def get_project(self, proj_id, need_owner=False):
        proj = self.db.proj.find_one({'_id': ObjectId(proj_id)}) if proj_id else None
        if proj is None:
            self.send_raise_failed('项目不存在', 404)
        if need_owner and self.username != proj['created_by']:
            self.send_raise_failed('只有本项目的创建者才能修改')
        return proj

    def editable(self, proj, verify=False):
        can = self.username == proj['created_by'] or self.username in proj['editors']
        if not can and verify:
            self.send_raise_failed('只有本项目的创建者或协编才能修改内容')
        return can

    @staticmethod
    def get_merged_row(proj, row_i):
        proj['rows'] = proj.get('rows') or []
        for r in proj['rows']:
            if r['row_i'] == row_i:
                return r

    @staticmethod
    def get_merged_p_in_cell(cell, row):
        row['line'] = int(row['line'])
        for i, r in enumerate(cell or []):
            if r and r['line'] == row['line'] and r['s_id'] == row['s_id']:
                return i, r
        return -1, None

    def get_article(self, _id):
        a = self.db.article.find_one({'_id': ObjectId(_id)})
        if a is None:
            self.send_raise_failed('经典不存在', 404)
        return a

    def get_section(self, _id):
        s = self.db.section.find_one({'_id': ObjectId(_id)})
        if s is None:
            self.send_raise_failed('经典内容不存在', 404)
        return s

    def get_sections(self, ids):
        return {str(r['_id']): r for r in self.db.section.find({'_id': {'$in': [
            ObjectId(s) for s in list(set(ids))]}})}

    def get_one_row(self, d, allow_no_raw=False):
        proj = self.get_project(d.pop('proj_id'))
        self.editable(proj, verify=True)
        if allow_no_raw and not d.get('s_id'):
            return proj, None, None, None
        sec = self.get_section(d['s_id'])
        rows = Section.get_rows(sec)  # {line,text}
        row = Section.get_row(rows, int(d['line']))
        assert row, '行内容不存在，请刷新页面'
        return proj, sec, rows, row

    def create_article(self):
        a = self.data()
        is_append = a.pop('append', 0)
        assert a['code'] and a['name'] and (is_append or a['type'])
        short_name = self.util.trim_bracket(a.pop('short_name', '') or a['name'])
        assert is_append or short_name, '请输入简称'
        code = re.sub(r'_\d{3}$|:', '', a['code'])
        colspan = int(a.pop('colspan', 0) or 0)

        proj = self.get_project(a['proj_id'])
        self.editable(proj, verify=True)
        exist_a = self.db.article.find_one(dict(code=code, proj_id=proj['_id']))
        proj['columns'] = proj.get('columns', [])
        exist_col = [c for c in proj['columns'] if c['code'] == code]
        if not is_append or is_append == 'auto':
            if exist_col and (not exist_a.get('sections') or is_append == 'auto'):
                exist_a.update(dict(name=a['name'], source=a.get('source'), content=a['content']))
                return proj, exist_a, is_append
            if exist_col:
                self.send_raise_failed(f"原文 {code} 已在项目 {proj['code']} 中存在", 404)
            if len(proj['columns']) > 11:
                self.send_raise_failed('最多12栏对读')

        assert not is_append or is_append == 'auto' or (exist_col and exist_a)
        if is_append and exist_a:
            exist_a.update(dict(name=a['name'], source=a.get('source'), content=a['content']))
            return proj, exist_a, is_append

        if self.db.article.find_one(dict(code=code, proj_id=proj['_id'])):
            self.send_raise_failed(f"经典编码重复 {code}+{self.username}")
        a.update(dict(proj_id=proj['_id'], created_by=self.username,
                      created=self.now(), updated=self.now()))
        a2 = dict(char_n=0, **a)
        a2.pop('content')
        a2.pop('source')
        r = self.db.article.insert_one(a2)
        a['_id'] = r.inserted_id

        proj['columns'].append(dict(a_id=a['_id'], code=code, name=short_name,
                                    **({'colspan': colspan} if colspan > 1 else {})))
        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
            updated=self.now(), columns=proj['columns'], cols=len(proj['columns']))})

        self.log(f"article {code} {a['name']} of project {proj['code']} created")
        return proj, a, is_append

    @staticmethod
    def update_ids(obj, id_map):
        s = json_util.dumps(obj)
        s = re.sub(r'"([a-f0-9]{24})"', lambda m: '"%s"' % id_map.get(m.group(1), m.group(1)), s)
        return json_util.loads(s)

    @staticmethod
    def fix_text(content):
        content = re.sub(r'(\s*\n)+', '\n', content)
        content = re.sub(r'<[^<>]*>|\[[A-Z]?\d+[a-z]?]|[@|]', '', content)  # 去除xml标签、保留字符
        return content.strip()


class ProjAddApi(BaseHandler):
    """增加项目"""
    URL = '/api/proj/add'

    @auto_try
    def post(self):
        p = self.data()
        assert p['code'] and p['name']

        if self.db.proj.find_one(dict(code=p['code'], created_by=self.username)):
            self.send_raise_failed(f"项目编码重复 {p['code']}+{self.username}")
        p = dict(code=p['code'], name=p['name'], comment=p['comment'], columns=[],
                 created_by=self.username, editors=[], cols=0, char_n=0, toc_n=0, rows=[],
                 created=self.now(), updated=self.now())
        r = self.db.proj.insert_one(p)
        _id = str(r.inserted_id)

        self.log(f"project {p['code']} {p['name']} created")
        self.send_success(dict(redirect=f"/proj/edit/{_id}"))


class ProjCloneApi(ProjBaseApi):
    """克隆项目"""
    URL = '/api/proj/clone'

    @auto_try
    def post(self):
        d, tmp = self.data(), self.username

        if self.db.proj.find_one(dict(code=d['code'], created_by=self.username)):
            self.send_raise_failed(f"项目编码重复 {d['code']}+{self.username}")
        p0 = self.get_project(d.pop('proj_id'))
        articles = list(self.db.article.find({'proj_id': p0['_id']}))
        sections = list(self.db.section.find({'proj_id': p0['_id']}))
        self.db.section.delete_many(dict(tmp=tmp))
        self.db.article.delete_many(dict(tmp=tmp))
        self.db.proj.delete_many(dict(tmp=tmp))

        p = dict(code=d['code'], name=d['name'], comment=d['comment'], tmp=tmp,
                 created_by=self.username, editors=[], cols=p0['cols'], char_n=p0['char_n'],
                 columns=[], rows=[], created=self.now(), updated=self.now(), toc_n=p0['toc_n'],
                 cloned=p0.get('cloned', p0['_id']))
        r = self.db.proj.insert_one(p)
        p_id = r.inserted_id
        id_map = {str(p0['_id']): str(p_id)}  # old_id: new_id

        for a in articles:
            old_id = a.pop('_id')
            a.update(dict(created_by=self.username, proj_id=p_id, cloned=a.get('cloned', old_id),
                          created=self.now(), updated=self.now(), tmp=tmp))
            r = self.db.article.insert_one(a)
            a['_id'] = r.inserted_id
            id_map[str(old_id)] = str(r.inserted_id)
        for s in sections:
            old_id = s.pop('_id')
            s.update(dict(created_by=self.username, a_id=ObjectId(id_map[str(s['a_id'])]),
                          tmp=tmp, cloned=s.get('cloned', old_id), proj_id=p_id,
                          created=self.now(), updated=self.now()))
            r = self.db.section.insert_one(s)
            s['_id'] = r.inserted_id
            id_map[str(old_id)] = str(r.inserted_id)

        for a in articles:
            self.db.article.update_one({'_id': a['_id']}, {'$set': self.update_ids(
                dict(sections=a['sections']), id_map)})
        self.db.proj.update_one({'_id': p_id}, {'$unset': {'tmp': 1}, '$set': self.update_ids(
            dict(columns=p0['columns'], rows=p0['rows']), id_map)})
        self.db.section.update_many(dict(proj_id=p_id), {'$unset': {'tmp': 1}})
        self.db.article.update_many(dict(proj_id=p_id), {'$unset': {'tmp': 1}})

        self.log(f"project {p['code']} {p['name']} created from {p0['_id']}")
        self.send_success(dict(redirect=f"/proj/edit/{p_id}"))


class ProjEditApi(ProjBaseApi):
    """修改项目信息"""
    URL = '/api/proj/info'

    @auto_try
    def post(self):
        d = self.data()
        upd = Proj.pack_data(d, ['code', 'name', 'comment', 'public'])
        proj = self.get_project(d.pop('proj_id'), True)
        if upd.get('code') and upd['code'] != proj['code']:
            if self.db.proj.find_one({'code': upd['code'], 'created_by': proj['created_by']}):
                self.send_raise_failed(f"项目编码重复 {upd['code']}")
        r = self.db.proj.update_one({'_id': proj['_id']}, {'$set': upd})
        if r.modified_count:
            self.log(f"proj {proj['code']} changed")
        return self.send_success({'modified': r.modified_count})


class SetEditorApi(ProjBaseApi):
    """设置项目协编"""
    URL = '/api/proj/editor'

    @auto_try
    def post(self):
        d = self.data()
        assert re.match(r'^([\s\n-]?[A-Za-z0-9]+)+$', d['editor'].strip()), '用户名格式不对'
        proj = self.get_project(d['proj_id'], True)
        editors, add = proj['editors'][:], []

        for s in re.split(r'[\s\n]+', d['editor']):
            if s.startswith('-'):
                if s[1:] in editors:
                    editors.remove(s[1:])
            elif s and s not in editors and s not in add and s != self.username:
                add.append(s)
        added = [u['username'] for u in self.util.get_users(self.db, add)]
        if set(added) != set(add):
            self.send_raise_failed(f"用户名 {', '.join(list(set(add) - set(added)))} 不存在")
        editors.extend(added)
        if editors == proj['editors']:
            self.send_raise_failed('协编没有改变')

        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(editors=editors)})
        self.log('editors changed: ' + ','.join(editors))
        return self.send_success(editors)


class ReorderColApi(ProjBaseApi):
    """调整栏序"""
    URL = '/api/proj/reorder'

    @auto_try
    def post(self):
        d = self.data()
        proj = self.get_project(d['proj_id'], True)
        rows = re.findall(r'[A-Za-z][A-Za-z0-9]+', d['rows'])
        old_rows = [c['code'] for c in proj['columns']]

        if rows == old_rows:
            self.send_raise_failed('栏序没有改变，可移动行顺序再试')
        if set(rows) != set(old_rows):
            self.send_raise_failed('不能增减栏')

        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
            columns=[[c for c in proj['columns'] if c['code'] == s][0] for s in rows])})
        return self.send_success()


class ArticleEditApi(ProjBaseApi):
    """修改经典信息"""
    URL = '/api/article/info'

    @auto_try
    def post(self):
        d = self.data()
        colspan = d.pop('colspan', 0)
        upd = Article.pack_data(d, ['name', 'type'])
        a = self.get_article(d.pop('_id'))
        r = self.db.article.update_one({'_id': a['_id']}, {'$set': upd})
        changed = r.modified_count

        p = self.db.proj.find_one({'_id': ObjectId(a['proj_id'])})
        col, col_changed = p and [c for c in p['columns'] if c['a_id'] == a['_id']], 0
        if col and d.get('short_name') and d['short_name'] != col[0]['name']:
            col[0]['name'] = d['short_name']
            col_changed += 1
        if col and colspan and int(colspan) != col[0].get('colspan'):
            col[0]['colspan'] = int(colspan)
            col_changed += 1
        if col_changed:
            r = self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(columns=p['columns'])})
            changed += r.modified_count

        if changed:
            self.log(f"article {a['code']} changed")
        return self.send_success({'modified': changed})


class ProjDelApi(ProjBaseApi):
    """删除项目"""
    URL = '/api/proj/del/@oid'

    @auto_try
    def post(self, _id):
        proj = self.get_project(_id, True)
        self.db.section.delete_many({'proj_id': proj['_id']})
        self.db.article.delete_many({'proj_id': proj['_id']})
        self.db.proj.delete_one({'_id': proj['_id']})
        self.log(f"project {_id} removed: {proj['name']}")
        self.send_success({'redirect': '/'})


class SectionDelApi(ProjBaseApi):
    """删除经典内容区"""
    URL = '/api/section/del/@oid'

    @auto_try
    def post(self, sec_id):
        s = self.get_section(sec_id)
        a = self.get_article(s['a_id'])
        p = self.get_project(a.get('proj_id')) or {}

        if s['created_by'] != self.username and p.get('created_by') != self.username:
            self.send_raise_failed(f"需要由创建者 {s['created_by']} 删除")
        r = self.db.article.update_one({'_id': a['_id']}, {'$set': {
            'char_n': a['char_n'] - s['char_n'],
            'sections': [r for r in a['sections'] if r['_id'] != s['_id']]}})
        assert r.modified_count
        self.db.section.delete_one({'_id': s['_id']})
        self.log(f"section {s['_id']} removed: {s['name']}")

        rows = self.update_ids(dict(char_n=p['char_n'] - s['char_n'],
                                    rows=p.get('rows', [])), {str(s['_id']): ''})
        self.db.proj.update_one({'_id': p['_id']}, {'$set': rows})
        self.send_success({'a_id': str(a['_id'])})


class ArticleDelApi(ProjBaseApi):
    """删除经典"""
    URL = '/api/article/del/@oid'

    @auto_try
    def post(self, a_id):
        a = self.get_article(a_id)
        p = self.db.proj.find_one({'_id': ObjectId(a['proj_id'])}) or {}
        if a['created_by'] != self.username and p.get('created_by') != self.username:
            self.send_raise_failed(f"需要由创建者 {a['created_by']} 删除")

        sections = list(self.db.section.find({'a_id': a['_id']}, projection=dict(name=1)))
        id_map = {str(a['_id']): ''}
        for sec in sections:
            id_map[str(sec['_id'])] = ''

        if p.get('columns'):
            rows = self.update_ids(p.get('rows', []), id_map)
            columns = [c for c in p['columns'] if c['a_id'] != a['_id']]
            self.db.proj.update_one({'_id': p['_id']}, {'$set': {
                'char_n': p['char_n'] - a['char_n'],
                'columns': columns, 'cols': len(columns), 'rows': rows}})

        self.db.article.delete_one({'_id': a['_id']})
        self.db.section.delete_many({'a_id': a['_id']})
        self.log(f"article {a['_id']} removed: {a['name']}")

        self.send_success({'redirect': f"/proj/edit/{a['proj_id']}" if p else '/'})


class ImportTextApi(ProjBaseApi):
    """导入经典内容，为纯文本内容或子类导入的格式内容"""
    URL = '/api/proj/import/text'

    @auto_try
    def post(self):
        proj, a, is_append = self.create_article()
        large, n = None, 0
        if isinstance(a['content'], list):
            for s in a['content']:
                if self.db.section.find_one(dict(a_id=a['_id'], source=a['source'] + s['code'])):
                    continue
                if s['code'] not in s['title']:
                    s['title'] = f"{s['code']} {s['title']}"
                large = self.save_section(proj, a, s['title'], s['text'], s['code'], s.pop('rows'))
                if large:
                    break
                n += 1
        else:
            m = re_long_word.search(a['content'])
            if m:
                self.send_raise_failed('内容有太长的词: ' + m.group())
            large = self.save_section(proj, a, a['name'], a['content'])
        large = large and f'已导入{n}部分，项目总字数{large[0]}，如再导入{large[1]}字的内容就超过20万，多余内容可分拆项目'
        if n:
            self.log(large or f'已导入{n}部分', 'W')
            self.send_success({'ignore': large, 'n': n})
        else:
            self.send_raise_failed(large)

    def save_section(self, p, a, name, text, code='', rows=None):
        if not text:
            return
        if p['char_n'] + len(text) > 2e5:
            return p['char_n'], len(text)
        text = self.fix_text(text)
        content_md5, char_n = self.util.md5(text), len(re.sub(r'[^\u4e00-\u9fa5]+', '', text))
        if self.db.section.find_one(dict(a_id=a['_id'], content_md5=content_md5), projection={}):
            self.send_raise_failed('不能重复导入相同内容')

        rows = rows or [dict(line=(i + 1) * 100, text=r) for i, r in enumerate(
            re.split(r'[\u3000\s]*\n+[\u3000\s]*', text))]
        sec = dict(a_id=a['_id'], proj_id=a['proj_id'], name=name, char_n=char_n,
                   source=(a.get('source') or 'import_text') + code,
                   org_rows=rows, _content_md5=content_md5,
                   created_by=self.username, created=self.now(), updated=self.now())
        r = self.db.section.insert_one(sec)
        a['sections'] = a.get('sections', []) + [dict(_id=r.inserted_id, name=name)]
        a['char_n'] = a.get('char_n', 0) + char_n
        p['char_n'] = p.get('char_n', 0) + char_n
        self.db.article.update_one({'_id': a['_id']}, {'$set': dict(
            sections=a['sections'], char_n=a['char_n'])})
        self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(char_n=p['char_n'])})
