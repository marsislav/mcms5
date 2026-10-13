"""comments.forms - the public comment form. Adapts to Settings -> Discussion."""
from django import forms

from .models import Comment


class CommentForm(forms.Form):
    author_name = forms.CharField(label='Name', max_length=80, required=False)
    author_email = forms.EmailField(label='E-mail', required=False)
    body = forms.CharField(label='Comment', max_length=2000, widget=forms.Textarea(attrs={'rows': 5}))
    parent = forms.IntegerField(required=False, widget=forms.HiddenInput)
    # Honeypot: invisible to people (CSS), bots fill it in. A filled value = silently dropped.
    website = forms.CharField(required=False, label='Leave this empty',
                              widget=forms.TextInput(attrs={'autocomplete': 'off', 'tabindex': '-1'}))

    def __init__(self, *args, site, post, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.site, self.post = site, post
        self.user = user if user is not None and user.is_authenticated else None
        if self.user:                       # name/e-mail come from the account
            del self.fields['author_name']
            del self.fields['author_email']
        elif site.comments_require_name_email:
            self.fields['author_name'].required = True
            self.fields['author_email'].required = True
        if not site.comments_threaded:
            del self.fields['parent']

    def clean_body(self):
        body = self.cleaned_data['body'].strip()
        if not body:
            raise forms.ValidationError('Please write a comment.')
        return body

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        if self.user:
            data['author_name'] = self.user.get_full_name() or self.user.get_username()
            data['author_email'] = self.user.email
        else:
            data['author_name'] = (data.get('author_name') or '').strip() or 'Anonymous'
            data['author_email'] = data.get('author_email') or ''

        data['parent_obj'] = None
        parent_id = data.get('parent')
        if parent_id:
            parent = Comment.objects.filter(pk=parent_id, post=self.post, status=Comment.APPROVED).first()
            if parent is None:
                raise forms.ValidationError('The comment you are replying to no longer exists.')
            if parent.depth() >= self.site.comments_max_depth:
                raise forms.ValidationError('Replies cannot be nested any deeper.')
            data['parent_obj'] = parent

        if Comment.objects.filter(post=self.post, author_name=data['author_name'],
                                  author_email=data['author_email'], body=data['body']).exists():
            raise forms.ValidationError('Duplicate comment - you have already said that.')
        return data
