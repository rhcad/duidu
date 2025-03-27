from srv.proj.api import ProjBaseApi, auto_try, json_util


class AddNoteApi(ProjBaseApi):
    """插入注解"""
    URL = '/api/proj/note/add'

    @auto_try
    def post(self):
        d, p = self.get_project_edit()
        note = d['note']
        note['id'] = self.util.md5(f"{d['leftAid']}.{d['noteAid']}.{json_util.dumps(note['left'])}")
        p['notes'] = p.get('notes', [])
        assert not [s for s in p['notes'] if s['id'] == note['id']], '重复保存'
        p['notes'].append(dict(left_aid=d['leftAid'], note_aid=d['noteAid'], **note))

        self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(updated_at=self.now(), notes=p['notes'])})
        self.send_success({'id': note['id']})


class DelNoteApi(ProjBaseApi):
    """删除注解"""
    URL = '/api/proj/note/del'

    @auto_try
    def post(self):
        d, p = self.get_project_edit()
        if d.get('all'):
            notes = EditNoteApi.sub_notes(p['notes'], d['note_a'])
            notes = [s for s in p['notes'] if s not in notes]
        else:
            notes = [s for s in p['notes'] if s['id'] != d['nid']]
        if notes == p['notes']:
            self.send_raise_failed('没有改变')

        self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(updated_at=self.now(), notes=notes)})
        self.send_success({'notes': EditNoteApi.sub_notes(notes, d['note_a'])})


class EditNoteApi(ProjBaseApi):
    """修改注解类型"""
    URL = '/api/proj/note/type'

    @auto_try
    def post(self):
        d, p = self.get_project_edit()
        note = ([s for s in p['notes'] if s['id'] == d['nid']] or [{}])[0]
        assert note, '没有此注解'
        old_type = note.get('type') or ('inline' if note.get('inline') else 'end')
        if d['type'] == old_type:
            self.send_raise_failed('没有改变')

        note['inline'] = 1 if d['type'] == 'inline' else 0
        if d['type'] == 'front':
            note['type'] = d['type']
        else:
            note.pop('type', 0)

        self.db.proj.update_one({'_id': p['_id']}, {'$set': dict(updated_at=self.now(), notes=p['notes'])})
        self.send_success({'notes': self.sub_notes(p['notes'], d['note_a'])})

    @staticmethod
    def sub_notes(notes, n_a):
        if n_a.get('note_for'):
            return [s for s in notes if s['left_aid'] == str(
                n_a['note_for']) and (not s.get('note_aid') or s['note_aid'] == str(n_a['_id']))]
        return [s for s in notes if s['left_aid'] == str(n_a['_id'])]
