#!/usr/bin/env python
# -*- coding: utf-8 -*-

import uuid
import os
import re
import logging
from functools import wraps, partial

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
from mz_common.models import Keywords

from .forms import (CareerCourseForm, StageEditForm, CourseForm, QuizForm,
                    ProjectForm, LessonForm, ExamineForm, LessonResourceForm)

from .helper import intval, floatval, page_items, get_or_none, authenticated, get_or_create
from .models import LESSON_PAPER, COURSE_PAPER, LESSON_HOMEWORK, LESSON_ONLINE_EXAM, COURSE_PROJECT


logger = logging.getLogger('mz_nadmin.views')



def handler_keywords(item, new_kws, old_kws):
    """将用户修改的 kws 作为单个 kw 保存 并更新 item
    目前 item 只能是 career_course 或 course"""

    if new_kws != ",".join(old_kws):
        try:
            kw = Keywords.objects.get(name=new_kws)

        except Keywords.DoesNotExist as e:
            kw = Keywords(name=new_kws)
            kw.save()

        # 清除之前的值 保存新值
        item.search_keywords.clear()
        item.search_keywords.add(kw)


def handle_resource_upload(files):
    """处理章节资源的上传"""

    # @TODO 放置到 settings 文件中
    RESOURCE_SIZE_LIMIT = 2560
    RESOURCE_SUFFIX_LIMIT = ["zip", "rar", "pdf"]

    try:
        file_suffix = files.name.split(".")[-1].lower()

    except:
        return (False, u"文件必须为 ZIP/RAR/PDF 格式", None)

    if intval(files.size/1024) > RESOURCE_SIZE_LIMIT:
        return (False, u"文件大小超过 %s KB限制" % str(settings.JOB_SIZE_LIMIT), None)

    if not (file_suffix in RESOURCE_SUFFIX_LIMIT):
        return (False, u"文件必须为 ZIP/RAR/PDF 格式", None)

    path = os.path.join(settings.MEDIA_ROOT, upload_generation_dir("lesson"))
    if not os.path.exists(path):
        os.makedirs(path)

    file_name = "%s.%s" % (str(uuid.uuid1()), file_suffix)
    path_file = os.path.join(path, file_name)
    db_file_url = path_file.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    status = open(path_file, 'wb').write(files.file.read())

    return (True, u"文件上传成功", db_file_url)


def career_course_info_handle(form, _render, request=None, _ctx_dict=None,
                              career_course=None, kws=None):

    """处理 form 中的职业课程信息"""

    cleaned_data = form.cleaned_data

    is_edit = False
    if career_course:
        is_edit = True

    # 单个 kw 最多 50 字符
    search_keywords_name = cleaned_data["search_keywords"][:50]

    if is_edit:
        career_course.name=cleaned_data["name"]
        career_course.short_name=cleaned_data["short_name"]
        career_course.description=cleaned_data["description"]
        career_course.market_page_url=cleaned_data["market_page_url"]

    else:
        career_course = CareerCourse(name=cleaned_data["name"],
                                     short_name=cleaned_data["short_name"],
                                     description=cleaned_data["description"],
                                     market_page_url=cleaned_data["market_page_url"])

    if is_edit:
        # kw 被修改
        if cleaned_data["search_keywords"] != ",".join(kws):
            kw = get_or_create(Keywords, name=search_keywords_name)

            # 清空之前的关联 但是不能删除 kw 记录
            career_course.search_keywords.clear()
            career_course.search_keywords.add(kw)

    else:
        # 判断是否已经存在相应的 kw
        kw = get_or_create(Keywords, name=search_keywords_name)

    try:
        career_course.save()

        if is_edit:
            messages.success(request, u"更新成功")

        else:
            career_course.search_keywords.add(kw)
            messages.success(request, u"创建职业课程成功")

        return redirect(reverse("nadmin:career_courses_edit", args=[career_course.id]))

    except Exception as e:
        logger.error(e)
        messages.error(request, u"系统错误，请稍后再试")
        return _render(dict(_ctx_dict, form=form))


