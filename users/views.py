"""users.views - public user registration."""
from django.http import request
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


def register_view(request):
    """Show and process the sign-up form (username + password twice).

    GET   -> empty ``UserCreationForm``.
    POST  -> validate; on success create the user and redirect to the blog list
             (``posts:list``). On errors, re-render the form with messages.

    Notes:
    * The new user is NOT logged in automatically and is NOT staff, so they
      cannot enter the admin or see draft pages.
    * There is no login view/URL in this project yet (only the admin login at
      ``/admin/``).
    * Uses Django's CSRF protection (the template contains ``{% csrf_token %}``).
    Template: ``users/templates/users/register.html``.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('posts:list')
    else:
        form = UserCreationForm()

    return render(request, 'users/register.html', {"form": form})


def login_view(request): 
    if request.method == "POST": 
        form = AuthenticationForm(data=request.POST)
        if form.is_valid(): 
            login(request, form.get_user())
            return redirect("posts:list")
    else: 
        form = AuthenticationForm()
    return render(request, "users/login.html", { "form": form })