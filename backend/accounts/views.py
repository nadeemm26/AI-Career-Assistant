from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import RegistrationForm
from .services import AuthenticationService


def register(request):

    if request.method == "POST":

        form = RegistrationForm(request.POST)

        if form.is_valid():

            AuthenticationService.register_user(form)

            messages.success(
                request,
                "Registration completed successfully."
            )

            return redirect("login")

    else:

        form = RegistrationForm()

    context = {
        "form": form
    }

    return render(
        request,
        "accounts/register.html",
        context,
    )