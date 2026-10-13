"""
search.views - the public site search at ``/search/?q=...``.

What is searched
----------------
* Pages  (``pages.Page``)  - only PUBLISHED ones: title, body text, meta description.
* Posts  (``posts.Post``)  - title and body text.

How matching works
------------------
1. The query is split into words (``"web design"`` -> ``web``, ``design``).
   A result must contain ALL words (AND), anywhere in title/body, in any order.
2. Case-insensitive, any language (Cyrillic included - see ``search/sqlite.py``).
3. The HTML of the body is stripped first, so markup such as ``class="mcms-col"``
   or ``<div>`` can never produce a match - only visible text counts.
4. Ranking: a word in the TITLE scores 5, in the meta description 2, in the body
   1 per occurrence (max 5); ties go to the newest item. Best first.
5. Each result shows a text snippet around the first match with the words
   highlighted (``<mark>``). 10 results per page.

Limits: queries shorter than 2 characters are ignored; at most 5 words are used.
"""
import html
import re

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape, strip_tags
from django.utils.safestring import mark_safe

from pages.models import Page
from posts.models import Post

MIN_LENGTH = 2        # shortest accepted word
MAX_TERMS = 5         # words used from the query
PER_PAGE = 10         # results per page
SNIPPET = 160         # characters of context shown around the match
CANDIDATES = 500      # safety cap on rows examined per model


def parse_query(q):
    """Split ``q`` into unique lower-case words (order kept), dropping too-short ones."""
    seen, terms = set(), []
    for w in re.split(r'\s+', (q or '').strip()):
        key = w.casefold()
        if len(w) >= MIN_LENGTH and key not in seen:
            seen.add(key)
            terms.append(w)
    return terms[:MAX_TERMS]


def plain_text(raw_html):
    """HTML -> visible text (tags removed, entities decoded, whitespace collapsed)."""
    text = html.unescape(strip_tags(raw_html or ''))
    return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()


def snippet(text, terms):
    """Excerpt of ``text`` around the first matching word, with matches wrapped in <mark>.

    Returns a safe HTML string (all text is escaped first).
    """
    low = text.casefold()
    first = min((p for p in (low.find(t.casefold()) for t in terms) if p >= 0), default=0)
    start = max(0, first - SNIPPET // 3)
    end = min(len(text), start + SNIPPET)
    part = text[start:end]
    out = escape(part)
    pattern = re.compile('|'.join(re.escape(escape(t)) for t in terms), re.IGNORECASE)
    out = pattern.sub(lambda m: '<mark>%s</mark>' % m.group(0), out)
    return mark_safe(('… ' if start > 0 else '') + out + (' …' if end < len(text) else ''))


def _score(title, body, meta, terms):
    """Return the relevance score, or ``None`` if some word is missing everywhere."""
    t, b, m = title.casefold(), body.casefold(), meta.casefold()
    score = 0
    for term in terms:
        w = term.casefold()
        in_title, in_meta, n_body = w in t, w in m, b.count(w)
        if not (in_title or in_meta or n_body):
            return None
        score += (5 if in_title else 0) + (2 if in_meta else 0) + min(n_body, 5)
    return score


def _db_filter(qs, terms, fields):
    """Cheap SQL pre-filter: every word must appear in at least one of ``fields``."""
    for term in terms:
        cond = Q()
        for f in fields:
            cond |= Q(**{f + '__icontains': term})
        qs = qs.filter(cond)
    return qs


def run_search(terms):
    """Return a list of result dicts (best first) for the given words."""
    results = []
    pages = _db_filter(Page.objects.filter(is_published=True), terms, ('title', 'body', 'meta_description'))
    for p in pages.select_related('parent')[:CANDIDATES]:
        body = plain_text(p.body)
        score = _score(p.title, body, p.meta_description, terms)
        if score is not None:
            results.append({'kind': 'Page', 'title': p.title, 'url': p.get_absolute_url(),
                            'snippet': snippet(body or p.meta_description, terms),
                            'score': score, 'date': p.updated})
    for post in _db_filter(Post.objects.all(), terms, ('title', 'body'))[:CANDIDATES]:
        body = plain_text(post.body)
        score = _score(post.title, body, '', terms)
        if score is not None:
            results.append({'kind': 'Post', 'title': post.title,
                            'url': reverse('posts:page', args=[post.slug]),
                            'snippet': snippet(body, terms), 'score': score, 'date': post.date})
    results.sort(key=lambda r: (r['score'], r['date']), reverse=True)
    return results


def search(request):
    """``/search/?q=<words>&page=<n>`` - Breadcrumbs: Home > Search."""
    q = request.GET.get('q', '').strip()
    terms = parse_query(q)
    page_obj = None
    total = 0
    if terms:
        paginator = Paginator(run_search(terms), PER_PAGE)
        total = paginator.count
        page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'search/results.html', {
        'q': q, 'terms': terms, 'page_obj': page_obj, 'total': total,
        'too_short': bool(q) and not terms,
        'page_title': 'Search',
        'breadcrumbs': [('Search', reverse('search'))],
    })