def course_info_handle(form, _render, request=None, _ctx_dict=None,
                       stage=None, course=None):

    """课程信息 处理
    新建从属于职业课程的课程时 只传入 stage
    新建零散课程时 传入的 stage=None

    编辑课程时 只传入 course"""

    cleaned_data = form.cleaned_data

    # 判断是否是新建
    if course:
        # edit
        is_edit = True
        is_individual_course = False if course.stages else True

    else:
        # create
        is_edit = False
        is_individual_course = False if stage else True

    # 判断 teacher 信息的有效性
    teacher_id = cleaned_data["teacher"]
    teacher = get_or_none(UserProfile, id=teacher_id)

    if teacher == None or not teacher.is_teacher():
        messages.error(request, u"选择的教师并不具有教师身份")
        return _render(dict(_ctx_dict, form=form))

    # 处理搜索关键字
    try:
        kw = Keywords.objects.get(name=cleaned_data["search_keywords"])

    except Keywords.DoesNotExist as e:
        kw = Keywords(name=cleaned_data["search_keywords"])
        kw.save()

    if is_edit:
        course.teacher = teacher
        course.name = cleaned_data["name"]
        course.description = cleaned_data["description"]

    else:
        # create
        course = Course(name=cleaned_data["name"],
                        teacher=teacher,
                        description=cleaned_data["description"])

        if stage:
            course.stages = stage

    try:
        course.save()
        course.search_keywords.add(kw)

        redirect_url = reverse("nadmin:courses_edit", args=[course.id])
        if not is_individual_course:
            redirect_url = "?".join([redirect_url, "stage_id=%s" % course.stages.id])

        if is_edit:
            messages.success(request, u"修改课程成功")
        else:
            messages.success(request, u"创建课程成功")

        return redirect(redirect_url)

    except Exception as e:
        logger.error(e)
        messages.error(request, u"系统错误，请稍后再试")
        return _render(dict(_ctx_dict, form=form))


def lesson_info_handle(form, _render, request=None, _ctx_dict=None,
                       course=None, lesson=None):

    """处理章节信息"""

    cleaned_data = form.cleaned_data

    is_edit = True
    if not lesson:
        is_edit = False

        lesson = Lesson()
        lesson.course = course

    lesson.name = cleaned_data["name"]
    lesson.video_url = cleaned_data["video_url"]
    lesson.video_length = cleaned_data["video_length"]
    lesson.index = cleaned_data["index"]

    # 根据 lesson.course.stage 是否存在
    is_individual_course = True
    if lesson.course.stages:
        is_individual_course = False

    try:
        lesson.save()

        if is_edit:
            messages.success(request, u"修改章节信息成功")
            return redirect(reverse("nadmin:courses_edit_lessons", args=[course.id]))

        else:
            messages.success(request, u"创建章节信息成功")
            return redirect(reverse("nadmin:lessons_edit", args=[course.id, lesson.id]))

    except Exception as e:
        logger.error(e)
        messages.error(request, u"系统错误，请稍后再试")
        return _render(dict(_ctx_dict, form=form))


def handle_resource_upload(files):
    """处理章节资源的上传"""

    # @TODO 放置到 settings 文件中
    RESOURCE_SIZE_LIMIT = 2560
    RESOURCE_SUFFIX_LIMIT = ["zip", "rar", "pdf"]

    try:
        file_suffix = files.name.split(".")[-1].lower()

    except:
        return (False, u"文件必须为 ZIP/RAR/PDF 格式", None)

    if intval(files.size/1024) > RESOURCE_SIZE_LIMIT:
        return (False, u"文件大小超过 %s KB限制" % str(settings.JOB_SIZE_LIMIT), None)

    if not (file_suffix in RESOURCE_SUFFIX_LIMIT):
        return (False, u"文件必须为 ZIP/RAR/PDF 格式", None)

    path = os.path.join(settings.MEDIA_ROOT, upload_generation_dir("lesson"))
    if not os.path.exists(path):
        os.makedirs(path)

    file_name = "%s.%s" % (str(uuid.uuid1()), file_suffix)
    path_file = os.path.join(path, file_name)
    db_file_url = path_file.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    status = open(path_file, 'wb').write(files.file.read())

    return (True, u"文件上传成功", db_file_url)


