from django.urls import path
from . import views

urlpatterns = [
    path("resume/upload/",views.upload_resume,name="upload_resume",),
    path("resume/list/",views.resume_list,name="resume_list",),
]