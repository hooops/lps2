#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import math
import uuid
import os
import re
import logging
from functools import wraps, partial

from django.views.decorators.csrf import csrf_exempt
from django import template
from django.conf import settings
from django.core.context_processors import csrf
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotAllowed
from django.template import loader, RequestContext, Library
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction

from utils.tool import upload_generation_dir

from mz_user.models import UserProfile
from mz_lps.models import Paper, Quiz, Project, Examine, Homework
from mz_course.models import CareerCourse, Stage, Course, Lesson, LessonResource, Discuss
from mz_common.models import Keywords, MyMessage

from .forms import (CareerCourseForm, StageEditForm, CourseForm, QuizForm,
                    ProjectForm, LessonForm, ExamineForm, LessonResourceForm)

from .helper import intval, floatval, page_items, get_or_none, authenticated, Route
from base_views import (BaseView, course_info_handle, lesson_info_handle, CareerCoursesBaseView, _handle_item_list,
                        lesson_resource_handle, lesson_online_exam_handle, handle_resource_upload,
                        lesson_homework_handle, lesson_paper_quiz_handle, handler_keywords, career_course_info_handle)

from .models import LESSON_PAPER, COURSE_PAPER, LESSON_HOMEWORK, LESSON_ONLINE_EXAM, COURSE_PROJECT


logger = logging.getLogger('mz_nadmin.views')
route = Route.route


@route(url_regex="^$", name="home_page")
@authenticated
@require_GET
@BaseView
def home_page(request, **kwargs):
    """首页"""

    extra_info = kwargs["extra_info"]

    return render(request, "mz_nadmin/home.html",
                  {"extra_info": extra_info})


@route(url_regex="^career_courses$", name="career_courses")
@authenticated
@require_GET
@BaseView
def career_courses(request, **kwargs):
    """职业课程"""

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)

    career_courses_qs = CareerCourse.objects.all().order_by("-id")
    career_courses = page_items(career_courses_qs, page_num)

    return render(request, "mz_nadmin/career_courses.html",

                  {"is_career_courses": True,
                   "career_courses": career_courses,

                   "messages": msgs,
                   "extra_info": extra_info})


