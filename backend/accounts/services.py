from .models import User
from django.contrib.auth import authenticate

class AuthenticationService:

    @staticmethod
    def register_user(form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data["password"])
        user.save()

        return user
    
    @staticmethod
    def login_user(email, password):
        user = authenticate(
            email=email,
            password=password
        )

        return user