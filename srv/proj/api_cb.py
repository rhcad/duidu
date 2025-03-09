from tornado import gen
from tornado.escape import to_basestring
from tornado.httpclient import AsyncHTTPClient, HTTPError
from srv.base import on_exception
from srv.proj.api import ImportTextApi, re
from bs4 import BeautifulSoup as Soup


class ImportCBApi(ImportTextApi):
    """从CBeta导入或追加经典内容"""
    URL = '/api/proj/import/cb'

    @gen.coroutine
    def post(self):
        try:
            a = self.data()
            a.update(dict(content=[], name='', source='import_cb '), append='auto')
            for vol in self.util.parse_vol(a.pop('vol', '') or '1'):
                html, title, code = yield self.fetch_cb(re.sub(':[a-z]$', '', a['code']), vol)
                r, err = self.parse_html(html, title, code)
                if not err:
                    if not title or not r['rows']:
                        break
                    a['content'].append(r)
                    a.update(dict(code=a['code'].replace(':', ''),
                                  name=a['name'] or self.util.trim_bracket(r['title'])))
                elif len(a['content']) < 2:
                    self.send_raise_failed(f'{code} 导入失败: {err}')
            ImportTextApi.post(self)
            self.finish()
        except Exception as e:
            on_exception(self, e)

    def parse_html(self, html, title, code):
        def flush_xu():
            if len(xu_rows) > 1:
                xu_rows[0]['tag'].append('xu_first')
                xu_rows[-1]['tag'].append('xu_end')
            xu_rows.clear()

        self.log(f'parse_html {code} {title}')
        html = re.sub('<(a|title)( [^>]+)?>[^<]+</(a|title)>', '', html, re.I)  # 去掉脚注
        html = re.sub(r"<div id='[a-z]+-copyright'>(.|\n)+</div>", '', html, re.M)
        soup = Soup(html, 'html.parser')
        text, error, rows, tags = '', '', [], {}
        mu, xu, xu_n, xu_rows = '', '', 0, []

        for p in soup.select('#body,p,.lg-cell,.div-xu,mulu'):
            s = self.fix_text(p.get_text())
            cls = p.get_attribute_list('class')

            if p.name == 'mulu':
                mu = mu or (cls[0] if cls else '')
            elif 'div-xu' in cls:
                xu, mu = xu or 'xu', ''  # 允许连续的 .div-xu 元素
            elif s:
                r = self._parse_html_p(text, rows, xu, xu_rows, tags, cls, s, p)
                if not r:
                    continue
                r, text, xu = r
                if mu:
                    r['tag'] = r.get('tag', []) + [mu]
                    mu = ''
                if xu:
                    if xu == 'xu':
                        xu_n += 1
                        flush_xu()
                    xu = p.find_parent('div', class_='div-xu') is not None
                    if xu:
                        r['tag'] = r.get('tag', []) + ['xu', f'xu{xu_n}']
                        xu_rows.append(r)
                if not xu and xu_rows:
                    flush_xu()
                rows.append(r)
        flush_xu()
        if text.startswith('{"'):
            m = re.search(r'"message":"(.+)"}}', text)
            text, error = '', m.group(1) if m else 'error'
        return dict(rows=rows, text=text.strip(), title=title, code=code), error

    @staticmethod
    def _parse_html_p(text, rows, xu, xu_rows, tags, cls, s, p):
        r = dict(text=s, line=(len(rows) + 1) * 100)
        if p.get('id') == 'body':
            text = r['text'] = s = p.contents[0].string.strip()
            if re.match(r'^[A-Za-z0-9 \[\](),.-]+$', s):
                rows.append(dict(tag=['num'], **r))
            return
        text += s + '\n'
        if 'lg-cell' in cls:
            r['tag'] = ['verse']
        elif 'juan' in cls and len(s) > 2 and s in tags.get('juan', {}).get('text', ''):
            r['tag'] = ['juan_end']
        elif cls:
            for tag in ['juan', 'byline', 'dharani', 'head']:
                if tag == 'head' and len(xu_rows) > 1 and 'head' in xu_rows[0].get('tag', []):
                    xu = 'xu'  # 开启新的序
                if tag in cls:
                    r['tag'] = [tag]
                    tags[tag] = r
                    break
        return r, text, xu

    @gen.coroutine
    def fetch_cb(self, name, vol='001'):
        """下载CBeta页面原文，已下载则从缓存文件读取"""
        if '_' not in name:
            name += '_' + vol
        p = self.db.cb.find_one({'name': name})
        if p:
            return p['html'], p['title'], name

        url = f'https://api.cbetaonline.cn/download/html/{name}.html'
        client = AsyncHTTPClient()
        try:
            r = yield client.fetch(url, connect_timeout=30, request_timeout=30)
            if r.error:
                self.send_raise_failed(f'获取{name}文本失败: {r.error}')

            html = to_basestring(r.body)
            if html.startswith('{"'):
                return '', '', name
            m = re.search('<title>(.+)</title>', html, re.I)
            title = m and m.group(1).strip() or ''
            self.db.cb.update_one({'name': name}, {'$set': dict(
                html=html, title=title, size=len(html),
                created_by=self.username, created=self.now())}, upsert=True)
            return html, title, name
        except HTTPError as e:
            self.send_raise_failed(f'获取{name}文本失败: {str(e)}')

    def update_cb(self):
        for p in self.db.cb.find({'size': None}):
            self.db.cb.update_one({'_id': p['_id']}, {'$set': dict(size=len(p['html']))})


class ArticleImportCBApi(ImportCBApi):
    """重新导入经典内容"""
    URL = '/api/article/reimport/@oid'

    @gen.coroutine
    def post(self, a_id):
        try:
            a = self.get_article(a_id)
            changes = []
            for sec in self.db.section.find({'a_id': a['_id']}):
                if 'import_cb' in sec['source']:
                    yield from self.import_cb(sec, changes)
            self.send_success(changes)
            self.finish()
        except Exception as e:
            on_exception(self, e)

    def import_cb(self, s, changes):
        html, title, code = yield self.fetch_cb(s['source'].split(' ')[1])
        r, err = self.parse_html(html, title, code)
        if r['rows'] and r['rows'] != s['org_rows']:
            s_upd, n, checked = dict(org_rows=r['rows'], updated=self.now()), 0, []
            if s.get('rows'):
                s_upd['rows'] = s['rows']
                for i, old_r in enumerate(s['rows']):
                    if (old_r['line'] // 100) not in checked:
                        ref = [w for w in r['rows'] if w['line'] // 100 == old_r['line'] // 100]
                        ref = ref and ref[0]['text'][:5] == old_r['text'][:5] and ref[0]
                        if ref:
                            checked.append(old_r['line'] // 100)
                        if ref and ref.get('tag'):
                            while s['rows'][i]['line'] // 100 == ref['line'] // 100:
                                s['rows'][i]['tag'] = ref['tag']
                                n, i = n + 1, i + 1

            if n or not s.get('rows'):
                self.db.section.update_one({'_id': s['_id']}, {'$set': s_upd})
                self.log(f"section {code} {s['_id']} updated: {n} rows")
                changes.append(dict(code=code, s_id=str(s['_id'])))
