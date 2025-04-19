from os import path, makedirs, remove
from srv.base import auto_try, BaseHandler, json_util, re, BASE_DIR
from bson.objectid import ObjectId
from srv.proj.model import Proj, Article, Section
from zipfile import ZipFile, ZIP_BZIP2
import shutil


re_long_word = re.compile('[A-Za-z0-9]{12,}')


class ProjBaseApi(BaseHandler):
    def get_project(self, proj_id, need_owner=False):
        proj = self.db.proj.find_one({'_id': ObjectId(proj_id)}) if proj_id else None
        if proj is None:
            self.send_raise_failed('项目不存在', 404)
        if need_owner and self.username != proj['created_by']:
            self.send_raise_failed('创建者才能修改，或克隆后修改')
        return proj

    def get_project_edit(self):
        d = self.data()
        p = self.get_project(d['proj_id'])
        self.verify_editable(p)
        return d, p

    def verify_editable(self, proj):
        if self.username != proj['created_by']:
            self.send_raise_failed('本项目的创建者才能修改内容，或克隆后修改')

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

    def get_section(self, _id, def_sec=None):
        s = self.db.section.find_one({'_id': ObjectId(_id)})
        if s is None and def_sec is None:
            self.send_raise_failed('经典内容不存在', 404)
        return s or def_sec

    def get_sections(self, ids):
        return {str(r['_id']): r for r in self.db.section.find({'_id': {'$in': [
            ObjectId(s) for s in list(set(ids))]}})}

    def get_one_row(self, d, allow_no_raw=False):
        proj = d.get('proj') or self.get_project(d.pop('proj_id'))
        d.get('proj') or self.verify_editable(proj)
        if allow_no_raw and not d.get('s_id'):
            return proj, None, None, None
        sec = d.get('sections', {}).get(d['s_id'])
        if sec:
            rows = sec['rows']
        else:
            sec = self.get_section(d['s_id'], d.get('def_sec'))
            rows = Section.get_rows(sec)  # {line,text}
        row = Section.get_row(rows, int(d['line']))
        assert row or 'sections' in d, '行内容不存在，请刷新页面'
        return proj, sec, rows, row

    def create_article(self):
        a = self.data()
        is_append = a.pop('append', 0)
        note_base, note_tag = a.pop('base', ''), a.pop('tag', '')
        if a.get('code2'):
            a['code'] = a.pop('code2')

        if ' 第' in a['name']:
            a['name'] = re.sub(' 第.*$', '', a['name'])
        short_name = self.util.trim_bracket(a.pop('short_name', '') or a['name'])
        assert note_base or is_append or short_name, '请输入简称'
        code = re.sub(r'_\d{3}$|:', '', a.get('code', ''))
        assert code, '请输入编码'
        colspan = int(a.pop('colspan', 0) or 0)

        proj = self.get_project(a['proj_id'])
        self.verify_editable(proj)
        exist_a = self.db.article.find_one(dict(code=code, proj_id=proj['_id']))
        proj['columns'] = proj.get('columns', [])
        exist_col = [c for c in proj['columns'] if c['code'] == code or c['code'] == note_base]

        if not is_append or is_append == 'auto':
            if note_base:
                assert len(exist_col) <= 1, '已存在相同编码的经典'
                assert len(exist_col) == 1 and len(note_tag) == 1
                exist_col = exist_col[0]
                exist_col['notes'] = exist_col.get('notes', [])
                exist_t = [t for t in exist_col['notes'] if t['tag'] == note_tag]
                if exist_t:
                    if exist_a and exist_a['code'] == exist_t[0]['code']:
                        exist_a.update(dict(name=a['name'], source=a.get('source'), content=a['content']))
                        return proj, exist_a, is_append
                    self.send_raise_failed('注解标签重复，已有 ' + '、'.join(
                        [t['tag'] for t in exist_col['notes']]))
            else:
                if exist_col and (not exist_a.get('sections') or is_append == 'auto'):
                    exist_a.update(dict(name=a['name'], source=a.get('source'), content=a['content']))
                    return proj, exist_a, is_append
                if exist_col:
                    self.send_raise_failed(f"原文 {code} 已在项目 {proj['code']} 中存在", 404)
                if len(proj['columns']) > 11:
                    self.send_raise_failed('最多12栏对读')

        assert not is_append or is_append == 'auto' or exist_a
        if is_append and exist_a:
            exist_a.update(dict(name=a['name'], source=a.get('source'), content=a['content']))
            return proj, exist_a, is_append

        if self.db.article.find_one(dict(code=code, proj_id=proj['_id'])):
            self.send_raise_failed(f"经典编码重复 {code}+{self.username}")
        a.update(dict(proj_id=proj['_id'], created_by=self.username,
                      created_at=self.now(), updated_at=self.now()))
        if note_base:
            a.update(dict(note_for=exist_col['a_id'], note_tag=note_tag))
        a2 = dict(char_n=0, **a)
        a2.pop('content')
        a2.pop('source', 0)
        r = self.db.article.insert_one(a2)
        a['_id'] = r.inserted_id

        if note_base:
            exist_col['notes'].append(dict(a_id=a['_id'], code=code, name=short_name, tag=note_tag))
            proj['note_n'] = proj.get('note_n', 0) + 1
        else:
            proj['columns'].append(dict(a_id=a['_id'], code=code, name=short_name,
                                        **({'colspan': colspan} if colspan > 1 else {})))
        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
            updated_at=self.now(), columns=proj['columns'], cols=len(proj['columns']),
            note_n=proj.get('note_n', 0))})

        self.log(f"article {code} {a['name']} of project {proj['code']} created_at")
        return proj, a, is_append

    @staticmethod
    def update_ids(obj, id_map):
        s = json_util.dumps(obj)
        s = re.sub('"([a-f0-9]{24})"', lambda m: '"%s"' % id_map.get(m.group(1), m.group(1)), s)
        return json_util.loads(s)

    @staticmethod
    def fix_text(content):
        content = re.sub(r'(\s*\n)+', '\n', content)
        content = re.sub(r'<[^<>]*>|\[[A-Z]?\d+[a-z]?]|[@|]', '', content)  # 去除xml标签、保留字符
        content = re.sub(r'\\([“”’])', lambda m: m.group(1), content)
        return content.strip()