def lesson_resource_handle(form, _render, request=None, _ctx_dict=None,
                           lesson=None, lesson_resource=None):

    """章节资源的处理
    新建的时候 需要传入 lesson
    """

    if lesson_resource:
        is_edit = True

    else:
        is_edit = False

    cleaned_data = form.cleaned_data

    try:
        # 处理文件上传
        if not ("download_url" in request.FILES):
            form.add_error("download_url", u"请选择一个资源文件上传")
            return _render(dict(_ctx_dict, form=form))

        (res, desc, db_file_url) = handle_resource_upload(request.FILES["download_url"])

        if not res:
            form.add_error("download_url", desc)
            return _render(dict(_ctx_dict, form=form))

        if is_edit:
            lesson_resource.download_url = db_file_url
            lesson_resource.name = cleaned_data["name"]

        else:
            lesson_resource = LessonResource(name=cleaned_data["name"],
                                             download_url=db_file_url,
                                             lesson=lesson)
        lesson_resource.save()

        if is_edit:
            messages.success(request, u"修改资源成功")
            lesson_id = lesson_resource.lesson.id
            course_id = lesson_resource.lesson.course.id

            redirect_url = reverse("nadmin:lessons_resources_edit",
                                   args=[course_id, lesson_id, lesson_resource.id])

        else:
            messages.success(request, u"上传资源成功")
            lesson_id = lesson.id
            course_id = lesson.course.id

            redirect_url = reverse("nadmin:lessons_edit_resources",
                                    args=[course_id, lesson_id])

        return redirect(redirect_url)

    except Exception as e:
        logger.error(e)
        messages.error(request, u"上传资源失败")
        return _render(dict(_ctx_dict, form=form))


def lesson_online_exam_handle(form, _render, request=None, _ctx_dict=None, lesson=None, examine=None):
    """处理章节在线练习信息 如果没有相应的记录就创建一个因此没有 is_edit"""

    # 由于 relation_id 不是外键，lesson 要单独传入
    course = lesson.course

    cleaned_data = form.cleaned_data

    if examine == None:
        examine = Examine(**dict(LESSON_ONLINE_EXAM, description=cleaned_data["description"],
                                 is_active=cleaned_data["is_active"], relation_id=lesson.id))

    else:
        examine.description = cleaned_data["description"]
        examine.is_active = cleaned_data["is_active"]

    examine.save()

    messages.success(request, u"修改成功")

    return redirect(reverse("nadmin:lessons_edit_online_exam",
                            args=[course.id,
                                  lesson.id]))


def lesson_homework_handle(form, _render, request=None, _ctx_dict=None,
                           lesson=None, lesson_homework=None):

    """处理章节作业"""

    cleaned_data = form.cleaned_data

    course = lesson.course

    if lesson_homework == None:
        lesson_homework = Homework(**dict(LESSON_HOMEWORK, relation_id=lesson.id,
                                          description=cleaned_data["description"],
                                          is_active=cleaned_data["is_active"]))

    else:
        lesson_homework.description = cleaned_data["description"]
        lesson_homework.is_active = cleaned_data["is_active"]

    lesson_homework.save()

    messages.success(request, u"修改成功")

    return redirect(reverse("nadmin:lessons_edit_homework",
                            args=[course.id,
                                  lesson.id]))


def _handle_item_list(cleaned_data):
    """将用户的输入选项转换为 string"""
    item_list = ""
    button_tpl = '<button value="%s">%s</button>'

    item_list += (button_tpl + "\r\n") % ("a", cleaned_data["item_1"])
    item_list += (button_tpl + "\r\n") % ("b", cleaned_data["item_2"])
    item_list += (button_tpl + "\r\n") % ("c", cleaned_data["item_3"])
    item_list += button_tpl % ("d", cleaned_data["item_4"])

    return item_list


