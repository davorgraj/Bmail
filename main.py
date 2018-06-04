#!/usr/bin/env python
import os
import jinja2
import webapp2
import hmac
import ast
from google.appengine.ext import ndb
from webapp2_extras import sessions
from user import Users
from message import Messages
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir), autoescape=False)


class BaseHandler(webapp2.RequestHandler):

    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_template(self, view_filename, params=None):
        if not params:
            params = {}

        params["current_user"] = self.current_user()

        if not self.current_user():
            return self.redirect_to("login")

        template = jinja_env.get_template(view_filename)
        self.response.out.write(template.render(params))

    def render_accsess_template(self, view_filename, params=None):
        if not params:
            params = {}

        template = jinja_env.get_template(view_filename)
        self.response.out.write(template.render(params))

    @webapp2.cached_property
    def session(self):
        return self.session_store.get_session()

    def get_password_hash(self, password):
        return hmac.new(bytearray('bmail' + password, "utf-8")).hexdigest()

    def current_user(self):
        user_id = self.session.get("current_user")
        if not user_id:
            return False

        return Users.get_by_id(user_id)


class BmailHandler(BaseHandler):
    def get(self):
        messages = Messages.query(
            Messages.deleted == False,
            ndb.OR(
                Messages.sender == self.current_user().key,
                Messages.receiver == self.current_user().key,
            )
        ).fetch()

        params = {"messages": messages}
        return self.render_template("bmail.html", params=params)

    def post(self):
        receiver_mail = self.request.get("email")
        receiver = Users.query(Users.email == receiver_mail).get()

        if not receiver:
            params = {
                "notification": "Uporabnik " + receiver_mail + " ne obstaja.",
                "alert_type": "danger"
            }
            return self.render_template("bmail.html", params=params)

        message = self.request.get("message")

        Messages(
            message=message,
            sender=self.current_user().key,
            receiver=receiver.key
        ).put()
        params = {
            "notification": "Uspesno poslano " + receiver_mail,
            "alert_type": "success"
        }
        return self.render_template("bmail.html", params=params)


class LoginHandler(BaseHandler):
    def get(self):
        params = []
        if "params" in self.request.GET:
            params = ast.literal_eval(self.request.GET["params"])

        return self.render_accsess_template("login.html", params=params)

    def post(self):
        email = self.request.get("email")
        password = self.get_password_hash(
            self.request.get("password") + self.request.get("email")
        )

        query = Users.query(Users.password == password, Users.email == email)
        user = query.get()
        if user:
            self.session["current_user"] = user.key.id()
            return self.redirect_to("home")

        params = {
            "notification": "Uporabnisko ime ali geslo ni pravilno",
            "alert_type": "danger"
        }
        return self.render_accsess_template("login.html", params=params)


class SignUpHandler(BaseHandler):
    def get(self):
        return self.render_accsess_template("sign_up.html")

    def post(self):
        name = self.request.get("name")
        email = self.request.get("email")
        password = self.get_password_hash(
            self.request.get("password") + self.request.get("email")
        )

        user = Users.query(Users.email == email).get()
        if user:
            params = {
                "notification": "Uporabnik " + user.email + " ze obstaja.",
                "alert_type": "danger"
            }
            return self.render_accsess_template("sign_up.html", params=params)

        Users(email=email, password=password, name=name).put()
        params = {
            "notification": "Uspesno registrirani",
            "alert_type": "success"
        }
        return self.redirect_to("login", params=params)


class LogoutHandler(BaseHandler):
    def get(self):
        self.session["current_user"] = []
        return self.redirect_to("login")


class SentMessagesHandler(BaseHandler):
    def get(self):
        messages = Messages.query(
            Messages.deleted == False,
            Messages.sender == self.current_user().key
        ).fetch()

        params = {"messages": messages}
        return self.render_template("sent_messages.html", params=params)


class ReceivedMessagesHandler(BaseHandler):
    def get(self):
        messages = Messages.query(
            Messages.deleted == False,
            Messages.receiver == self.current_user().key
        ).fetch()

        params = {"messages": messages}
        return self.render_template("received_messages.html", params=params)


class MessageDeleteHandler(BaseHandler):
    def post(self, message_id):
        message_delete = Messages.get_by_id(int(message_id))
        message_delete.key.delete()
        message_delete.deleted = True
        message_delete.put()
        return self.redirect_to("home")


class DeletedMessagesHandler(BaseHandler):
    def get(self):
        deleted_messages = Messages.query(
            Messages.deleted == True,
            ndb.OR(
                Messages.sender == self.current_user().key,
                Messages.receiver == self.current_user().key,
            )
        ).fetch()
        params = {"deleted_messages": deleted_messages}
        return self.render_template("deleted_messages.html", params=params)


config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'some-secret-key',
}

app = webapp2.WSGIApplication([
    webapp2.Route('/', BmailHandler, name="home"),
    webapp2.Route('/login', LoginHandler, name="login"),
    webapp2.Route('/sign_up', SignUpHandler),
    webapp2.Route('/logout', LogoutHandler),
    webapp2.Route('/sent_messages', SentMessagesHandler),
    webapp2.Route('/received_messages', ReceivedMessagesHandler),
    webapp2.Route('/deleted_messages/<message_id:\d+>', MessageDeleteHandler),
    webapp2.Route('/deleted_messages', DeletedMessagesHandler),
], debug=True, config=config)
