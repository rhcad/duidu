import logging
from tornado import ioloop
from tornado.options import options
from srv.app import Application
from srv import handlers, conv_placeholder
from srv.public import invalid, ui_module

if __name__ == '__main__':
    options.parse_command_line()
    app = Application([(conv_placeholder(c.URL), c) for c in handlers],
                      default_handler_class=invalid.Page404Handler,
                      ui_modules=ui_module.modules,
                      xsrf_cookies=True, xheaders=True)
    if app.db is None:
        exit(1)
    app.listen(options.port)
    logging.info('Start the maker on http://localhost:%d' % (options.port,))
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        logging.info('Stop the maker')
    finally:
        app.stop()