@route(url_regex="^career_courses/create$", name="career_courses_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def career_courses_create(request, **kwargs):
    """职业课程 新建"""

    _render = partial(render, request, "mz_nadmin/career_courses_edit.html")

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    msgs = messages.get_messages(request)

    _ctx_dict = {"tabs_active": "info",
                 "is_career_courses_create": True,

                 "messages": msgs,
                 "extra_info": extra_info}

    if request.method == "GET":
        form = CareerCourseForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = CareerCourseForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return career_course_info_handle(form, _render, request=request, _ctx_dict=_ctx_dict)


@route(url_regex=r"^career_course/(\d+)$", name="career_courses_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def career_courses_edit(request, career_course_id, **kwargs):
    """职业课程 编辑"""

    _render = partial(render, request, "mz_nadmin/career_courses_edit.html")
    msgs = messages.get_messages(request)

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    kws = [kw.name for kw in career_course.search_keywords.all()]

    _ctx_dict = {"tabs_active": "info",
                 "is_career_courses_edit": True,

                 "messages": msgs,
                 "career_course": career_course,
                 "extra_info": extra_info}

    if request.method == "GET":
        form = CareerCourseForm(initial={"name": career_course.name,
                                         "short_name": career_course.short_name,
                                         "search_keywords": ",".join(kws),
                                         "description": career_course.description,
                                         "market_page_url": career_course.market_page_url})

        return _render(dict(_ctx_dict, form=form))

    else:
        form = CareerCourseForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return career_course_info_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                         kws=kws, career_course=career_course)


@route(url_regex="^career_courses/(\d+)/stages$", name="stages")
@authenticated
@require_GET
@BaseView
def stages(request, career_course_id, **kwargs):
    """职业课程 编辑 阶段列表"""

    # 同一个阶段只能属于一个 职业课程 view 没有必要添加
    # 前缀 但是 url 中还是需要带上 career_course_id
    # 虽然修改的时候已经可以根据 stage_id 获取 carrer_course_id

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    stages_qs = Stage.objects.filter(career_course=career_course).order_by("-index")
    stages = page_items(stages_qs, page_num)

    return render(request, "mz_nadmin/stages.html",

                   {"tabs_active": "stages",
                    "is_career_courses_edit": True,

                   "extra_info": extra_info,
                   "career_course": career_course,
                   "messages": msgs,
                   "stages": stages})


@route(url_regex="^career_courses/(\d+)/pay$", name="career_courses_edit_pay")
@authenticated
@require_GET
@BaseView
def career_courses_edit_pay(request, career_course_id, **kwargs):
    """职业课程 编辑 查看支付信息"""

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    msgs = messages.get_messages(request)

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    # 折扣百分比
    career_course_discount_pre = career_course.discount * 100

    # 直接取出所有的 stage
    stages_qs = Stage.objects.filter(career_course=career_course).order_by("id")

    # 全款价格 = 各阶段价格总和 X 全款折扣
    stage_price_sum = 0
    for stage in stages_qs:
        stage_price_sum += stage.price

    stage_price_sum = stage_price_sum * career_course.discount

    return render(request, "mz_nadmin/career_courses_edit_pay.html",

                   {"tabs_active": "pay",
                    "is_career_courses_edit": True,

                   "messages": msgs,
                   "extra_info": extra_info,
                   "career_course": career_course,
                   "stages": stages_qs,
                   "career_course_discount_pre": career_course_discount_pre,
                   "stage_price_sum": stage_price_sum})


@route(url_regex="^career_courses/(\d+)/pay/edit$", name="career_courses_edit_pay_edit")
@authenticated
@require_POST
def career_courses_edit_pay(request, career_course_id, **kwargs):
    """职业课程 编辑 支付模块 修改支付信息"""

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    # 取出所有的 stage 比较价格是不是发生了变化
    stages_qs = Stage.objects.filter(career_course=career_course).order_by("-index")

    try:
        for stage in stages_qs:
            price_key = "stage_%s_price" % stage.id
            istry_key = "stage_%s_istry" % stage.id

            user_input_price = intval(request.POST.get(price_key, ""))
            user_input_istry = request.POST.get(istry_key, "")

            user_input_istry = True if user_input_istry == "on" else False

            stage.price = user_input_price
            stage.is_try = user_input_istry

            stage.save()

        # 处理 career_course 部分
        discount = floatval(request.POST.get("discount", ""))

        if discount < 0 or discount > 100 or math.ceil(discount) > discount:
            messages.error(request, u"全款折扣应该是 0 到 100 之间的正整数")
            return redirect(reverse("nadmin:career_courses_edit_pay", args=[career_course.id]))

        career_course.discount = discount / 100
        career_course.save()

        messages.success(request, u"保存成功")

    except Exception as e:
        logger.error(e)
        messages.error(request, u"更新失败，请稍后再试")

    finally:
        return redirect(reverse("nadmin:career_courses_edit_pay", args=[career_course.id]))


@route(url_regex="^career_courses/(\d+)/stages/create$", name="stages_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def stages_create(request, career_course_id, **kwargs):
    """新建阶段"""

    _render = partial(render, request, "mz_nadmin/stage_edit.html")
    msgs = messages.get_messages(request)

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    _ctx_dict = {"tabs_active": "info",
                 "is_stage_create": True,

                 "messages": msgs,
                 "extra_info": extra_info,

                 "career_course": career_course}

    if request.method == "GET":
        form = StageEditForm()
        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = StageEditForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        stage = Stage()
        stage.name = cleaned_data["name"]
        stage.description = cleaned_data["description"]
        stage.price = cleaned_data["price"]
        stage.career_course = career_course

        try:
            stage.save()

            messages.success(request, u"新建阶段成功")
            return redirect(reverse("nadmin:stages_edit", args=[career_course_id, stage.id]))

        except Exception as e:
            logger.error(e)
            messages.error(request, u"新建失败，请稍后再试")
            return _render(dict(_ctx_dict, form=form))


@route(url_regex=r"^career_courses/(\d+)/stages/(\d+)$", name="stages_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def stage_edit(request, career_course_id, stage_id, **kwargs):
    """阶段修改 基本信息"""

    _render = partial(render, request, "mz_nadmin/stage_edit.html")
    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    msgs = messages.get_messages(request)

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    stage_id = intval(stage_id)
    stage = get_object_or_404(Stage, id=stage_id)

    _ctx_dict = {"tabs_active": "info",
                 "is_stage_edit": True,

                 "messages": msgs,
                 "extra_info": extra_info,
                 "career_course": career_course,
                 "stage": stage}

    if request.method == "GET":
        form = StageEditForm(initial={"name": stage.name,
                                      "price": stage.price,
                                      "description": stage.description})

        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = StageEditForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        stage.name = cleaned_data["name"]
        stage.description = cleaned_data["description"]
        stage.price = cleaned_data["price"]

        try:
            stage.save()
            messages.success(request, u"修改阶段成功")

            return redirect(reverse("nadmin:stage_edit", args=[career_course_id, stage.id]))

        except Exception as e:
            logger.error(e)
            messages.error(request, u"修改失败，请稍后再试")
            return _render(dict(_ctx_dict, form=form))


@route(url_regex=r"^stages/(\d+)/courses$", name="stages_courses")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def stage_edit_courses(request, stage_id, **kwargs):
    """阶段编辑 课程列表"""

    page_num = intval(request.GET.get("page_num", 1))
    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "career_courses"

    msgs = messages.get_messages(request)

    stage_id = intval(stage_id)
    stage = get_object_or_404(Stage, id=stage_id)

    career_course_id = intval(stage.career_course.id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    courses_qs = Course.objects.filter(stages=stage).order_by("-id")
    courses = page_items(courses_qs, page_num)

    return render(request,
                  "mz_nadmin/stage_edit_courses.html",

                  {"is_stage_edit": True,
                   "tabs_active": "courses",

                   "career_course": career_course,
                   "stage": stage,
                   "extra_info": extra_info,
                   "courses": courses,
                   "messages": msgs})


@route(url_regex="^courses$", name="courses")
@authenticated
@require_GET
@BaseView
def courses(request, **kwargs):
    """零散课程"""

    _render = partial(render, request, "mz_nadmin/individual_courses.html")

    extra_info = kwargs["extra_info"]
    extra_info["current_nav_name"] = "individual_courses"

    msgs = messages.get_messages(request)
    page_num = intval(request.GET.get("page_num", 1))

    courses_qs = Course.objects.filter(stages=None).order_by("-id")
    courses = page_items(courses_qs, page_num)

    _ctx_dict = {"is_courses": True,

                 "courses": courses,
                 "messages": msgs,
                 "extra_info": extra_info}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/create$", name="courses_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def courses_create(request, **kwargs):
    """新建课程(或零散课程)"""

    _render = partial(render, request, "mz_nadmin/course_edit.html")

    extra_info = kwargs["extra_info"]
    msgs = messages.get_messages(request)

    # 通过传入的 stage_id 是否合法 来判断是不是零散课程
    stage_id = intval(request.GET.get("stage_id", ""))
    stage = get_or_none(Stage, id=stage_id)

    teachers = UserProfile.objects.filter(groups__name=u"老师")

    if stage != None:
        # 关联课程
        career_course_id = intval(stage.career_course.id)
        career_course = get_object_or_404(CareerCourse, id=career_course_id)
        extra_info["current_nav_name"] = "career_courses"

    else:
        # 零散课程
        career_course = None
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "info",
                 "is_courses_create": True,

                 "extra_info": extra_info,
                 "messages": msgs,
                 "teachers": teachers,

                 # 如果是 零散课程 则以下两个值都是 None
                 "career_course": career_course,
                 "stage": stage}

    if request.method == "GET":
        form = CourseForm()
        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = CourseForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return course_info_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                  stage=stage)


@route(url_regex=r"^courses/(\d+)$", name="courses_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def courses_edit(request, course_id, **kwargs):
    """课程修改"""

    _render = partial(render, request, "mz_nadmin/course_edit.html")
    extra_info = kwargs["extra_info"]
    msgs = messages.get_messages(request)

    stage_id = intval(request.GET.get("stage_id", ""))
    stage = get_or_none(Stage, id=stage_id)

    if stage != None:
        career_course_id = intval(stage.career_course.id)
        career_course = get_object_or_404(CareerCourse, id=career_course_id)

    else:
        career_course = None

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    kws = [kw.name for kw in course.search_keywords.all()]

    # 获取所有老师的列表
    teachers = UserProfile.objects.filter(groups__name=u"老师")

    _ctx_dict = {"tabs_active": "info",
                 "is_courses_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,
                 "teachers": teachers,

                 "career_course": career_course,
                 "stage": stage,
                 "course": course}

    if request.method == "GET":
        form = CourseForm(initial={"name": course.name,
                                   "description": course.description,
                                   "search_keywords": ",".join(kws),
                                   "teacher": course.teacher})

        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = CourseForm(request.POST)

        if not form.is_valid():
            return  _render(dict(_ctx_dict, form=form))

        return course_info_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                  course=course)


@route(url_regex=r"^courses/(\d+)/lessons$", name="courses_edit_lessons")
@authenticated
@require_GET
@BaseView
def course_edit_lessons(request, course_id, **kwargs):
    """课程修改 章节管理"""

    _render = partial(render, request, "mz_nadmin/course_edit_lessons.html")
    msgs = messages.get_messages(request)
    page_num = page_num = intval(request.GET.get("page_num", 1))

    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    lessons_qs = Lesson.objects.filter(course=course)
    lessons = page_items(lessons_qs, page_num)

    _ctx_dict = {"tabs_active": "lessons",
                 "is_courses_edit": True,

                 "messages": msgs,
                 "extra_info": extra_info,

                 "course": course,
                 "lessons": lessons}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/(\d+)/lessons/create$", name="lessons_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_create(request, course_id, **kwargs):
    """课程编辑 创建章节"""

    _render = partial(render, request, "mz_nadmin/lessons_edit.html")

    extra_info = kwargs["extra_info"]
    msgs = messages.get_messages(request)

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "info",
                 "is_lessons_create": True,

                 "extra_info": extra_info,
                 "messages": msgs,
                 "course": course}

    if request.method == "GET":
        form = LessonForm()
        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = LessonForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_info_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                  course=course)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)$", name="lessons_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_edit(request, course_id, lesson_id, **kwargs):
    """课程修改 章节编辑"""

    _render = partial(render, request, "mz_nadmin/lessons_edit.html")
    extra_info = kwargs["extra_info"]
    msgs = messages.get_messages(request)

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "info",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson}

    if request.method == "GET":
        form = LessonForm(initial={"name": lesson.name,
                                   "video_url": lesson.video_url,
                                   "video_length": lesson.video_length,
                                   "index": lesson.index})

        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = LessonForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_info_handle(form, request, _render, _ctx_dict=_ctx_dict,
                                  lesson=lesson)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/resoures$", name="lessons_edit_resources")