class ProjAddApi(BaseHandler):
    """增加项目"""
    URL = '/api/proj/add'

    @auto_try
    def post(self):
        p = self.add_proj(self, self.data())
        self.send_success(dict(redirect=f"/proj/edit/{str(p['_id'])}"))

    @staticmethod
    def add_proj(self, d):
        assert d['code'] and d['name']
        if self.db.proj.find_one(dict(code=d['code'], created_by=self.username)):
            self.send_raise_failed(f"项目编码重复 {d['code']}+{self.username}")
        p = dict(code=d['code'], name=d['name'], comment=d['comment'], columns=[],
                 created_by=self.username, cols=0, char_n=0, toc_n=0, note_n=0,
                 rows=[], created_at=self.now(), updated_at=self.now(), note_char_n=0)
        r = self.db.proj.insert_one(p)
        p['_id'] = r.inserted_id
        self.log(f"project {p['code']} {p['name']} created_at")
        return p


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
                 created_by=self.username, cols=p0['cols'], char_n=p0['char_n'],
                 columns=[], rows=[], created_at=self.now(), updated_at=self.now(), toc_n=p0['toc_n'],
                 cloned=p0.get('cloned', p0['_id']),
                 note_n=p0['note_n'], note_char_n=p0.get('note_char_n', 0))
        r = self.db.proj.insert_one(p)
        p_id = r.inserted_id
        id_map = {str(p0['_id']): str(p_id)}  # old_id: new_id

        for a in articles:
            old_id = a.pop('_id')
            a.update(dict(created_by=self.username, proj_id=p_id, cloned=a.get('cloned', old_id),
                          created_at=self.now(), updated_at=self.now(), tmp=tmp))
            r = self.db.article.insert_one(a)
            a['_id'] = r.inserted_id
            id_map[str(old_id)] = str(r.inserted_id)
        for s in sections:
            old_id = s.pop('_id')
            s.update(dict(created_by=self.username, a_id=ObjectId(id_map[str(s['a_id'])]),
                          tmp=tmp, cloned=s.get('cloned', old_id), proj_id=p_id,
                          created_at=self.now(), updated_at=self.now()))
            r = self.db.section.insert_one(s)
            s['_id'] = r.inserted_id
            id_map[str(old_id)] = str(r.inserted_id)

        for a in articles:
            self.db.article.update_one({'_id': a['_id']}, {'$set': self.update_ids(
                dict(sections=a.get('sections', []), note_for=a.get('note_for'),
                     updated_at=self.now()), id_map)})
        self.db.proj.update_one({'_id': p_id}, {'$unset': {'tmp': 1}, '$set': self.update_ids(
            dict(columns=p0['columns'], rows=p0['rows'], notes=p0.get('notes', []),
                 updated_at=self.now()), id_map)})
        self.db.section.update_many(dict(proj_id=p_id), {'$unset': {'tmp': 1}})
        self.db.article.update_many(dict(proj_id=p_id), {'$unset': {'tmp': 1}})

        self.log(f"project {p['code']} {p['name']} created_at from {p0['_id']}")
        self.send_success(dict(redirect=f"/proj/edit/{p_id}"))


