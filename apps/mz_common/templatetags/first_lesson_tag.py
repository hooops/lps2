# -*- coding: utf-8 -*-
__author__ = 'admin'

from django import template
from django.template import Context, Template, loader, resolve_variable
import string
from  datetime import *
import  time
from mz_course.views import *

register=template.Library()

@register.tag(name='first_lesson')
def first_lesson(parser,token):
    try:
        tag_name,course_id=token.split_contents()
    except :
        raise template.TemplateSyntaxError(" tag  error!")
    return find_first_lesson(course_id)

class find_first_lesson(template.Node):
    def __init__(self,course_id):
        self.course_id=template.Variable(course_id)
    def render(self, context):
        courseid = self.course_id.resolve(context)
        lesson_list = Lesson.objects.filter(course=courseid).order_by("index")
        if len(lesson_list) > 0:
            return str(lesson_list[0].id)
        else:
        	return '0'

