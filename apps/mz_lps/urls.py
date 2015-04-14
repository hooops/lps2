# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url
from mz_lps import views

from mz_lps import teacher_views

urlpatterns = patterns('',

                       url(r'learning/plan/(?P<careercourse_id>[\d]+)/$',
                           views.learning_plan_view,
                           name='learning_plan'),

                       url(r'project/upload/$',
                           views.project_upload,
                           name='project_upload'),

                       url(r'course/rebuild/(?P<course_id>[\d]+)/$',
                           views.rebuild_course,
                           name='rebuild_course'),

                       url(r'quiz/answer/(?P<quiz_id>[\d]+)/(?P<select>[^/]{1})/$',
                           views.answer_quiz,
                           name='answer_quiz'),

                       url(r'paper/result/(?P<type>[^/]+)/(?P<type_id>[\d]+)/$',
                           views.get_paper_result,
                           name='get_paper_result'),

                       url(r'course/novice/(?P<careercourse_id>[\d]+)/$',
                           views.get_all_course_novice_info,
                           name='get_all_course_novice_info'),

                       url(r'learning/plan/(?P<careercourse_id>[\d]+)/build/$',
                           views.build_learning_plan,
                           name='build_learning_plan'),

                       url(r"learning/plan/(?P<careercourse_id>[\d]+)/restore/$",
                           views.learning_restore,
                           name="learning_restore"),

                       url(r'user/teacher/class_manage/(?P<class_id>[\d]+)/$',
                           teacher_views.class_manage,
                           name='class_manage'),

                       url(r"user/teacher/class_manage/(?P<class_id>[\d]+)/(?P<user_id>[\d]+)/$",
                           teacher_views.student_detail,
                           name="student_detail"),

                       url(r"user/teacher/pause_planning/$",
                           teacher_views.pause_planning,
                           name="pause_planning"),

                       url(r"user/teacher/restore_planning/$",
                           teacher_views.restore_planning,
                           name="restore_planning"),

                       url(r"user/teacher/set_course_project_score/$",
                           teacher_views.set_course_project_score,
                           name="set_course_project_score"),

                       url(r"user/teacher/add_mission/$",
                           teacher_views.add_mission,
                           name="add_mission"),

                       url(r"user/teacher/edit_mission/$",
                           teacher_views.edit_mission,
                           name="edit_mission"),

                       url(r"user/teacher/set_mission_score/$",
                           teacher_views.set_mission_score,
                           name="set_mission_score"),

                       url(r"liveroom/update/status/$",
                           teacher_views.update_live_room_status,
                           name="update_live_room_status"),

                       url(r'^domain/auth/failure/$',
                           teacher_views.domain_auth_failure,
                           name='domain_auth_failure'),

                       url(r'^live/play/$',
                           teacher_views.live_play,
                           name='live_play'),

                       url(r"user/teacher/remark/$",
                           teacher_views.teacher_save_remark,
                           name="teacher_save_remark"),

                       url(r"user/review/answers/$",
                           views.get_review_answer,
                           name="get_review_answer"),

                       )