@authenticated
@require_GET
@BaseView
def lessons_edit_resources(request, course_id, lesson_id, **kwargs):
    """章节编辑 课件及源码"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_resources.html")

    extra_info = kwargs["extra_info"]
    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    resources_qs = LessonResource.objects.filter(lesson=lesson).order_by("-id")
    resources = page_items(resources_qs, page_num)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "resources",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "resources": resources}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/resources/create$", name="lessons_resources_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_resources_create(request, course_id, lesson_id, **kwargs):
    """章节编辑 添加新的资源"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_resources_edit.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "resources",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson}

    if request.method == "GET":
        form = LessonResourceForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = LessonResourceForm(request.POST, request.FILES)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_resource_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                      lesson=lesson)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/resources/(\d+)$", name="lessons_resources_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_resources_edit(request, course_id, lesson_id, resource_id, **kwargs):
    """章节编辑 编辑资源"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_resources_edit.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    resource_id = intval(resource_id)
    resource = get_object_or_404(LessonResource, id=resource_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "resources",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "resource": resource,
                 "lesson": lesson}

    if request.method == "GET":
        form = LessonResourceForm(initial={"name": resource.name,
                                           "download_url": resource.download_url})

        return _render(dict(_ctx_dict, form=form))

    else:
        # @XXX 文件修改
        form = LessonResourceForm(request.POST, request.FILES)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_resource_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                      lesson_resource=resource)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/online_exam$", name="lessons_edit_online_exam")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_edit_online_exam(request, course_id, lesson_id, **kwargs):
    """章节编辑 在线练习"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_online_exam.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    examine = get_or_none(Examine,
                          **dict(LESSON_ONLINE_EXAM, relation_id=lesson.id))

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "online_exam",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "examine": examine}

    if request.method == "GET":
        if examine == None:
            form = ExamineForm()

        else:
            form = ExamineForm(initial={"description": examine.description,
                                        "is_active": examine.is_active})

        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":
        form = ExamineForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_online_exam_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                         lesson=lesson, examine=examine)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/homework$", name="lessons_edit_homework")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lessons_homework(request, course_id, lesson_id, **kwargs):
    """章节编辑 随堂作业"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_homework.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    lesson_homework = get_or_none(Homework,
                                  **dict(LESSON_HOMEWORK, relation_id=lesson.id))

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "homework",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "lesson_homework": lesson_homework}

    if request.method == "GET":
        if lesson_homework == None:
            form = ExamineForm()

        else:
            form = ExamineForm(initial={"is_active": lesson_homework.is_active,
                                        "description": lesson_homework.description})

        return _render(dict(_ctx_dict, form=form))

    else:
        form = ExamineForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_homework_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                      lesson=lesson, lesson_homework=lesson_homework)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/paper$", name="lessons_edit_paper")
@authenticated
@require_GET
@BaseView
def lessons_paper(request, course_id, lesson_id, **kwargs):
    """章节编辑 随堂测验"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_paper.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    lesson_paper = get_or_none(Paper, **dict(LESSON_PAPER,
                                             relation_id=lesson.id))

    if lesson_paper:
        quizs_qs = Quiz.objects.filter(paper=lesson_paper).order_by("-id")
        quizs = page_items(quizs_qs, page_num)

    else:
        quizs = []

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "paper",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "lesson_paper": lesson_paper,
                 "quizs": quizs}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/paper/(\d+)/quiz/(\d+)$",
       name="lessons_edit_paper_quiz_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lesson_edit_paper_quiz_edit(request, course_id, lesson_id, paper_id, quiz_id, **kwargs):
    """修改已经存在的 随堂测试试题"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_paper_quiz_edit.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    quiz_id = intval(quiz_id)
    quiz = get_object_or_404(Quiz, id=quiz_id)

    lesson_paper = get_object_or_404(Paper,
                                     **dict(LESSON_PAPER, relation_id=lesson.id))

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "paper",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "paper_id": paper_id,
                 "lesson_paper": lesson_paper,
                 "quiz": quiz}

    quiz_id = intval(quiz_id)
    quiz = get_object_or_404(Quiz, id=quiz_id)

    if request.method == "GET":
        item_list = quiz.item_list
        items = item_list.split("\r\n")
        item_infos = map(lambda html : re.match("^<(.*)>(.*)<\/button>$", html).group(2), items)

        form = QuizForm(initial={"index": quiz.index,
                                 "question": quiz.question,
                                 "item_1": item_infos[0],
                                 "item_2": item_infos[1],
                                 "item_3": item_infos[2],
                                 "item_4": item_infos[3],
                                 "result": quiz.result})

        return _render(dict(_ctx_dict, form=form))

    elif request.method == "POST":

        form = QuizForm(request.POST)

        if not form.is_valid():
            return  _render(dict(_ctx_dict, form=form))

        return lesson_paper_quiz_handle(form, _render, request, _ctx_dict=_ctx_dict,
                                        lesson=lesson, quiz=quiz)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/paper/(\d+|create)/quiz/create$",
       name="lessons_edit_paper_quiz_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def lesson_edit_paper_quiz_create(request, course_id, lesson_id, paper_id, **kwargs):
    """创建新的随堂测试试题"""

    _render = partial(render, request, "mz_nadmin/lessons_edit_paper_quiz_edit.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "paper",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "paper_id": paper_id}

    if request.method == "GET":
        form = QuizForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = QuizForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        return lesson_paper_quiz_handle(form, _render, request=request, _ctx_dict=_ctx_dict,
                                        lesson=lesson, paper_id=paper_id)


@route(url_regex=r"^courses/(\d+)/lessons/(\d+)/discusses$", name="lessons_edit_discusses")
@authenticated
@require_GET
@BaseView
def lesson_edit_discusses(request, course_id, lesson_id, **kwargs):
    """章节编辑 用户评论"""

    _render = partial(render, request, "mz_nadmin/lesson_edit_discusses.html")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    lesson_id = intval(lesson_id)
    lesson = get_object_or_404(Lesson, id=lesson_id)

    discusses_qs = Discuss.objects.filter(lesson=lesson).order_by("-date_publish")
    discusses = page_items(discusses_qs, page_items)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "discusses",
                 "is_lessons_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "lesson": lesson,
                 "discusses": discusses}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/(\d+)/paper$", name="courses_edit_paper")
@authenticated
@require_GET
@BaseView
def course_edit_course_paper(request, course_id, **kwargs):
    """课程总测验"""

    _render = partial(render, request, "mz_nadmin/courses_edit_paper.html")

    page_num = page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    course_paper = get_or_none(Paper, examine_type=2, relation_type=2, relation_id=course.id)

    if course_paper:
        quizs_qs = Quiz.objects.filter(paper=course_paper)
        quizs = page_items(quizs_qs, page_num)

    else:
        quizs = []

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "paper",
                 "is_courses_edit": True,

                 "messages": msgs,
                 "extra_info": extra_info,
                 "course": course,
                 "course_paper": course_paper,
                 "quizs": quizs,
                 "quizs_with_index": enumerate(quizs, start=1)}

    return _render(_ctx_dict)


@route(url_regex=r"^courses/(\d+)/paper/(\d+)/quiz/(\d+)$", name="courses_edit_paper_quiz")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def course_edit_course_paper_quiz(request, course_id, paper_id, quiz_id, **kwargs):
    """课程总测验 试题编辑"""

    _render = partial(render, request, "mz_nadmin/courses_edit_course_paper_quiz.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    course_paper = get_object_or_404(Paper, examine_type=2, relation_type=2, relation_id=course.id)

    quiz_id = intval(quiz_id)
    quiz = get_object_or_404(Quiz, id=quiz_id)

    _ctx_dict = {"tabs_active": "paper",
                 "is_courses_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "course_paper": course_paper,
                 "quiz": quiz}

    if request.method == "GET":
        # 处理答案选项信息 由于顺序是固定的 因此直接使用 正则匹配 <button> 内容
        item_list = quiz.item_list
        items = item_list.split("\r\n")
        # @XXX 去除空值
        item_infos = map(lambda html : re.match("^<(.*)>(.*)<\/button>$", html).group(2), items)

        # 保证 4 个选项都要设置
        # item_len_dalta = 4 - len(item_infos)

        form = QuizForm(initial={"index": quiz.index,
                                 "question": quiz.question,
                                 "item_1": item_infos[0],
                                 "item_2": item_infos[1],
                                 "item_3": item_infos[2],
                                 "item_4": item_infos[3],
                                 "result": quiz.result})

        return _render(dict(_ctx_dict, form=form))

    else:

        form = QuizForm(request.POST)

        if not form.is_valid():
            return  _render(dict(_ctx_dict, form=form))

        # 生成 item_list
        cleaned_data = form.cleaned_data

        #for key in cleaned_data.keys():
        #    if key.startswith("item_"):
        #        pass

        item_list = _handle_item_list(cleaned_data)

        quiz.index = cleaned_data["index"]
        quiz.result = cleaned_data["result"]
        quiz.question = cleaned_data["question"]
        quiz.item_list = item_list
        quiz.save()

        messages.success(request, u"修改题成功")
        return redirect("nadmin:course_edit_course_paper", career_course.id, stage.id, course.id)


@route(url_regex=r"^courses/(\d+)/paper/(\d+|create)/quiz/create$", name="courses_edit_paper_quiz_create")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def course_edit_course_paper_quiz_create(request, course_id, paper_id, **kwargs):
    """课程总测验 新建试题
    如果 paper_id = create 则需要新建 course_paper"""

    _render = partial(render, request, "mz_nadmin/courses_edit_course_paper_quiz.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    if paper_id == "create":
        # 新建 course_paper
        course_paper = Paper(examine_type=2, relation_type=2, relation_id=course.id)
        course_paper.save()

    else:
        course_paper = get_object_or_404(Paper, examine_type=2, relation_type=2, relation_id=course.id)

    _ctx_dict = {"tabs_active": "paper",
                 "is_courses_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "course_paper": course_paper}

    if request.method == "GET":
        form = QuizForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = QuizForm(request.POST)

        if not form.is_valid():
            return  _render(dict(_ctx_dict, form=form))

        # 生成 item_list
        cleaned_data = form.cleaned_data

        item_list = _handle_item_list(cleaned_data)

        quzi = Quiz()
        quzi.index = cleaned_data["index"]
        quzi.result = cleaned_data["result"]
        quzi.question = cleaned_data["question"]
        quzi.item_list = item_list
        quzi.paper = course_paper

        quzi.save()

        messages.success(request, u"创建试题成功")
        return redirect("nadmin:courses_edit_paper", course.id)


@route(url_regex=r"^courses/(\d+)/project$", name="courses_edit_project")
@authenticated
@require_http_methods(["GET", "POST"])
@BaseView
def courses_edit_project(request, course_id, **kwargs):
    """课程项目制作"""

    _render = partial(render, request, "mz_nadmin/courses_edit_project.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    course_id = intval(course_id)
    course = get_object_or_404(Course, id=course_id)

    course_project = get_or_none(Project, examine_type=5, relation_type=2, relation_id=course.id)

    if course.stages:
        extra_info["current_nav_name"] = "career_courses"
    else:
        extra_info["current_nav_name"] = "individual_courses"

    _ctx_dict = {"tabs_active": "project",
                 "is_courses_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,

                 "course": course,
                 "course_project": course_project}

    if request.method == "GET":

        if course_project:
            form = ProjectForm(initial={"description": course_project.description,
                                        "is_active": course_project.is_active})

        else:
            form = ProjectForm()

        return _render(dict(_ctx_dict, form=form))

    else:
        form = ProjectForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        if course_project == None:
            course_project = Project(**dict(COURSE_PROJECT, relation_id=course.id))

        course_project.is_active = cleaned_data["is_active"]
        course_project.description = cleaned_data["description"]
        course_project.save()

        messages.success(request, u"保存成功")
        return redirect("nadmin:courses_edit_project", course.id)


# xhr


@route(url_regex=r"^lessons/resources/delete$", name="lessons_resources_delete")
@csrf_exempt
@authenticated
@require_POST
def lesson_resources_delete(request):
    """删除章节资源"""

    _response_json = partial(HttpResponse, content_type="text/json")

    resource_id = intval(request.POST.get("resource_id", ""))
    resource = get_or_none(LessonResource, id=resource_id)

    if resource == None:
        HttpResponse.status_code = 404
        msg = {"msg": "fail", "error": u"指定的资源不存在"}
        return _response_json(json.dumps(msg))

    try:
        # @TODO 删除相应文件
        resource.delete()
        return _response_json(json.dumps({"msg": "ok"}))

    except Exception as e:
        logger.error(e)
        HttpResponse.status_code = 500
        msg = {"msg": "fail"}
        return HttpResponse(json.dumps(msg))


@route(url_regex=r"^paper/quiz/delete$", name="paper_quiz_delete")
@csrf_exempt
@authenticated
@require_POST
def paper_quiz_delete(request):

    _response_json = partial(HttpResponse, content_type="text/json")

    quiz_id = intval(request.POST.get("quiz_id", ""))
    quiz = get_or_none(Quiz, id=quiz_id)

    if quiz == None:
        HttpResponse.status_code = 404
        msg = {"msg": "fail", "error": u"指定的资源不存在"}
        return _response_json(json.dumps(msg))

    try:
        # @TODO 删除相应文件
        quiz.delete()
        HttpResponse.status_code = 200
        return _response_json(json.dumps({"msg": "ok"}))

    except Exception as e:
        logger.error(e)
        HttpResponse.status_code = 500
        msg = {"msg": "fail"}
        return HttpResponse(json.dumps(msg))


@route(url_regex=r"^paper/toggle_active$", name="paper_toggle_active")
@csrf_exempt
@authenticated
@require_POST
def paper_toggle_active(request):

    _response_json = partial(HttpResponse, content_type="text/json")

    is_active = request.POST.get("is_active", "false")
    paper_id = intval(request.POST.get("paper_id", ""))

    paper = get_or_none(Paper, id=paper_id)

    if paper == None:
        HttpResponse.status_code = 404
        msg = {"msg": "fail", "error": u"指定的资源不存在"}
        return _response_json(json.dumps(msg))

    try:
        HttpResponse.status_code = 200
        paper.is_active = True if is_active == "true" else False
        paper.save()

        return _response_json(json.dumps({"msg": "ok"}))

    except Exception as e:
        logger.error(e)
        HttpResponse.status_code = 500
        msg = {"msg": "fail"}
        return HttpResponse(json.dumps(msg))


@route(url_regex=r"^lessons/discusses/delete$", name="lessons_discusses_delete")
@csrf_exempt
@authenticated
@require_POST
def lesson_discusses_delete(request):
    _response_json = partial(HttpResponse, content_type="text/json")

    discuss_id = intval(request.POST.get("discuss_id", ""))
    discuss = get_or_none(Discuss, id=discuss_id)

    if discuss == None:
        HttpResponse.status_code = 404
        msg = {"msg": "fail", "error": u"指定的资源不存在"}
        return _response_json(json.dumps(msg))

    try:
        HttpResponse.status_code = 200
        discuss.delete()
        return _response_json(json.dumps({"msg": "ok"}))

    except Exception as e:
        logger.error(e)
        HttpResponse.status_code = 500
        msg = {"msg": "fail"}
        return HttpResponse(json.dumps(msg))


@route(url_regex=r"^messages/delete$", name="messages_delete")
@csrf_exempt
@authenticated
@require_POST
def messages_delete(request):
    _response_json = partial(HttpResponse, content_type="text/json")

    message_id = intval(request.POST.get("message_id", ""))
    message = get_or_none(MyMessage, id=message_id)

    if message == None:
        HttpResponse.status_code = 404
        msg = {"msg": "fail", "error": u"指定的资源不存在"}
        return _response_json(json.dumps(msg))

    try:
        HttpResponse.status_code = 200
        message.delete()
        return _response_json(json.dumps({"msg": "ok"}))

    except Exception as e:
        logger.error(e)
        HttpResponse.status_code = 500
        msg = {"msg": "fail"}
        return HttpResponse(json.dumps(msg))