class ProjImportApi(ProjBaseApi):
    """导入项目"""
    URL = '/api/proj/import/@oid'

    @auto_try
    def post(self, p_id):
        proj = p_id != 'auto' and self.get_project(p_id, True)

        file = self.request.files.get('file')
        z_fn = path.join(BASE_DIR, 'log', f'{self.username if p_id == "auto" else p_id}.zip')
        makedirs(path.dirname(z_fn), exist_ok=True)
        with open(z_fn, 'wb') as f:
            f.write(file[0]['body'])
        data, j_path, ret = {}, z_fn[:-4], []
        try:
            makedirs(j_path, exist_ok=True)
            with ZipFile(z_fn) as zf:
                zf.extractall(j_path)
            for coll in ['proj', 'article', 'section']:
                j_fn = path.join(j_path, coll + '.json')
                data[coll] = []
                if path.exists(j_fn):
                    with open(j_fn, encoding='utf-8') as f:
                        data[coll] = json_util.loads(f.read())
            if not proj:
                new_p = data['proj'][:1]
                proj = self.db.proj.find_one({'code': new_p[0]['code'], 'created_by': self.username})
                if proj is None:
                    proj = ProjAddApi.add_proj(self, new_p[0])
            else:
                new_p = [p for p in data['proj'] if p['created_by'] == proj[
                    'created_by'] and p['code'] == proj['code']]
            new_a = new_p and [a for a in data['article'] if a['proj_id'] == new_p[0]['_id']]
            new_s = new_a and [a for a in data['section'] if a['proj_id'] == new_p[0]['_id']]
            if not new_a:
                self.send_raise_failed('没有此项目的数据')
            data['proj'].remove(new_p[0])
            new_p = self.apply_data(proj, dict(proj=new_p[:1], article=new_a, section=new_s))
            ret.append(dict(_id=new_p['_id'], code=new_p['code'], name=new_p['name']))
            self.send_success(ret)
        finally:
            shutil.rmtree(j_path, ignore_errors=True)
            remove(z_fn)

    def apply_data(self, proj, data):
        new_p = data['proj'][0]
        p = self.db.proj.find_one({'_id': new_p['_id']}, projection=dict(name=1))
        if p and p['_id'] != proj['_id']:
            return self.send_raise_failed('项目不匹配')
        for k in ['_id', 'code', 'public', 'published', 'created_by']:
            if k in proj:
                new_p[k] = proj[k]
            else:
                new_p.pop(k, 0)

        for coll in ['article', 'section']:
            for r in data[coll]:
                a = self.db[coll].find_one({'_id': r['_id']}, projection=dict(proj_id=1))
                if a and a['proj_id'] != proj['_id']:
                    return self.send_raise_failed('项目的经典不匹配')
                r['proj_id'] = proj['_id']

        self.db.section.delete_many({'proj_id': proj['_id']})
        self.db.article.delete_many({'proj_id': proj['_id']})
        self.db.proj.delete_one({'_id': proj['_id']})
        for coll in ['proj', 'article', 'section']:
            for r in data[coll]:
                self.db[coll].update_one({'_id': r['_id']}, {'$set': r}, upsert=True)
        self.log(f"project {proj['code']} imported: {proj['name']}")
        return new_p


class ProjImportAutoApi(ProjImportApi):
    """导入项目"""
    URL = '/api/proj/import/(auto)'


