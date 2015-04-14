from django.conf.urls import patterns, url, include
from mz_course import views

urlpatterns = patterns('',
            url(r'^(?P<lesson_id>[\d]+)/$',views.lesson_view,name='lesson_view'),
            url(r'^student/job/upload/$', views.job_upload,name="job_upload"),
            url(r'^(?P<lesson_id>[\d]+)/update/status/$',views.update_learning_lesson,name='update_learning_lesson'),
            url(r'^comment/$', views.lesson_comment,name="lesson_comment"),
            url(r'^hascourse/(?P<has_id>[\d]+)/$', views.has_course,name="has_course"),
)