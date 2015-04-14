#s!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
import os
import re
import logging
import json
from functools import wraps, partial

from django import template
from django.conf import settings
from django.core.context_processors import csrf
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.template import loader, RequestContext, Library
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.contrib.auth.models import Group

from mz_common.models import MyMessage
from mz_user.models import UserProfile, ProvinceDict, CityDict
from mz_lps.models import Paper, Quiz, Project, Examine, Homework, Class
from mz_course.models import CareerCourse, Stage, Course, Lesson, LessonResource, Discuss
from mz_common.models import Keywords

from .forms import (StageEditForm, CourseForm, QuizForm, TeacherForm,
                    ProjectForm, LessonForm, ExamineForm, LessonResourceForm)

from .helper import intval, floatval, page_items, get_or_none, authenticated, Route
from base_views import TeachersBaseView


from .models import LESSON_PAPER, COURSE_PAPER, LESSON_HOMEWORK, LESSON_ONLINE_EXAM, COURSE_PROJECT


logger = logging.getLogger('mz_nadmin.views')
route = Route.route


@route(url_regex=r"^teachers$", name="users_teachers")
@authenticated
@require_GET
@TeachersBaseView
def teachers(request, **kwargs):
    """获取教师列表"""

    q = request.GET.get("q", "")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teachers_qs = UserProfile.objects.filter(groups__name=u"老师").order_by("-id")

    if q != "":
        teachers_qs = teachers_qs.filter(username__contains=q)

    teachers = page_items(teachers_qs, page_num)

    return render(request,
                  "mz_nadmin/teachers.html",

                  {"is_teachers": True,

                   "teachers": teachers,
                   "messages": msgs,
                   "q": q,
                   "extra_info": extra_info})


