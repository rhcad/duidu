from srv.model import Model


class User(Model):
    fields = {
        'username': {'caption': '用户名'},
        'nickname': {'caption': '昵称'},
        'ip': {'caption': 'IP地址'},
        **Model.fields
    }
    hidden_fields = []
