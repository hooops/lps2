from django.conf.urls import patterns, url, include
from mz_course import views

urlpatterns = patterns('',
                         url(r'^$',views.course_list_view,name='course_list'),
                         url(r'^ajax/$',views.course_list_view_ajax,name='course_list_ajax'),
                         url(r'^(?P<course_id>[\d]+)/$',views.course_view,name='course_detail'),
                         url(r'^(?P<course_id>[\d]+)/(?P<university_id>[\d]+)$',views.course_view,name='course_detail_academic'),
                         url(r'^add/comment/$',views.add_comment,name='add_comment'),
                         url(r'^(?P<course_id>[\d]+)/recent/play/$',views.course_recent_play,name='course_recent_play'),
                         url(r'^(?P<course_id>[\d]+)/favorite/update/$',views.update_favorite,name='update_favorite'),
                         url(r'^(?P<careercourse_id>[\d]+)/pay/other/$',views.course_pay_other,name='course_pay_other'),
)