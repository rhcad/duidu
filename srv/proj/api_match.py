from bson import json_util
from srv.proj.api import ProjBaseApi, auto_try, re, re_long_word
from srv.proj.model import Section, Toc


class SplitApi(ProjBaseApi):
    """拆分段落"""
    URL = '/api/proj/match/split'

    @auto_try
    def post(self):
        d = self.data()  # {old_text,text,line,a_i,a_id,s_i,s_id}
        if d['old_text'] == d['text']:
            self.send_raise_failed('没有改变')
        re_cr, rc_sp = re.compile(r'@|\s*\n+\s*'), re.compile(r'[\s\u3000]')
        if rc_sp.sub('', d['old_text']) != rc_sp.sub('', re_cr.sub('', d['text'])):
            self.send_raise_failed('除了插入@或回车换行外，不能改动文本')

        proj, sec, rows, row = self.get_one_row(d)
        if d['old_text'] != row['text']:
            self.send_raise_failed('行内容不匹配，请刷新页面')
        self.verify_no_note(self, proj, d)
        assert not re_cr.search(row['text'])
        from_r = self.get_merged_row(proj, row.get('row_i'))
        from_cell = from_r and from_r[str(d['a_i'])]
        from_i, _ = self.get_merged_p_in_cell(from_cell, d)

        row_i, attr = rows.index(row), dict(row)
        texts, new_rs, new_line = re_cr.split(d['text']), [], 1
        for i, text in enumerate(texts):
            text = text.strip('| \u3000')
            if i == 0:
                row['text'] = text
                new_rs.append(row)
                new_line = row['line'] // 100 * 100 + 1
                for k in ['_id', 'line', 'text', 'toc_ids']:
                    attr.pop(k, 0)
                if from_cell:
                    from_cell[from_i]['text'] = text[:10]
            else:
                while Section.get_row(rows, new_line):
                    new_line += 1
                if new_line % 100 == 0:
                    self.send_raise_failed('一段拆分太多')
                if from_cell:
                    from_i += 1
                    from_cell.insert(from_i, dict(line=new_line, s_id=d['s_id'], text=text[:10]))
                new_rs.append(dict(line=new_line, text=text, **attr))
                new_line += 1

        self.log(f"match split {sec['_id']} {row_i}: {len(new_rs)} rows")
        rows[row_i:row_i + 1] = new_rs
        self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
            updated=self.now(), rows=rows)})
        if from_cell:
            self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
                rows=proj['rows'], updated=self.now())})
        self.send_success()

    @staticmethod
    def verify_no_note(self, p, d):
        line = int(d['line'])
        for nr in p.get('notes', []):
            for key in ['left', 'right']:
                for r in nr[key]:
                    if r['s_id'] == d['s_id'] and r['line'] == line:
                        self.send_raise_failed('此段已关联注解')


class MergeUpApi(ProjBaseApi):
    """合并段落到上一段"""
    URL = '/api/proj/match/merge'

    @auto_try
    def post(self):
        d = self.data()
        proj, sec, rows, now_r = self.get_one_row(d['info'])
        prev_r = Section.get_row(rows, d['prev']['line'])
        ri = rows.index(prev_r)
        assert now_r and prev_r and ri + 1 == rows.index(now_r), '参数错误'
        if now_r.get('toc_ids'):
            self.send_raise_failed('需要解除科判条目才可合并此段')
        SplitApi.verify_no_note(self, proj, d['info'])

        from_r = self.get_merged_row(proj, now_r.get('row_i'))
        from_cell = from_r and from_r[str(d['info']['a_i'])]
        from_i, _ = self.get_merged_p_in_cell(from_cell, d['info'])

        if prev_r['line'] % 100 == 0 and prev_r['line'] // 100 != now_r['line'] // 100 \
                and '|' not in prev_r['text']:
            prev_r['text'] += '|'
        elif prev_r['line'] % 100 and now_r['line'] % 100 == 0:
            prev_r['text'] += '|'
            prev_r['line'] = now_r['line']
        prev_r['text'] += now_r['text']
        del rows[ri + 1]

        self.log(f"match merge {sec['_id']} {ri}")
        if from_i >= 0:
            del from_cell[from_i]
            self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
                rows=proj['rows'], updated=self.now())})
        self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
            updated=self.now(), rows=rows)})
        self.send_success()


