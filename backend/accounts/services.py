from .models import User

class AuthenticationService:

    @staticmethod
    def register_user(form):
        user = form.save(commit=False)

        user.set_password(form.cleaned_data["password"])

        user.save()

        return user