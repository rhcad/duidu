from . import view, api

handlers = [view.LoginHandler, view.RegisterHandler,
            view.ProfileHandler, view.PasswordHandler, view.ForgotHandler,
            api.LoginApi, api.RegisterApi, api.LogoutApi,
            api.ProfileApi, api.PasswordApi, api.ForgotApi]
