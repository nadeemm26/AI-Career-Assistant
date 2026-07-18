from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

from .forms import RegistrationForm, LoginForm
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

def login_view(request):

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user = AuthenticationService.login_user(
                email,
                password
            )

            if user is not None:

                login(request, user)

                return redirect("dashboard")

            messages.error(
                request,
                "Invalid email or password."
            )

    else:

        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )

@login_required
def dashboard(request):
    return render(request, "accounts/dashboard.html")