class MergeRowApi(ProjBaseApi):
    """合并选中的各栏段落为单独的一组"""
    URL = '/api/proj/match/merge-row'

    @auto_try
    def post(self):
        d, proj = self.get_project_edit()
        from_ri = d.pop('from_row', 0)  # extract row
        from_r = from_ri and self.get_merged_row(proj, from_ri)

        sections = self.get_sections(s['s_id'] for s in d['rows'])
        end_row = proj['rows'][-1] if proj['rows'] else {}
        end_status = dict(others=0, cur_col='')
        new_row, n_rows = dict(row_i=1 + max([r['row_i'] for r in proj['rows']] + [0])), []
        rest_row = from_r and dict(row_i=2 + max([r['row_i'] for r in proj['rows']] + [0]))

        for key, c in d['columns'].items():
            if not c:  # 此栏没有新加的段落
                if end_row.get(key):  # 末行中此栏有段落
                    end_status['others'] += 1
            else:
                new_row[key] = [dict(line=r['line'], s_id=r['s_id'], text=r['text'][:10]) for r in c]
                from_cell, remove_i = from_r and from_r[key], 0
                if not from_ri:
                    end_status['cur_col'] = 'up-has-text' if end_row.get(key) else 'up-null'
                for r in c:
                    sec = sections[r['s_id']]
                    row = Section.get_row(Section.get_rows(sec), r['line'])
                    assert from_ri == (row.get('row_i') or 0), '内部行号错误'
                    row['row_i'] = new_row['row_i']
                    if from_cell:
                        i, _ = self.get_merged_p_in_cell(from_cell, r)
                        if i >= 0:  # 在已合并格中，就先清空其行号
                            from_cell[i].update({'line': 0})
                            remove_i = remove_i or i + 1
                    else:
                        n_rows.append(row)
                    sec['_changed'] = True
                if from_cell and from_cell[-1]['line']:
                    rest_cell = rest_row[key] = []
                    for i in range(remove_i, len(from_cell)):
                        r = from_cell[i]
                        if r['line']:
                            sec = sections[r['s_id']]
                            row = Section.get_row(Section.get_rows(sec), r['line'])
                            row['row_i'] = rest_row['row_i']
                            rest_cell.append(dict(line=r['line'], s_id=r['s_id'], text=r['text'][:10]))
                if remove_i:
                    from_cell[remove_i - 1:] = []

        # 如果只加了一栏的段落、已合并的末行中此栏空缺、末行有其他栏的段落，就合并到此栏最后一个空单元格中
        if end_status['cur_col'] == 'up-null' and len(new_row.keys()) == 2 and end_status['others']:
            new_row.pop('row_i')  # 准备合并到更上面的单元格
            key = list(new_row.keys())[0]
            for i in range(len(proj['rows']) - 1, -1, -1):  # 从下往上找空单元格
                end_row, up_row = proj['rows'][i], i > 0 and proj['rows'][i - 1]
                if up_row and up_row.get(key):  # 此栏上一行有段落
                    break
            end_row[key] = new_row[key]  # 填充段落到此空单元格
            for row in n_rows:
                new_row['row_i'] = row['row_i'] = end_row['row_i']
        else:
            if from_ri:
                i = proj['rows'].index(from_r)
                proj['rows'].insert(i + 1, new_row)
                if len(rest_row.keys()) > 1:
                    proj['rows'].insert(i + 2, rest_row)
            else:
                proj['rows'].append(new_row)

        if from_r and len([k for k, v in from_r.items() if v]) == 1:
            proj['rows'].remove(from_r)

        self.log(f"match merge row: {json_util.dumps(new_row)}")
        for sec in sections.values():
            if sec.get('_changed'):
                self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
                    rows=sec['rows'], updated=self.now())})
        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
            rows=proj['rows'], updated=self.now())})
        self.send_success()


