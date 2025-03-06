from tornado.web import UIModule
from tornado.template import Template
from srv import util
from srv.proj.model import Article


class Table(UIModule):
    def render(self, model, rows):
        assert isinstance(rows, list)
        for r in rows:
            assert isinstance(r, dict)
        fields = dict((k, v) for k, v in model.fields.items()
                      if k not in model.hidden_fields and [1 for r in rows if r.get(k)])
        return self.render_string('_/table.html', model=model, fields=fields, rows=rows, util=util)


class TopNav(UIModule):
    def render(self, title='', prev=None, themes=True, download=False):
        return self.render_string('_/nav.html', prev=prev, title=title,
                                  themes=themes, download=download)


class Users(UIModule):
    def render(self, usernames, tip=''):
        t = Template('''<span class="users">
  {% set users = handler.util.get_users(handler.db, usernames) %}
  {% for u in usernames %}
  {% set u=([s for s in users if s['username']==u] or [dict(username=u, nickname='无')])[0] %}
  <span class="gray" title="用户名: {{u['username']}}">
    {% if u['username'] == handler.username %} 我 {% else %}{{u['nickname']}}{% end %}
  </span>{% end %}
  {% if not users %}
  <span class="m-r-10 gray">无　{{tip}}</span>
  {% end %}
</span>''')
        return t.generate(**self.handler.kwargs_render(usernames=usernames, tip=tip))


class RadioGroup(UIModule):
    def render(self, field, obj=None, required=False):
        assert isinstance(field['type'], list)
        t = Template('''
<div class="modal-radio{{' required' if required else ''}} id="modal-{{k}}" name="{{k}}">
{% for i, t in enumerate(field['type']) %} {% set v, t = t.split(':') if ':' in t else (t,t) %}
<input type="radio" id="{{k}}-{{i}}" name="r_{{k}}" value="{{v}}"
  {{'checked' if obj and str(obj.get(k)) == v else ''}}>
<label for="{{k}}-{{i}}">{{t}}</label>
{% end %}</div>''')
        return t.generate(**self.handler.kwargs_render(
            k=field['id'], field=field, obj=obj, required=required))


class BoolGroup(UIModule):
    def render(self, field_id, obj=None, required=False):
        v = (obj or {}).get(field_id)
        v = 1 if v in [True, 'true'] else -1 if v is None else 0
        t = Template('''
<div class="modal-radio bool{{' required' if required else ''}} id="modal-{{k}}" name="{{k}}">
{% for i, t in enumerate(['否', '是']) %}
<input type="radio" id="{{k}}-{{i}}" name="r_{{k}}"
       value="{{i}}" {{'checked' if v == i else ''}}>
<label for="{{k}}-{{i}}">{{t}}</label>
{% end %}</div>''')
        return t.generate(**self.handler.kwargs_render(k=field_id, v=v, required=required))


