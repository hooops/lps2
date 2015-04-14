# -*- coding: utf-8 -*-
import xadmin
from models import *

class StageInline(object):
    model = Stage
    extra = 1
    style = 'accordion'

class LessonResourceInline(object):
    model = LessonResource
    extra = 1
    style = 'accordion'

class LessonInline(object):
    model = Lesson
    extra = 1
    style = 'accordion'
    inlines = [LessonResourceInline]

class CareerCourseAdmin(object):
    list_display = ('name', 'description','click_count','id')
    search_fields = ['name','id']
    inlines = [StageInline]

class StageAdmin(object):
    list_display = ('name', 'description','id')
    search_fields = ['name','id']

class CourseAdmin(object):
    list_display = ('name','date_publish','need_days','teacher','click_count','id')
    search_fields = ['name','id']
    inlines = [LessonInline]

class LessonAdmin(object):
    inlines = [LessonResourceInline]
    list_display = ('name','video_length','play_count','id')
    search_fields = ['name','id']

class LessonResourceAdmin(object):
    list_display = ('name','download_url','download_count','id')

class DiscussAdmin(object):
    list_display = ('content','id')
    search_fields = ['content']

xadmin.site.register(CareerCourse, CareerCourseAdmin)
xadmin.site.register(Stage, StageAdmin)
xadmin.site.register(Course, CourseAdmin)
xadmin.site.register(Lesson, LessonAdmin)
xadmin.site.register(LessonResource, LessonResourceAdmin)
xadmin.site.register(Discuss, DiscussAdmin)