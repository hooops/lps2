#!/usr/bin/env python
# -*- coding: utf-8 -*-


from django.conf.urls import patterns, url
from mz_nadmin import course_views, student_views, auth_views, teacher_views

from helper import Route

urlpatterns = Route.urls()