class SectionBlock(UIModule):
    @staticmethod
    def gen_line(line):
        a, b = line // 100, line % 100
        return f"#{a}{'-%d' % b if b else ''}"

    def render(self, cell, row_i=None):
        t = Template('''<p class="col-name gray ellipsis">{{c['code']}} {{c['name']}}</p>
{% for r in c['rows'] %}{% set tags = r.get('tag',[]) %}
{% if r.get('name') %}
    {% if row_i is None and r['s_i'] %}
    <p class="sec gray ellipsis" data-s-i="{{r['s_i']}}" data-id="{{
    r['s_id']}}"><small>{{r['s_i'] + 1}} {{r['name']}}</small></p>{% end %}
{% elif r.get('row_i') == row_i %}
    {% set d_tag = [s for t,s in tags_d if t in tags] %}
    {% set tc = get_toc(c.get('toc'),c.get('toc_i'),r.get('toc_ids',[])) %}
    {% for t in tc %}{% if t.get('s_id') %}
    <p class="toc_row ellipsis" data-toc-i="{{c['toc_i']}}" data-toc-id="{{t['id']}}" data-level="{{
    t['level']}}" data-line="{{t['line']}}" data-s-id="{{t['s_id']}}">{{t['text']}}</p>
    {% end %}{% end %}
    <span title="{{gen_line(r['line'])}}{{
    ' 拆分的段落' if r['line']%100 else ''}}{{
    ' |后有合并段落' if '|' in r['text'] else ''}}" class="p-head{{
    ' split' if r['line']%100 else ''}}{{
    ' merge' if '|' in r['text'] else ''}}{{
    ''.join(' '+s for s in tags if s in ['xu', 'xu_first', 'xu_end', 'dharani']) }}{{
    ' del' if r.get('del') else ''}}"{% if d_tag %} data-tag="{{d_tag[0]}}"{% end %}></span>
    <p class="text {{'del ellipsis' if r.get('del') else 'ellipsis-n'}}{{
    ''.join([' ' + s for s in tags])}}" data-line="{{
    r['line']}}"{% if tc %} data-toc-i="{{c['toc_i']}}" data-toc-id="{{tc[-1]['id']}}"{% end %} data-line-s="{{
    gen_line(r['line'])}}" data-s-i="{{
    r['s_i']}}" data-s-id="{{r['s_id']}}">{{ r['text'] }}</p>
{% end %}{% end %}''')
        tags_d = dict(juan='卷', juan_end='尾', verse='颂', dharani='咒',
                      pin='品', head='节', xu='序', byline='作').items()
        return t.generate(**self.handler.kwargs_render(
            c=cell, row_i=row_i, gen_line=self.gen_line, get_toc=Article.get_toc_row, tags_d=tags_d))


class TocDropdown(UIModule):
    def render(self, all_toc, cur=0, ext=''):
        t = Template('''<div class="dropdown toc-dropdown">
  <div class="dropdown-toggle ellipsis" type="button" id="drop-toc{{ext}}"
   data-toggle="dropdown" aria-haspopup="true" aria-expanded="true">
    <span class="drop-toc-name">{{ toc[cur]['name'] }}</span> <span class="caret"></span>
  </div>
  <ul class="dropdown-menu" aria-labelledby="drop-toc{{ext}}">
    {% for i,t in enumerate(toc) %}
    <li data-i="{{i}}" data-a-id="{{
    t['a_id']}}" data-toc-i="{{t['toc_i']}}"><a>
    <span>{{t['name']}}</span><small>{{t['code']}}</small></a></li>
    {% end %}
  </ul></div>''')
        return t.generate(**self.handler.kwargs_render(toc=all_toc, cur=cur, ext=ext))


class Pager(UIModule):
    def render(self, pi, max_page, ul_cls=''):
        t = Template('''<nav aria-label="pagination" class="text-right no-select">
  <ul class="pagination {{ul_cls}}">
    {% set arr=[(i-10+4)//5*5, i-3, i-2, i-1, i, i+1, i+2, i+3, (i+10)//5*5] %}
    <li class="{{ 'disabled' if i < 2 else '' }}"><a href="{{path}}?page={{i-1}}" aria-label="Previous"><span aria-hidden="true">«</span></a></li>
    {% if 1 not in arr %}
    <li><a href="{{path}}?page=1" aria-label="Front"><span aria-hidden="true">1</span></a></li>
    {% end %}
    {% for j in arr %}
    {% if j == i %}
    <li class="active no-pointer"><a href="#">{{i}} <span class="sr-only">(current)</span></a></li>
    {% elif 0 < j <= max_page %}
    <li><a href="{{path}}?page={{j}}">{{j}}</a></li>
    {% end %}{% end %}
    {% if max_page not in arr %}
    <li><a href="{{path}}?page={{max_page}}" aria-label="End"><span aria-hidden="true">{{max_page}}</span></a></li>
    {% end %}
    <li class="{{ 'disabled' if i == max_page else '' }}"><a href="{{path}}?page={{i+1}}" aria-label="Next"><span aria-hidden="true">»</span></a></li>
  </ul>
</nav>''')
        return t.generate(**self.handler.kwargs_render(
            i=pi, max_page=max_page, ul_cls=ul_cls, path=self.request.path))


modules = dict(Table=Table, TopNav=TopNav, Users=Users, RadioGroup=RadioGroup, BoolGroup=BoolGroup,
               SectionBlock=SectionBlock, TocDropdown=TocDropdown, Pager=Pager)