class MoveApi(ProjBaseApi):
    """移到段落到相邻组"""
    URL = '/api/proj/match/move'

    @auto_try
    def post(self):
        d = self.data()
        sel = d['sel'] if d['up'] else list(reversed(d['sel']))
        proj = self.get_project(sel[0]['proj_id'])
        self.verify_editable(proj)

        sections, is_extract = {}, d['to_row'] == 'new'
        from_r = self.get_merged_row(proj, d['from_row'])
        if d['to_row'] == 'new':
            d['to_row'] = 1 + max([r['row_i'] for r in proj['rows']] + [0])
            to_r = {'row_i': d['to_row'], str(d['col_i']): []}
            proj['rows'].insert(proj['rows'].index(from_r) + 1, to_r)
        else:
            to_r = self.get_merged_row(proj, d['to_row']) if d['to_row'] else None

        for r in sel:
            sec = sections[r['s_id']] = sections.get(r['s_id']) or self.get_section(r['s_id'])
            row = Section.get_row(sec['rows'], r['line'])
            assert row and row['row_i'] == d['from_row']

            from_cell = from_r[str(r['a_i'])]
            _, to_move = self.get_merged_p_in_cell(from_cell, r)
            if to_move:
                from_cell.remove(to_move)
            row['row_i'] = d['to_row']
            if to_r is not None and to_move:
                to_cell = to_r[str(r['a_i'])] = to_r.get(str(r['a_i']), [])
                to_cell.insert(-1 if d['up'] else 0, to_move)

        if len([k for k, v in from_r.items() if v]) == 1:
            proj['rows'].remove(from_r)

        for sec in sections.values():
            self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
                rows=sec['rows'], updated=self.now())})
        self.db.proj.update_one({'_id': proj['_id']}, {'$set': dict(
            rows=proj['rows'], updated=self.now())})
        self.send_success()


class MarkDelApi(ProjBaseApi):
    """标记段落删除状态"""
    URL = '/api/proj/match/mark-del'

    @auto_try
    def post(self):
        sel = self.data()
        proj = self.get_project(sel[0]['proj_id'])
        self.verify_editable(proj)

        sections = {}
        for r in sel:
            sec = sections[r['s_id']] = sections.get(r['s_id']) or self.get_section(r['s_id'])
            row = Section.get_row(Section.get_rows(sec), r['line'])
            row['del'] = not row.get('del')

        for sec in sections.values():
            self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
                rows=sec['rows'], updated=self.now())})
        self.send_success()


class TagApi(ProjBaseApi):
    """设置段落类型"""
    URL = '/api/proj/match/tag'

    @auto_try
    def post(self):
        d = self.data()
        tag = d['info'].pop('tag')
        proj, sec, rows, row = self.get_one_row(d['info'])
        sel = d['sel'] if '*' in Section.TAGS[tag] else [d['info']]
        for r in sel:
            row = Section.get_row(rows, int(r['line']))
            if not row or r['s_i'] != d['info']['s_i']:
                continue
            tags = row['tag'] = row.get('tag', [])
            if tag.endswith('xu'):
                if tag[0] == '_':
                    if tag in tags:
                        tags.remove(tag)
                elif tag not in tags:
                    tags.append(tag)
            else:
                for k in Section.TAGS.keys():
                    if not tag.endswith('xu') and k in tags:
                        tags.remove(k)
                if tag[0] != '_':
                    tags.append(tag)

        self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(updated=self.now(), rows=rows)})
        self.send_success()


class FixRowsApi(ProjBaseApi):
    """数据修复"""
    URL = '/api/proj/match/fix/@oid'

    @auto_try
    def post(self, p_id):
        proj = self.get_project(p_id)
        self.verify_editable(proj)


class TocBaseApi(ProjBaseApi):
    def get_article(self, _id):
        a = ProjBaseApi.get_article(self, _id)
        a['toc_n'] = len([1 for t in a.get('toc', []) if t['rows']])
        return a

    def update_article(self, a, p, p_upd=None):
        now_n, old_n = len([1 for t in a.get('toc', []) if t['rows']]), a['toc_n']
        if old_n != now_n:
            p_upd = {'toc_n': p['toc_n'] + now_n - old_n, **(p_upd or {})}
        if p_upd:
            self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(updated=self.now(), **p_upd)})
        self.db.article.update_one({'_id': a['_id']}, {'$set': dict(updated=self.now(), toc=a['toc'])})


