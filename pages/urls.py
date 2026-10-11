from django.urls import path
from . import views

app_name = 'pages'
urlpatterns = [
    # Catch-all: MUST stay the LAST include in the project urls.py,
    # so /admin/, /posts/, /about/ etc. keep working.
    path('<path:path>/', views.page_detail, name='detail'),
]
