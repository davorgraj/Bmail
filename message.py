from google.appengine.ext import ndb
from user import Users


class Messages(ndb.Model):
    message = ndb.TextProperty()
    created_at = ndb.DateTimeProperty(auto_now_add=True)
    deleted = ndb.BooleanProperty(default=False)
    sender = ndb.KeyProperty(kind=Users)
    receiver = ndb.KeyProperty(kind=Users)
