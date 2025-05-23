import re
from srv.model import Model


class Proj(Model):
    fields = {
        'code': {'caption': '编码'},
        'name': {'caption': '名称'},
        'comment': {'caption': '备注'},
        'cols': {'caption': '栏数'},
        'toc_n': {'caption': '科判'},
        'note_n': {'caption': '注解'},
        'char_n': {'caption': '字数'},
        'char_k': {'caption': '千字', 'align': 'right'},  # 不存，动态显示
        'created_by': {'caption': '创建者', 'type': 'user'},
        'editors': {'caption': '协作人'},
        'public': {'caption': '公开', 'type': 'boolean'},
        'published': {'caption': '发布时间', 'type': 'time'},
        'columns': {'caption': '分栏'},  # {a_id,code,name,colspan,toc_i,notes}[]
        **Model.fields
    }
    hidden_fields = ['editors', 'public', 'published', 'columns', 'created_at', 'char_n']
    actions = [
        dict(id='edit', caption='修改', url='/proj/edit/@_id'),
        dict(id='view', caption='预览', url='/proj/view/@_id', default=True)
    ]


class Article(Model):
    types = ['经', '论', '注', '疏', '讲解', '其他']
    fields = {
        'proj_id': {'caption': '编码ID'},
        'code': {'caption': '编码'},
        'name': {'caption': '名称'},
        'type': {'caption': '类别', 'type': types},
        'colspan': {'caption': '宽度', 'type': ['1:一栏', '2:两栏', '3:三栏']},  # 对应于 Proj.columns[i].colspan
        'char_n': {'caption': '字数'},
        'created_by': {'caption': '创建者', 'type': 'user'},
        'sections': {'caption': '内容'},  # {_id,name}[]
        'note_tag': {'caption': '注解标签'},  # note_for
        **Model.fields
    }
    hidden_fields = ['proj_id', 'created_by', 'sections', 'created_at', 'updated_at']

    @classmethod
    def get_column_rows(cls, handler, article, pi=0):
        rows, ids = [], [s['_id'] for s in article['sections']]
        sec_coll = handler.db.section
        if pi > 0:
            res = [(pi + i, sec_coll.find_one({'_id': ids[pi + i]}))
                   if 0 <= pi + i < len(ids) else (0, None) for i in [-2, -1, 0]]
            for k, (i, sec) in enumerate(res):
                rs = sec and Section.get_rows(sec)
                if not rs:
                    continue
                rows.append(dict(s_i=i, s_id=sec['_id'], name=sec['name']))
                for r in (rs[-5:] if k == 0 else rs[:5] if k == 2 else rs):
                    r.update(dict(s_i=i, s_id=sec['_id']))
                    rows.append(r)
        else:
            sections = list(handler.db.section.find({'_id': {'$in': ids}}))
            for i, sec in enumerate(article['sections']):
                sec = [s for s in sections if s['_id'] == sec['_id']][0]
                rows.append(dict(s_i=i, s_id=sec['_id'], name=sec['name']))
                for r in Section.get_rows(sec):
                    r.update(dict(s_i=i, s_id=sec['_id']))
                    rows.append(r)
        return rows

    @classmethod
    def get_toc_row(cls, toc, toc_i, toc_id):
        if isinstance(toc_id, list):
            toc_id = [cls.get_toc_row(toc, toc_i, d) for d in toc_id]
            return [r for r in toc_id if r]
        if toc_id and toc and toc_i is not None:
            for r in toc[toc_i]['rows']:
                if r['id'] == toc_id:
                    return r


class Section(Model):
    NUMS = '一二三四五六七八九十百零〇'
    TAGS = dict(juan='章卷', juan_end='卷尾', byline='作译者', verse='偈颂 *', dharani='咒语 *',
                pin='品', head='小节', toc_line='科判行', num='CB编号', _='--清除以上 *', xu='序跋 *', _xu='--清除序跋 *')
    fields = {
        'a_id': {'caption': '文章ID'},
        'name': {'caption': '名称'},
        'source': {'caption': '来源'},
        'char_n': {'caption': '字数'},
        'created_by': {'caption': '创建者', 'type': 'user'},
        'org_rows': {'caption': '原文'},  # {line,text,tag}[]
        'rows': {'caption': '段落'},  # {line,text,row_i,del,tag,toc_ids,changed}[]
        **Model.fields
    }
    hidden_fields = ['a_id', 'created_by', 'org_rows', 'rows', 'created_at', 'updated_at']

    @staticmethod
    def get_rows(sec):
        if sec.get('rows') is None:
            sec['rows'] = [dict(r) for r in sec['org_rows']]
        for r in sec['rows']:
            if re.match('^[「“‘]', r['text']) and 'verse' in r.get('tag', []):
                r['tag'] = r.get('tag', []) + ['start-quot']
        return sec['rows']

    @staticmethod
    def get_row(rows, line):
        r = [r for r in rows if int(r['line']) == line]
        return r[0] if r else None


class Toc(Model):
    TOC_CH = '甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥'
    re_toc = re.compile('^[%s][初一二三四五六七八九十]' % TOC_CH)

    @classmethod
    def get_toc(cls, article, toc_i, t_id=None):
        toc = article['toc'][int(toc_i)]
        if t_id is not None:
            return toc, cls.get_row(toc['rows'], t_id)
        return toc

    @classmethod
    def get_row(cls, rows, t_id):
        r = [r for r in rows if r['id'] == t_id]
        return r[0] if r else None


class ProjNote(Model):
    """对应于 Proj.columns[i].notes """
    fields = {
        'base': {'caption': '栏名'},
        'tag': {'caption': '标签'},
        'code': {'caption': '编码'},
        'name': {'caption': '注解名称'},
    }
    actions = [
        dict(id='edit', caption='合并注解', url='/proj/notes/@_id', default=True),
        dict(id='view', caption='段落格式', url='/proj/para/@_id'),
        dict(id='view', caption='查看经典', url='/article/@_id')
    ]
