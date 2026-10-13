"""
mcms5.slugs - building URL slugs from titles (Bulgarian-aware).

Used by the admin forms of ``Page`` and ``Post`` (``pages/admin.py``,
``posts/admin.py``) to fill an EMPTY slug from the title. The browser does the
same live while typing with ``static/js/admin-slug.js`` - **both use the same
transliteration table, keep them in sync**.

Cyrillic is transliterated with the official Bulgarian "Streamlined System"
(Закон за транслитерацията, 2009): ``Уеб дизайн`` -> ``ueb-dizayn``,
``щастие`` -> ``shtastie``. Latin accents are removed (``café`` -> ``cafe``);
any other character is dropped; everything else becomes ``-``.

    slugify_bg('Нови услуги 2026!')   -> 'novi-uslugi-2026'
    unique_slug(qs, 'about', 'slug')  -> 'about' or 'about-2', 'about-3', ...
"""
import re
import unicodedata

# Bulgarian (official) + the extra Russian letters so mixed titles still work.
BG_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ж': 'zh', 'з': 'z',
    'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
    'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
    'ш': 'sh', 'щ': 'sht', 'ъ': 'a', 'ь': 'y', 'ю': 'yu', 'я': 'ya',
    'ы': 'y', 'э': 'e', 'ё': 'yo',
}


def slugify_bg(text, max_length=75):
    """Return a URL-safe slug (``[a-z0-9-]``) for ``text``; ``''`` if nothing usable remains."""
    text = (text or '').lower()
    text = ''.join(BG_MAP.get(ch, ch) for ch in text)
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return text[:max_length].strip('-')


def unique_slug(queryset, base, field='slug', max_length=75):
    """Return ``base`` or ``base-2``, ``base-3``... - the first value not used in ``queryset``.

    ``queryset`` must already be narrowed to the scope where the slug has to be
    unique (e.g. same parent) and exclude the object being edited.
    """
    candidate, n = base, 2
    while queryset.filter(**{field: candidate}).exists():
        suffix = '-%d' % n
        candidate = base[:max_length - len(suffix)].rstrip('-') + suffix
        n += 1
    return candidate