@route(url_regex=r"^teachers/(\d+)$", name="teachers_info")
@authenticated
@require_http_methods(["GET", "POST"])
@TeachersBaseView
def teachers_info(request, teacher_id, **kwargs):
    """教师信息"""

    _render = partial(render, request, "mz_nadmin/teachers_info.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teacher_id = intval(teacher_id)
    teacher = get_object_or_404(UserProfile, id=teacher_id)

    provinces = ProvinceDict.objects.all()

    _ctx_dict = {"is_teachers_edit": True,
                 "tabs_active": "info",

                 "teacher": teacher,
                 "provinces": provinces,
                 "messages": msgs,
                 "extra_info": extra_info}

    if request.method == "GET":
        form = TeacherForm(initial={"email": teacher.email,
                                    "username": teacher.username,
                                    "mobile": teacher.mobile,
                                    "date_joined": teacher.date_joined,
                                    "nick_name": teacher.nick_name,
                                    "city": teacher.city,
                                    "qq": teacher.qq})

        return _render(dict(_ctx_dict, form=form))

    else:
        form = TeacherForm(request.POST, instance=teacher)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        teacher.email=cleaned_data["email"]
        teacher.username=cleaned_data["username"]
        teacher.mobile=cleaned_data["mobile"]
        teacher.nick_name=cleaned_data["nick_name"]
        teacher.city=cleaned_data["city"]
        teacher.qq=cleaned_data["qq"]

        try:
            teacher.save()
            messages.success(request, u"修改教师信息成功")

            return redirect(reverse("nadmin:teachers_info", args=[teacher.id]))

        except Exception as e:
            logger.error(e)
            messages.error(request, u"修改教师信息失败，请稍后再试")
            return _render(dict(_ctx_dict, form=form))


@route(url_regex=r"^teachers/create$", name="teachers_create")
@authenticated
@require_http_methods(["GET", "POST"])
@TeachersBaseView
def teacher_create(request, **kwargs):
    """添加新的教师"""

    _render = partial(render, request, "mz_nadmin/teachers_info.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    provinces = ProvinceDict.objects.all()

    _ctx_dict = {"is_teachers_create": True,
                 "tabs_active": "info",

                 "provinces": provinces,
                 "messages": msgs,
                 "extra_info": extra_info}

    if request.method == "GET":
        form = TeacherForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = TeacherForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        try:
            teacher_group = Group.objects.get(name=u"老师")
            teacher = UserProfile(email=cleaned_data["email"],
                                  username=cleaned_data["username"],
                                  mobile=cleaned_data["mobile"],
                                  nick_name=cleaned_data["nick_name"],
                                  city=cleaned_data["city"],
                                  qq=cleaned_data["qq"])

            teacher.save()
            teacher_group.user_set.add(teacher)

            messages.success(request, u"添加教师成功")
            return redirect(reverse("nadmin:users_teachers"))

        except Exception as e:
            logger.error(e)
            messages.error(request, u"添加教师失败，请稍后再试")
            return _render(dict(_ctx_dict, form=form))


@route(url_regex=r"^teachers/(\d+)/classes$", name="teachers_classes")
@authenticated
@require_GET
@TeachersBaseView
def teacher_classes(request, teacher_id, **kwargs):
    """教师信息 班级信息"""

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teacher_id = intval(teacher_id)
    teacher = get_object_or_404(UserProfile, id=teacher_id)

    classes_qs = Class.objects.filter(teacher=teacher.id, status=1)
    classes = page_items(classes_qs, page_num)

    return render(request,
              "mz_nadmin/teachers_classes.html",

              {"is_teachers_edit": True,
               "tabs_active": "classes",

               "teacher": teacher,
               "classes": classes,
               "messages": msgs,
               "extra_info": extra_info})


@route(url_regex=r"^teachers/(\d+)/classes_ended$", name="teachers_classes_ended")
@authenticated
@require_GET
@TeachersBaseView
def teacher_classes_ended(request, teacher_id, **kwargs):
    """教师信息 班级信息 结束班级"""

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teacher_id = intval(teacher_id)
    teacher = get_object_or_404(UserProfile, id=teacher_id)

    classes_qs = Class.objects.filter(teacher__id=teacher.id, status=2)
    classes = page_items(classes_qs, page_num)

    return render(request,
              "mz_nadmin/teachers_classes_ended.html",

              {"is_teachers_edit": True,
               "tabs_active": "classes_ended",

               "teacher": teacher,
               "classes": classes,
               "messages": msgs,
               "extra_info": extra_info})


@route(url_regex=r"^teachers/(\d+)/msgs$", name="teachers_msgs")
@authenticated
@require_GET
@TeachersBaseView
def teacher_msgs(request, teacher_id, **kwargs):
    """教师信息 消息"""

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teacher_id = intval(teacher_id)
    teacher = get_object_or_404(UserProfile, id=teacher_id)

    recive_messages_qs = MyMessage.objects.filter(userB=teacher.id)
    recive_messages = page_items(recive_messages_qs, page_num)

    return render(request,
              "mz_nadmin/teachers_msgs.html",

              {"is_teachers_edit": True,
               "tabs_active": "msgs",

               "teacher": teacher,
               "messages": msgs,
               "recive_messages": recive_messages,
               "extra_info": extra_info})


@route(url_regex=r"^teachers/(\d+)/classes/(\d+)$", name="teachers_classes_info")
@authenticated
@require_GET
@TeachersBaseView
def teacher_class_info(request, teacher_id, class_id, **kwargs):
    """班级信息页面"""

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    teacher_id = intval(teacher_id)
    teacher = get_object_or_404(UserProfile, id=teacher_id)

    class_id = intval(class_id)
    class_ = get_object_or_404(Class, id=class_id)

    students_qs = UserProfile.objects.filter(classstudents__student_class=class_)
    students = page_items(students_qs, page_num)

    return render(request,
              "mz_nadmin/teachers_classes_info.html",

              {"is_classes_info": True,

               "class_": class_,
               "teacher": teacher,
               "messages": msgs,
               "students": students,
               "extra_info": extra_info})


# apis


@route(url_regex=r"get_city_by_province_id", name="get_city_by_province_id")
@require_GET
def get_city_by_province_id(request):

    province_id = intval(request.GET.get("province_id", ""))

    try:
        citys_qs = CityDict.objects.filter(province__id=province_id)
        citys = [{"id": city.id, "name": city.name} for city in citys_qs]

    except Exception as e:
        citys = []
        logger.error(e)

    return HttpResponse(json.dumps(citys), content_type="text/json")


@route(url_regex=r"get_province_id_by_city_id", name="get_province_id_by_city_id")
@require_GET
def get_province_id_by_city_id(request):

    city_id = intval(request.GET.get("city_id", ""))

    try:
        city = get_or_none(CityDict, id=city_id)

        if city != None:
            province_id = city.province.id

        else:
            province_id = -1

    except Exception as e:
        province_id = -1
        logger.error(e)

    return HttpResponse(json.dumps({"province_id": province_id}), content_type="text/json")