def lesson_paper_quiz_handle(form, _render, request=None, _ctx_dict=None,
                             lesson=None, paper_id=None, quiz=None):

    """处理在线测试的试题信息"""

    is_edit = False
    if quiz:
        is_edit = True

    # 创建的时候 需要判断 paper 是否已经存在
    if not is_edit:
        if paper_id == "create":
            lesson_paper = Paper(relation_id=lesson.id, **LESSON_PAPER)
            lesson_paper.save()

        else:
            lesson_paper = get_object_or_404(Paper, relation_id=lesson.id, **LESSON_PAPER)
    else:
        lesson_paper = quiz.paper

    cleaned_data = form.cleaned_data
    item_list = _handle_item_list(cleaned_data)

    if not is_edit:
        quiz = Quiz()

    quiz.index = cleaned_data["index"]
    quiz.result = cleaned_data["result"]
    quiz.question = cleaned_data["question"]
    quiz.item_list = item_list

    if not is_edit:
        quiz.paper = lesson_paper

    quiz.save()

    if is_edit:

        # 修改的时候不能 只需要传入 quiz
        # 也需要传入 lesson

        messages.success(request, u"修改题成功")
        return redirect("nadmin:lessons_edit_paper_quiz_edit",
                         lesson.course.id, lesson.id, lesson_paper.id, quiz.id)

    else:
        messages.success(request, u"创建试题成功")
        return redirect("nadmin:lessons_edit_paper", lesson.course.id, lesson.id)


class BaseView(object):
    """统一的为 views handler 增加一些信息 比如统计信息等
    example:
    @BaseView
    def home(request, user_id, **extra_info):
        extra_info = kwargs["exgtra_info"]"""

    def _get_individual_courses_count(self):
        try:
            # @XXX stages 是 FK 这样写有问题
            return Course.objects.filter(stages=None).count()

        except Exception as e:
            return -1

    def _get_career_courses_count(self):
        try:
            return CareerCourse.objects.count()

        except Exception as e:
            return -1

    def _get_student_count(self):
        try:
            return UserProfile.objects.filter(groups__name=u"学生").count()

        except Exception as e:
            return -1

    def _get_teacher_count(self):
        try:
            return UserProfile.objects.filter(groups__name=u"老师").count()

        except Exception as e:
            return -1

    def _get_url_dict(self):
        pass

    def __init__(self, handler, _extra_info={}):

        stats_info = {"students_count": self._get_student_count(),
                      "teachers_count": self._get_teacher_count(),
                      "career_courses_count": self._get_career_courses_count(),
                      "individual_courses_count": self._get_individual_courses_count()}

        extra_info = dict(_extra_info, **stats_info)

        def wrapper(*args, **kwargs):
            return handler(*args, **dict(kwargs, extra_info=extra_info))

        self.wrapper = wrapper


    def __call__(self, *args, **kwargs):
        return self.wrapper(*args, **kwargs)


class CareerCoursesBaseView(BaseView):
    """职业课程"""

    def __init__(self, handler):
        _extra_info = {"current_nav_name": "career_courses",
                       "is_individual_course": False}

        super(self.__class__, self).__init__(handler, _extra_info)


class IndividualCoursesBaseView(BaseView):
    """零散课程"""

    def __init__(self, handler):
        _extra_info = {"current_nav_name": "individual_courses",
                       "is_individual_course": True}

        super(self.__class__, self).__init__(handler, _extra_info)


class StudentsBaseView(BaseView):
    """学生模块"""

    def __init__(self, handler):
        _extra_info = {"current_nav_name": "students"}
        super(self.__class__, self).__init__(handler, _extra_info)


class TeachersBaseView(BaseView):
    """教师模块"""

    def _get_class_count(self):
        """获取当前教师进行中的班级数量"""
        pass

    def _get_ended_class_count(self):
        """获得已经结束的班级数量"""
        pass


    def __init__(self, handler):
        _extra_info = {"current_nav_name": "teacher"}

        super(self.__class__, self).__init__(handler, _extra_info)


