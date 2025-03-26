import logging
from tornado import ioloop
from tornado.options import options
from srv.app import Application
from srv import handlers, conv_placeholder
from srv.public import invalid, ui_module
import webbrowser


if __name__ == '__main__':
    options.parse_command_line()
    app = Application([(conv_placeholder(c.URL), c) for c in handlers],
                      default_handler_class=invalid.Page404Handler,
                      ui_modules=ui_module.modules,
                      xsrf_cookies=True, xheaders=True)
    if app.db is None:
        exit(1)
    try:
        webbrowser.open('http://localhost:%d' % options.port)
        app.listen(options.port)
    except OSError:
        exit(0)
    logging.info('Start the maker v%s on http://localhost:%d' % (app.version, options.port))
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info('Stop the maker')
    finally:
        app.stop()