class TocAddApi(TocBaseApi):
    """在段落前插入科判条目"""
    URL = '/api/proj/match/toc/insert'

    @auto_try
    def post(self):
        d = self.data()
        a = self.get_article(d['a_id'])
        p, sec, rows, row = self.get_one_row(d)
        self.add_rows(d, p, a, sec, rows, row)

    def add_rows(self, d, p, a, s, rows, r, name='', add_toc=False):
        # 如果当前栏没有科判，就创建科判
        col = p['columns'][int(d['a_i'])]
        p_upd, old_toc_i, ret_n = {}, col.get('toc_i'), 0
        add_toc = add_toc or not a.get('toc')
        if add_toc:
            a['toc'] = a.get('toc', []) + [dict(name=name or col['name'], rows=[])]
        toc_i = col['toc_i'] = len(a['toc']) - 1 if add_toc else col['toc_i'] if col.get(
            'toc_i', -1) in range(len(a['toc'])) else 0
        toc = a['toc'][toc_i]['rows']  # 当前科判的各行
        if old_toc_i != toc_i:
            p_upd.update(dict(columns=p['columns'], cur_toc=dict(a_id=str(a['_id']), toc_i=toc_i)))
        new_id = 1 + max([max([t['id'] for t in tc['rows']] or [0]) for tc in a['toc']])

        # 选了科判、没有文本，就关联到给定的段落
        if not d.get('text') and d.get('toc') and s and r:
            if d['toc']['a_id'] != d['a_id']:
                self.send_raise_failed('要关联的段落与科判必须属于同一个经典')
            for i, toc in enumerate(a['toc']):
                for t in toc['rows']:
                    if not ret_n and t['id'] == d['toc']['toc_id']:
                        toc_i, ret_n, new_id = i, 1, t['id'] + 1
                        if t.get('s_id'):
                            self.send_raise_failed('所选科判条目已插入到某个段落')
                        t.update(dict(s_id=s['_id'], line=r['line']))
                        r['toc_ids'] = r.get('toc_ids', []) + [t['id']]
                        break
            assert ret_n, '科判条目不存在'
        # 对每行科判条目设置级别和编号
        texts = re.split(r'\s*\n+\s*', d.pop('text', '').replace('»', '\n+'))
        for i, text in enumerate(texts):
            text = re.sub(r'\s*[+-]\s+(\d+\s)', lambda m_: m_.group(1), text)
            m = re.search(r'^([0-9]+\s+|[+-]+\s*)?(.+)$', text)
            if not m:
                break
            level, text = (m.group(1) or '').strip(), m.group(2).strip()
            if not level and Toc.re_toc.match(text):
                level = Toc.TOC_CH.index(text[0]) + 1
            if not toc:
                level = 1
            elif not level:
                level = toc[-1]['level']
            elif str(level)[0] in '+-':
                level = max(1, toc[-1]['level'] + (1 if level[0] == '+' else -1))
            else:
                level = max(1, min(int(level), toc[-1]['level'] + 1))
            m = re_long_word.search(text)
            if m:
                self.send_raise_failed('有太长的词: ' + m.group())

            toc.append(dict(level=level, text=text, id=new_id, **(dict(
                s_id=s['_id'], line=r['line']) if s and r and i == len(texts) - 1 else {})))
            if r and i == len(texts) - 1:
                r['toc_ids'] = r.get('toc_ids', []) + [new_id]
            new_id += 1
            ret_n += 1

        # 提交数据并返回请求
        assert ret_n, '没有改变'
        if s:
            self.db.section.update_one({'_id': s['_id']},
                                       {'$set': dict(updated=self.now(), rows=rows)})
        self.update_article(a, p, p_upd)
        self.send_success(dict(a_id=str(a['_id']), toc_i=toc_i, toc_id=new_id - 1,
                               name=a['toc'][toc_i]['name'], add_toc=1 if add_toc else 0))


