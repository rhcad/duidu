from . import user, home, proj

handlers = user.handlers + home.handlers + proj.handlers

_placeholders = {
    'oid': '[a-z0-9]{24}',
}


def conv_placeholder(url):
    for k, v in _placeholders.items():
        if k in url:
            url = url.replace('@' + k, '(' + v + ')')
    return url