class ProjExportApi(ProjBaseApi):
    """导出项目"""
    URL = '/api/proj/export/@oid'

    @auto_try
    def get(self, p_id):
        proj = self.get_project(p_id)
        data = dict(proj=[proj], article=self.db.article.find({'proj_id': proj['_id']}),
                    section=self.db.section.find({'proj_id': proj['_id']}))

        j_path = path.join(BASE_DIR, 'log', f'{p_id}e')
        z_fn = path.join(j_path, proj['code'] + '.zdb')
        try:
            makedirs(j_path, exist_ok=True)
            with ZipFile(z_fn, 'w', compression=ZIP_BZIP2) as zf:
                for k, rs in data.items():
                    with open(path.join(j_path, f'{k}.json'), 'w', encoding='utf-8') as f:
                        f.write(json_util.dumps(rs, ensure_ascii=False))
                    zf.write(path.join(j_path, f'{k}.json'), f'{k}.json')

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header('Content-Disposition', f'attachment; filename={path.basename(z_fn)}')
            with open(z_fn, 'rb') as f:
                self.write(f.read())
            self.finish()
        finally:
            shutil.rmtree(j_path, ignore_errors=True)
            if path.exists(z_fn):
                remove(z_fn)


class ProjEditApi(ProjBaseApi):
    """修改项目信息"""
    URL = '/api/proj/info'

    @auto_try
    def post(self):
        d = self.data()
        proj = self.get_project(d.pop('proj_id'), True)
        if d.get('published'):
            d['published'] = proj.get('published') or self.now()
        upd = Proj.pack_data(d, ['code', 'name', 'comment', 'public', 'published'])
        if upd.get('code') and upd['code'] != proj['code']:
            if self.db.proj.find_one({'code': upd['code'], 'created_by': proj['created_by']}):
                self.send_raise_failed(f"项目编码重复 {upd['code']}")
        r = self.db.proj.update_one({'_id': proj['_id']}, {'$set': upd})
        if r.modified_count:
            self.db.proj.update_one({'_id': proj['_id']}, {'$set': {'updated_at': self.now()}})
            self.log(f"proj {proj['code']} changed")
        return self.send_success({'modified': r.modified_count})


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
            updated_at=self.now(), columns=[[c for c in proj['columns'] if c['code'] == s][0] for s in rows])})
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
        changed, col_changed = r.modified_count, 0

        p = self.db.proj.find_one({'_id': ObjectId(a['proj_id'])})
        if a.get('note_for'):
            col = [c for c in p['columns'] if c['a_id'] == a['note_for']]
            col = col and [t for t in col[0]['notes'] if t['a_id'] == a['_id']]
            d['short_name'] = d.get('name')
        else:
            col = [c for c in p['columns'] if c['a_id'] == a['_id']]
        if col and d.get('short_name') and d['short_name'] != col[0]['name']:
            col[0]['name'] = d['short_name']
            col_changed += 1
        if col and colspan and int(colspan) != col[0].get('colspan'):
            col[0]['colspan'] = int(colspan)
            col_changed += 1
        if col_changed:
            r = self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(
                updated_at=self.now(), columns=p['columns'])})
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
        is_note = a.get('note_for')

        if s['created_by'] != self.username and p.get('created_by') != self.username:
            self.send_raise_failed(f"需要由创建者 {s['created_by']} 删除")
        r = self.db.article.update_one({'_id': a['_id']}, {'$set': {
            'char_n': a['char_n'] - s['char_n'], 'updated_at': self.now(),
            'sections': [r for r in a.get('sections', []) if r['_id'] != s['_id']]}})
        assert r.modified_count
        self.db.section.delete_one({'_id': s['_id']})
        self.log(f"section {s['_id']} removed: {s['name']}")

        rows = self.update_ids(dict(char_n=p['char_n'] - (0 if is_note else s['char_n']),
                                    note_char_n=p.get('note_char_n', 0) - (s['char_n'] if is_note else 0),
                                    rows=p.get('rows', []), updated_at=self.now()), {str(s['_id']): ''})
        self.db.proj.update_one({'_id': p['_id']}, {'$set': rows})
        self.send_success({'a_id': str(a['_id'])})


