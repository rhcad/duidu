import srv.util as _
from bson.objectid import ObjectId


class Model(object):
    fields = {
        'created_at': {'caption': '创建时间', 'type': 'time'},
        'updated_at': {'caption': '更新时间', 'type': 'time'},
    }
    hidden_fields = ['created_at', 'updated_at']
    actions = []

    @classmethod
    def get_field(cls, field_id):
        field = dict(cls.fields.get(field_id, {}))
        field['id'] = field_id
        return field

    @classmethod
    def format_rows(cls, rows, **p):
        for doc in rows:
            keys = list(set(doc.keys()) | set(cls.fields.keys()))
            for k in keys:
                field, value = cls.fields.get(k, {}), doc.get(k)
                if value and isinstance(value, list) and isinstance(value[0], dict):
                    cls.format_rows(value, **p)
                else:
                    doc[k] = _.format_value(value, **p)
                if not isinstance(doc[k], str) and field.get('type') == 'boolean':
                    doc[k] = '是' if doc[k] else '否'
                if doc[k] is None:
                    doc.pop(k)
        return rows

    @classmethod
    def convert_value(cls, field_id, value):
        ft = cls.get_field(field_id).get('type')
        if ft == 'boolean':
            value = value in ['true', True, '1', 1, '是']
        elif ft == 'time' and isinstance(value, str):
            value = _.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        elif value and isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = cls.pack_data(v, True)
        elif value and isinstance(value, dict):
            value = cls.pack_data(value, True)
        return value

    @classmethod
    def render_value(cls, field_id, value):
        ft = cls.get_field(field_id).get('type')
        if ft == 'boolean':
            value = '是' if value in ['true', True, '1', 1, '是'] else '否'
        elif ft == 'time' and isinstance(value, _.datetime):
            value = value.strftime('%Y-%m-%d %H:%M')
        elif isinstance(value, ObjectId):
            value = str(value)
        elif value and isinstance(value, list):
            for i, v in enumerate(value):
                value[i] = cls.unpack_data(v, True)
        elif value and isinstance(value, dict):
            value = cls.unpack_data(value, True)
        return value

    @classmethod
    def pack_data(cls, data, fields):
        return dict((k, cls.convert_value(k, data[k])) for k in (
            data.keys() if fields is True else fields) if data.get(k))

    @classmethod
    def unpack_data(cls, data, fields):
        return dict((k, cls.render_value(k, data[k])) for k in (
            data.keys() if fields is True else fields) if k in data)
