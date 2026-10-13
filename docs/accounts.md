# Accounts: register, login, forgot password, profiles, authors

App `users` (uses Django's built-in `User`). All pages extend `layout.html`.

| URL | What |
|---|---|
| `/users/register/` | Sign-up: username, **e-mail (required, unique)**, password twice. Then goes to the login page. New users are not staff. |
| `/users/profile/` | **My profile** (log in required): display name, **photo**, short description, location, website. |
| `/users/author/<username>/` | Public **author page**: the profile + all posts of that author (10 per page, newest first). |
| `/users/login/` | Log in. Honours `?next=/some/path` (only same-site paths; external URLs are ignored). Default landing: `LOGIN_REDIRECT_URL` (the blog list). A logged-in user opening it is redirected away. |
| `/users/logout/` | **POST only** (the "Logout" button in the top bar is a small form). Goes to the blog list. |
| `/users/password-reset/` | "Forgot your password?" - asks for the e-mail. |
| `/users/password-reset/done/` | "Check your e-mail" - shown for ANY address, so nobody can probe which e-mails have accounts. |
| `/users/reset/<uid>/<token>/` | Link from the e-mail: choose a new password (password validators apply). Works once; expires after `PASSWORD_RESET_TIMEOUT` (3 days). |
| `/users/reset/done/` | "Password changed" -> log in. |

The top bar of every page shows **Login / Register**, or the user name (a link to *My profile*) + **Logout**.

## Profiles and post authors

Every user has a `Profile` (created automatically; the migration created one for existing users).

| Field | Notes |
|---|---|
| Display name | max 80; empty = full name, then username |
| Photo | JPG/PNG/GIF/WebP, max **2 MB**, stored in `media/avatars/`; replacing/clearing/deleting the user removes the old file. SVG is refused on purpose. Without a photo a circle with the first letter is shown. |
| About me | max 500 characters, plain text (HTML is escaped) |
| Location, Website | website must start with `http://` or `https://`; shown with `rel="nofollow noopener ugc"` |

The **e-mail is never shown**.

**Post authors.** `Post.author` (admin -> Posts) says who wrote a post. A new post created in the admin gets the
logged-in user automatically; you can pick another user. Existing posts got the **first superuser** as author from migration `posts/0009`
(change it per post in the admin; posts without an author show no author info). Deleting the user keeps the post.

For a post with an author the site shows:

* "by *Name*" next to the date (post page, blog list, category list);
* the **author box** after the post text: photo, name, location, about, *All posts by Name (N)* and the website link;
* the author page `/users/author/<username>/` with all (not trashed) posts. It is public only for users who have at least
  one post (users can always open their own); inactive users give 404.

Admin -> Settings -> **Users** has the switch *Show the post author* (hides the byline and the box everywhere) and
*E-mail me about new registrations*. Admin -> Users shows the profile under the account fields.

In templates: `{% load users_tags %}` -> `{% author_box post %}`, `{{ post.author|author_name }}`.

## E-mail delivery (needed for "forgot password" and notifications)

Since the **E-mail** section exists in admin -> Settings, the sending method is chosen there (no restart needed, see
[settings.md](settings.md)): server default, console, `.eml` files, or an **SMTP server** - for a local server use host
`localhost`, port 25 (Postfix/Exim) or 1025 (Mailpit/MailHog), security *None*, no user. Notifications go to the
**Admin e-mail** (General): new comments (if enabled), new registrations, the test e-mail.

The rest of this section describes the **"Server default"** method (the original behaviour).

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
* Code: `users/views.py` (auth views + `profile_edit`, `author_page`), `users/forms.py`, `users/models.py` (`Profile`),
  `users/signals.py`, `users/templatetags/users_tags.py`, `users/admin.py`. Templates `profile.html`, `author.html`,
  `_author_box.html`; styles `static/css/mcms-users.css`.
* Tests: `users/tests.py`, `users/test_profiles.py`.
