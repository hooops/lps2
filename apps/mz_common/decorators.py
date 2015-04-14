# -*- coding: utf-8 -*-
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

# 定义只能学生分组才能访问的修饰符
def student_required(func):
    def is_student(request):
        if not request.user.is_authenticated() or not request.user.is_student():
            return HttpResponseRedirect(reverse('index_front'))
        return func(request)
    return is_student

# 定义只能老师分组才能访问的修饰符
def teacher_required(func):
    def is_teacher(request, **kwargs):
        if not request.user.is_authenticated() or not request.user.is_teacher():
            return HttpResponseRedirect(reverse('index_front'))
        return func(request, **kwargs)
    return is_teacher

# 定义只能超级管理员才能访问的修饰符
def superuser_required(func):
    def is_superuser(request, **kwargs):
        if not request.user.is_authenticated() or (not request.user.is_superuser and not request.user.is_staff):
            return HttpResponseRedirect(reverse('backend:admin_login'))
        return func(request, **kwargs)
    return is_superuser


