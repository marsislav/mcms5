from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

# Create your models here.
class Post(models.Model):
    title = models.CharField(max_length=75)
    body = CKEditor5Field('Съдържание', config_name='default')
    slug = models.SlugField(max_length=75, unique=True)
    date=models.DateTimeField(auto_now_add=True)
    banner=models.ImageField( default='fallback.png', blank=True) 

    def __str__(self):
        return self.title