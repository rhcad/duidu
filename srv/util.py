import re
import hashlib
from bson.objectid import ObjectId
from datetime import datetime, timedelta, timezone


def prop(obj, key: str, default=None):
    p = {} if obj is None else obj
    for k in key.split('.'):
        k = int(k) if re.match(r'^\d+$', k) else k
        if isinstance(p, list):  # k: int, index
            p = p[k] if len(p) > k > -1 else None
        else:
            p = p.get(k) if isinstance(p, dict) else None
    return default if p is None else p


def md5(text, salt=''):
    m = hashlib.md5()
    m.update((text + salt).encode('utf-8'))
    return m.hexdigest()


def format_value(value, **p):
    if isinstance(value, datetime):
        value = get_date_time(p.get('time_format', '%Y-%m-%d %H:%M'), value)
    elif isinstance(value, list):
        value = ','.join([str(v) for v in value])
    elif isinstance(value, ObjectId):
        value = str(value)
    return value


def get_date_time(fmt=None, time=None):
    time = time or datetime.now()
    if isinstance(time, str):
        try:
            time = datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return time

    time_zone = timezone(timedelta(hours=8))
    return time.astimezone(time_zone).strftime(fmt or '%Y-%m-%d %H:%M:%S')


def sub_prop(text, obj):
    return re.sub('@([A-Za-z0-9_]+)', lambda m: obj[m.group(1)], text)


def trim_bracket(text):
    return re.sub(r'[（）【】()\[－，。：；？-].*$', '', text).strip()


def get_users(db, usernames):
    return usernames and list(db.user.find({'username': {'$in': usernames}},
                                           projection=dict(username=1, nickname=1)))


def parse_vol(text):
    assert re.match(r'^([0-9]{1,3})([ ,~-][0-9]{1,3})*$', text), '卷号格式错误'
    texts, pos, items = re.split('[ ,~-]', text), 0, []
    for i, t in enumerate(texts):
        n, c = int(t), i and text[pos]
        if c == '~' or c == '-':
            assert items[-1] < n, '无效的卷号范围'
            for v in range(items[-1] + 1, n):
                items.append(v)
        items.append(n)
        pos += len(t)
        pos += 1 if i else 0
    return ['%03d' % n for n in items]
