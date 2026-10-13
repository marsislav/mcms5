# Comments

App `comments` · model `Comment` · admin: **Comments** (moderation) and **Settings → Discussion** (options).
Comments exist for **blog posts only** (not pages).

## Settings → Discussion

| Option | Default | Effect |
|---|---|---|
| **Enable comments** | on | Master switch. Off = form, comments and the comment counts are hidden everywhere and posting is refused (nothing is deleted). |
| **Comment approval** | Manual | *Manual*: every comment waits for an admin. *Automatic*: published at once. *Returning commenters*: published at once only if the same e-mail already has an approved comment. Staff users are always approved. |
| **Name and e-mail required** | on | If off, name is optional (shown as "Anonymous") and e-mail may be empty. The e-mail is never shown. |
| **Only registered users can comment** | off | Shows "log in to comment" (link to the login page, which returns to the post) instead of the form. Logged-in users comment under their account name. |
| **Enable replies (threaded)** | on | "Reply" link under each comment; replies are nested under their parent. |
| **Reply depth** | 3 | 2-10 levels (3 = comment, reply, reply to the reply). Only when replies are on. |
| **Close comments after (days)** | 0 | Posts older than N days no longer accept comments. 0 = never. |
| **Hold for approval if more links than** | 2 | More links → always pending, even with automatic approval. |
| **Blocked words** | empty | One per line, case-insensitive; a match in text/name/e-mail → marked **spam**, never shown. |
| **E-mail me about new comments** | off | Sends a message to *General → Admin e-mail* (needs working e-mail settings; failures are ignored). |

Per post: **Allow comments** checkbox in the post editor (the global switch must also be on).

## Moderation

Admin → **Comments**: filter by status (*Pending / Approved / Spam*), search, bulk actions
**Approve**, **Mark as pending**, **Mark as spam**. Only *approved* comments are shown or counted.
A reply whose parent is not approved is hidden with it. Deleting a comment deletes its replies (no Trash for comments).

## How it works

* The post page ends with `{% comments_section post %}` (`comments/templatetags/comments_tags.py`).
* The form posts to `POST /comments/post/<post_id>/` (`comments:submit`); then the visitor is redirected back with
  `?commented=approved|pending` (a thank-you / "awaiting moderation" notice).
* Rules (open/closed, status for a new comment) are in `comments/services.py`.
* "Reply" is a plain link `?replytocom=<id>#respond` - no JavaScript.
* Spam protection: hidden honeypot field (filled = silently dropped), link limit, blocked words, duplicate check,
  CSRF, all output escaped (links get `rel="nofollow"`). A spammy comment looks "pending" to the sender.
* The top-level URL segment `comments` is now a fixed route: don't create a top-level CMS page with the slug `comments`.
* Styles: `static/css/mcms-comments.css`.
