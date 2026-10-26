from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from .forms import LoginForm, SignupForm


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully. Please log in.")
            return redirect("accounts:login")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    redirect_to = request.POST.get('next') or request.GET.get('next') or 'home'

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f"Welcome back, {form.get_user().username}!")
            return redirect(redirect_to)
    else:
        form = LoginForm(request)

    return render(request, "accounts/login.html", {
        "form": form,
        "next": redirect_to,
    })


@login_required
def home_view(request):
    return render(request, "accounts/home.html", {
        "user": request.user,
    })


def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("accounts:login")
