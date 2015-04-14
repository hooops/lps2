# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from aca_course import views

urlpatterns = patterns('',
                       url(r'^home/',views.academic_home_view,name='academic_home'),
                       url(r'^school/list/',views.academic_school_list,name='school_list'),
                       url(r'^(?P<university_id>[\d]+)/$',views.academiccourse_list_view,name='academiccourse_list'),
                       url(r'^(?P<university_id>[\d]+)/(?P<course_id>[\d]+)/studentverify/$',views.student_verify_view,name='student_verify'),
                       url(r'^(?P<university_id>[\d]+)/(?P<course_id>[\d]+)/studentverifypost/$',views.student_verify_post,name='student_verify_post'),
                       #url(r'^studentverify/$',views.student_verify_view, name= 'student_verify_direct'),
                       )

