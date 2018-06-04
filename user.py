from google.appengine.ext import ndb


class Users(ndb.Model):
    password = ndb.StringProperty()
    email = ndb.StringProperty()
    name = ndb.StringProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
