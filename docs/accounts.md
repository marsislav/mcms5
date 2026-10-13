# Accounts: register, login, forgot password

App `users` (uses Django's built-in `User`). All pages extend `layout.html`.

| URL | What |
|---|---|
| `/users/register/` | Sign-up: username, **e-mail (required, unique)**, password twice. Then goes to the login page. New users are not staff. |
| `/users/login/` | Log in. Honours `?next=/some/path` (only same-site paths; external URLs are ignored). Default landing: `LOGIN_REDIRECT_URL` (the blog list). A logged-in user opening it is redirected away. |
| `/users/logout/` | **POST only** (the "Logout" button in the top bar is a small form). Goes to the blog list. |
| `/users/password-reset/` | "Forgot your password?" - asks for the e-mail. |
| `/users/password-reset/done/` | "Check your e-mail" - shown for ANY address, so nobody can probe which e-mails have accounts. |
| `/users/reset/<uid>/<token>/` | Link from the e-mail: choose a new password (password validators apply). Works once; expires after `PASSWORD_RESET_TIMEOUT` (3 days). |
| `/users/reset/done/` | "Password changed" -> log in. |

The top bar of every page shows **Login / Register**, or the user name + **Logout**.

## E-mail delivery (needed for "forgot password")

By default `settings.py` uses the **console backend**: the reset e-mail is *printed in the terminal* running
`manage.py runserver` - nothing is really sent (fine for development). For production set SMTP via environment variables:

```
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL="My Site <no-reply@example.com>"
```

(also used by the comment notifications, see comments.md). The link in the e-mail uses the host of the request, so
`ALLOWED_HOSTS` must contain your domain in production.

## Notes

* Users created before this change (or in the admin) may have **no e-mail** - they can't use "forgot password" until an
  admin fills in the e-mail (admin -> Users). An admin can also set a new password there.
* There is no login rate limiting yet; for a public site add one (e.g. `django-axes`) or limit it at the web server.
* Templates: `users/templates/users/*.html`, e-mail text: `password_reset_email.txt`, `password_reset_subject.txt`.
* Code: `users/views.py` (thin subclasses of Django's `auth.views`), `users/forms.py`.