class ArticleDelApi(ProjBaseApi):
    """删除经典"""
    URL = '/api/article/del/@oid'

    @auto_try
    def post(self, a_id):
        a = self.get_article(a_id)
        is_note = a.get('note_for')
        p = self.db.proj.find_one({'_id': ObjectId(a['proj_id'])}) or {}
        if a['created_by'] != self.username and p.get('created_by') != self.username:
            self.send_raise_failed(f"需要由创建者 {a['created_by']} 删除")

        sections = list(self.db.section.find({'a_id': a['_id']}, projection=dict(name=1)))
        id_map = {str(a['_id']): ''}
        for sec in sections:
            id_map[str(sec['_id'])] = ''

        col_map, columns, rows = None, None, p.get('rows', [])
        if p.get('columns'):
            rows = self.update_ids(rows, id_map)
            columns = [c for c in p['columns'] if c['a_id'] != a['_id']]
            col_map = [i if c['a_id'] != a['_id'] else -1 for i, c in enumerate(p['columns'])]
            if -1 in col_map:
                col_map = col_map[:col_map.index(-1)] + [i - 1 for i in col_map[col_map.index(-1):]]
            col_map = {str(i): '' if idx < 0 else str(idx) for i, idx in enumerate(col_map)}
            for c in columns:
                if c.get('notes'):
                    c['notes'] = [t for t in c['notes'] if t['a_id'] != a['_id']]
            for i, r in enumerate(rows):
                new_r = {'row_i': r['row_i']}
                for k_old, k_new in col_map.items():
                    if k_new and r.get(k_old):
                        new_r[k_new] = r[k_old]
                rows[i] = new_r
            rows = [r for r in rows if len(list(r.keys())) > 1]

        if columns is not None:
            self.db.proj.update_one({'_id': p['_id']}, {'$set': {
                'char_n': p['char_n'] - (0 if is_note else a['char_n']),
                'note_char_n': p.get('note_char_n', 0) - (a['char_n'] if is_note else 0),
                'note_n': p['note_n'] - (1 if is_note else 0), 'updated_at': self.now(),
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
            n += 0 if large else 1
        large = large and f'已导入{n}部分，项目总字数{large[0]}，不能再导入{large[1]}字的内容，多余内容可分拆项目'
        if n:
            self.log(large or f'已导入{n}部分', 'W')
            self.send_success({'ignore': large, 'n': n})
        else:
            self.send_raise_failed(large or '未导入新的内容')

    def save_section(self, p, a, name, text, code='', rows=None):
        if not text:
            return
        if a.get('note_for'):
            if p.get('note_char_n', 0) + len(text) > 5e6 or len(text) > 1e5:
                return p.get('note_char_n', 0), len(text), 10
        else:
            if p['char_n'] + len(text) > 2e5:
                return p['char_n'], len(text), 20
        text = self.fix_text(text)
        content_md5, char_n = self.util.md5(text), len(re.sub(r'[^\u4e00-\u9fa5]+', '', text))
        if self.db.section.find_one(dict(a_id=a['_id'], content_md5=content_md5), projection={}):
            self.send_raise_failed('不能重复导入相同内容')

        rows = rows or [dict(line=(i + 1) * 100, text=r) for i, r in enumerate(
            re.split(r'[\u3000\s]*\n+[\u3000\s]*', text))]
        sec = dict(a_id=a['_id'], proj_id=a['proj_id'], name=name, char_n=char_n,
                   source=(a.get('source') or 'import_text') + code,
                   org_rows=rows, _content_md5=content_md5,
                   created_by=self.username, created_at=self.now(), updated_at=self.now())
        r = self.db.section.insert_one(sec)
        a['sections'] = a.get('sections', []) + [dict(_id=r.inserted_id, name=name)]
        a['char_n'] = a.get('char_n', 0) + char_n
        if a.get('note_for'):
            p['note_char_n'] = p.get('note_char_n', 0) + char_n
        else:
            p['char_n'] = p.get('char_n', 0) + char_n
        self.db.article.update_one({'_id': a['_id']}, {'$set': dict(
            sections=a.get('sections', []), char_n=a['char_n'], updated_at=self.now())})
        self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(
            note_char_n=p.get('note_char_n', 0), char_n=p['char_n'],
            note_n=p.get('note_n', 0), columns=p['columns'], updated_at=self.now()
        )})
