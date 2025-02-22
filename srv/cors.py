# -*- coding: utf-8 -*-
import inspect

from tornado.web import RequestHandler


def _get_class_that_defined_method(meth):
    for cls in inspect.getmro(meth.__self__.__class__):
        if meth.__name__ in cls.__dict__:
            return cls
    return None


class CorsMixin(RequestHandler):

    CORS_HEADERS = None
    CORS_METHODS = None
    CORS_CREDENTIALS = True
    CORS_CACHES = False
    CORS_MAX_AGE = 86400
    CORS_EXPOSE_HEADERS = None

    def set_default_headers(self):
        if self.CORS_EXPOSE_HEADERS:
            self.set_header('Access-Control-Expose-Headers', self.CORS_EXPOSE_HEADERS)
        if self.CORS_CACHES:
            self.set_header('Cache-Control', 'no-cache')

    def options(self):
        if self.CORS_HEADERS:
            self.set_header('Access-Control-Allow-Headers', self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self.CORS_METHODS or self._get_methods())
        if self.CORS_CREDENTIALS is not None:
            self.set_header('Access-Control-Allow-Credentials',
                            'true' if self.CORS_CREDENTIALS else 'false')
        if self.CORS_MAX_AGE:
            self.set_header('Access-Control-Max-Age', self.CORS_MAX_AGE)
        if self.CORS_EXPOSE_HEADERS:
            self.set_header('Access-Control-Expose-Headers', self.CORS_EXPOSE_HEADERS)

        self.set_status(204)
        self.finish()

    def _get_methods(self):
        supported_methods = [method.lower() for method in self.SUPPORTED_METHODS]
        methods = []
        for meth in supported_methods:
            instance_meth = getattr(self, meth)
            if not meth:
                continue
            handler_class = _get_class_that_defined_method(instance_meth)
            if handler_class is not RequestHandler:
                methods.append(meth.upper())

        return ', '.join(methods)