class TocImportApi(TocAddApi):
    """导入科判"""
    URL = r'/api/proj/match/toc/import'

    @auto_try
    def post(self):
        d, p = self.get_project_edit()
        a = self.get_article(d['a_id'])
        assert d.get('name'), '需要科判名称'
        assert not [1 for t in a.get('toc', []) if t['name'] == d['name']], '科判名称重复'
        content = re.split(r'\s*\n+\s*', d['text'].strip())
        assert content, '需要至少一个科判条目'
        d['text'] = '\n'.join(content)
        self.add_rows(d, p, a, {}, [], {}, name=d['name'], add_toc=True)


class TocDelApi(TocBaseApi):
    """删除科判条目"""
    URL = '/api/proj/match/toc/del'

    @auto_try
    def post(self):
        d, n = self.data(), 0
        p, sec, rows, row = self.get_one_row(d, True)
        a = self.get_article(d['a_id'])
        toc, t_r = Toc.get_toc(a, d['toc_i'], int(d.get('toc_id') or 0))

        if d.get('del_root'):
            a['toc'].remove(toc)
            dis_link = {}
            for r in toc['rows']:
                k = str(r.get('s_id') or '')
                if k:
                    dis_link[k] = dis_link.get(k, set()) | {r['line']}
            for k, lines in dis_link.items():
                sec = self.get_section(k)
                for r in sec['rows']:
                    if r.get('toc_ids'):
                        r['toc_ids'] = list(set(r['toc_ids']) & lines)
                        n += 1
                self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(
                    updated=self.now(), rows=sec['rows'])})
            sec = None
            self.log(f"toc_del n={n} name={toc['name']}")
        else:
            assert t_r, '科判条目不存在'
            if row and t_r['id'] in row.get('toc_ids', []):
                row['toc_ids'].remove(t_r['id'])
                n += 1
            if d.get('dis_link'):
                t_r.pop('s_id')
                t_r.pop('line')
            else:
                i, t_rows = toc['rows'].index(t_r), toc['rows']
                t_rows.remove(t_r)
                d['next_id'] = t_rows[i if i < len(t_rows) else i - 1]['id'] if t_rows else 0
                self.log(f"toc_del id={d['toc_id']} next_id={d['next_id']}")

        if sec:
            self.db.section.update_one({'_id': sec['_id']}, {'$set': dict(updated=self.now(), rows=rows)})
        self.update_article(a, p)
        self.send_success(d)


class TocEditApi(TocBaseApi):
    """修改科判条目"""
    URL = '/api/proj/match/toc/edit'

    @auto_try
    def post(self):
        d, p = self.get_project_edit()
        a = self.get_article(d['a_id'])
        toc, t_r = Toc.get_toc(a, d['toc_i'], int(d.get('toc_id') or 0))

        d['text'] = d['text'].strip().replace('\n', '')
        if d.get('edit_root'):
            if not d['text'] or d['text'] == toc['name']:
                self.send_raise_failed('没有改变')
            toc['name'] = d['text']
        else:
            assert t_r, '科判条目不存在'
            m = re.search(r'^([0-9]+)\s+(.+)$', d['text'])
            level, text = (int(m.group(1)), m.group(2).strip()) if m else (0, '')
            level = max(1, min(int(level), t_r['level'] + 1)) if level else t_r['level']
            if not text or re.match(r'^\d+[^\d\s]', d['text']):
                self.send_raise_failed('格式为“级别 文本”')

            if level == t_r['level'] and text == t_r['text']:
                self.send_raise_failed('没有改变')
            t_r.update(dict(level=level, text=text))
            d.update(t_r)

        self.update_article(a, p)
        self.send_success(d)


class TocGetApi(ProjBaseApi):
    """获取科判内容"""
    URL = r'/api/proj/toc/@oid/(\d+)'
    ROLES = None

    @auto_try
    def get(self, a_id, toc_i):
        a = self.get_article(a_id)
        toc = a.get('toc', [])[int(toc_i)]
        toc = Toc.format_rows([toc])[0]
        self.send_success(dict(a_id=a_id, toc_i=toc_i, code=a['code'], **toc))
