from django.urls import path
# relative path needed for the code to pass
from .views import Index 

urlpatterns = [
    path("/test", Index.as_view(), name="index")
]
