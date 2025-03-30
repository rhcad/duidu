import sys
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
        sys.exit(1)
    try:
        port = int(app.config.get('port', options.port))
        if app.mock_path:  # app made by installer
            webbrowser.open('http://localhost:%d' % port)
        app.listen(port)
        logging.info('Start the maker v%s on http://localhost:%d' % (app.version, port))
        ioloop.IOLoop.current().start()
    except OSError:
        logging.info('ignore same port')
        sys.exit(0)
    except KeyboardInterrupt:
        logging.info('Stop the maker')
    finally:
        app.stop()
