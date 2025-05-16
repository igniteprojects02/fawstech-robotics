from django.contrib.auth.backends import ModelBackend
from admin_panel.models import User

class EmailAuthBackend(ModelBackend):
    """Authenticate using email instead of username."""
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
