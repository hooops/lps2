#!/usr/bin/env python
#coding=utf8

import itertools
import logging
from functools import wraps, partial

from django.db.models import F, Q
from django.http import HttpResponse, HttpResponseNotAllowed
from django.core.context_processors import csrf
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django import template
from django.template import loader, RequestContext, Library
from django.contrib.auth.models import Group

from utils.tool import generate_random, second_to_time, upload_generation_dir

from mz_common.models import MyMessage
from mz_user.models import (UserProfile, CityDict, ProvinceDict, MyCourse, Certificate,
                            UserUnlockStage)
from mz_course.models import CareerCourse, Course, Stage, Lesson
from mz_lps.models import CourseScore, PaperRecord, Paper, ProjectRecord

from mz_common.views import all_stu_ranking, current_user_ranking, current_study_point, get_course_score
from mz_course.views import get_recent_learned_lesson

from .helper import intval, page_items, get_or_none, authenticated, Route
from .forms import StudentForm

from base_views import StudentsBaseView

from .models import LESSON_PAPER, COURSE_PAPER, LESSON_HOMEWORK, LESSON_ONLINE_EXAM, COURSE_PROJECT

route = Route.route
logger = logging.getLogger('mz_nadmin.views')


def sum_lessons_time(student):
    """获取总的学习时间 """

    try:
        sum_time = student.mylesson.extra(select={'sum': 'sum(video_length)'}).values('sum')[0]['sum']

        if sum_time != None:
            sum_time = second_to_time(mylesson_time)

        else:
            sum_time = "0小时"

    except Exception as e:
        sum_time = "0小时"

    return sum_time


def get_provinces():
    """获取 provinces 列表"""

    provinces = ProvinceDict.objects.all()
    return provinces


def _get_study_point_by_course(user_id, course_id):
    """获取学生在某课程获得的学力"""

    course_lesson_list = course.lesson_set.all().values_list("id")

    # 观看视频学力数
    study_point_count += len(course_lesson_list) * 1
    # 课后作业学力数
    study_point_count += len(course_lesson_list) * 1
    # 获取有随堂测验的章节总数
    study_point_count += Paper.objects.filter(examine_type=2,
                                                    relation_type=1,
                                                    relation_id__in=course_lesson_list).count() * 1
    # 课程总测验学力数
    study_point_count += Paper.objects.filter(examine_type=2,
                                                    relation_type=2,
                                                    relation_id=course.id).count() * 10
    # 项目制作学力数
    study_point_count += Project.objects.filter(examine_type=5,
                                                    relation_type=2,
                                                    relation_id=course.id).count() * 10


def _get_individual_course(course_id):
    """ 获取零散课程信息 """

    try:
        course = Course.objects.get(id=course_id)

    except Course.DoesNotExist:
        logging.warning(u"零散课程不存在 course:%s" % course_id)
        return False

    # 获取最近观看的章节
    setattr(course, "recent_learned_lesson", u"还未观看过该课程")
    try:
        recent_learned_lesson = get_recent_learned_lesson(request.user, course)

    except Exception as e:
        logger.error(e)
        recent_learned_lesson = None

    if recent_learned_lesson != None:
        course.recent_learned_lesson = u"最近观看《"+str(recent_learned_lesson.lesson.name)+"》"

    return course


def _get_career_course(student, career_course_id):
    """针对于用户选择的 career_course 添加学力排名等信息
    study_point, cur_ranking, stu_count
    其中 study_point 中包含了 classobj.id
    """

    career_course_id = intval(career_course_id)

    try:
        career_course = CareerCourse.objects.get(id=career_course_id)

    except CareerCourse.DoesNotExist:
        logger.error(u"career_course:%s 不存在" % career_course_id)
        return False

    # 获取学力
    # 返回的 classobj 中可以获取相应的班级编号
    # 此函数已经在内部处理了异常
    study_point = current_study_point(career_course, student)
    setattr(career_course, "study_point", study_point)

    # 根据职业课程找到对应的班级 获取班级排名
    curr_student_ranking = current_user_ranking(career_course, student)

    if curr_student_ranking == "NotSignUp":
        # 未报名
        setattr(career_course, "cur_ranking", u"NotSignUp")

    else:
        all_student = all_stu_ranking(career_course, student)
        setattr(career_course, "cur_ranking", intval(curr_student_ranking))
        setattr(career_course, "stu_count", len(all_student))

    return career_course


@route(url_regex=r"^users/students$", name="users_students")
@authenticated
@require_GET
@StudentsBaseView
def students(request, **kwargs):
    """学生列表"""

    q = request.GET.get("q", "")

    page_num = intval(request.GET.get("page_num", 1))
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    students_query_set = UserProfile.objects.filter(groups__name=u"学生").order_by("-id")

    if q != "":
        students_query_set = students_query_set.filter(username__contains=q)

    students = page_items(students_query_set,
                          page_num)

    return render(request,
                  "mz_nadmin/students.html",

                  {"is_students": True,

                   "students": students,
                   "messages": msgs,

                   "q": q,
                   "extra_info": extra_info})


@route(url_regex=r"^users/students/create$", name="students_create")
@authenticated
@require_http_methods(["GET", "POST"])
@StudentsBaseView
def student_create(request, **kwargs):
    """创建学生账户"""

    _render = partial(render, request, "mz_nadmin/students_edit.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    provinces = ProvinceDict.objects.all()

    _ctx_dict = {"is_students_create": True,
                 "tabs_active": "info",

                 "extra_info": extra_info,
                 "messages": msgs,

                 "provinces": provinces}

    if request.method == "GET":
        form = StudentForm()
        return _render(dict(_ctx_dict, form=form))

    else:
        form = StudentForm(request.POST)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        else:
            cleaned_data = form.cleaned_data

            try:
                student_group = Group.objects.get(name=u"学生")

                student = UserProfile(email=cleaned_data["email"],
                                      username=cleaned_data["username"],
                                      mobile=cleaned_data["mobile"],
                                      nick_name=cleaned_data["nick_name"],
                                      city=cleaned_data["city"],
                                      qq=cleaned_data["qq"])

                student.save()
                student_group.user_set.add(student)

                messages.success(request, u"添加学生成功")
                return redirect(reverse("nadmin:users_students"))

            except Exception as e:
                logger.error(e)
                messages.error(request, u"添加学生失败，请稍后再试")

                return _render(dict(_ctx_dict, form=form))


@route(url_regex=r"^users/students/(\d+)$", name="students_edit")
@authenticated
@require_http_methods(["GET", "POST"])
@StudentsBaseView
def student_edit(request, student_id, **kwargs):
    """修改学生信息"""

    _render = partial(render, request, "mz_nadmin/students_edit.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    city_id = student.city.id if student.city else None
    city = get_or_none(CityDict, id=city_id)

    provinces = ProvinceDict.objects.all()

    if city != None:
        province = get_or_none(ProvinceDict, id=city.province.id)

    else:
        province = None

    sum_time = sum_lessons_time(student)

    _ctx_dict = {"is_students_edit": True,
                 "tabs_active": "info",

                 "extra_info": extra_info,
                 "messages": msgs,
                 "provinces": provinces,

                 "province": province,
                 "city": city,
                 "sum_time": sum_time,
                 "student": student}

    if request.method == "GET":
        form = StudentForm(initial={"email": student.email,
                                    "username": student.username,
                                    "mobile": student.mobile,
                                    "nick_name": student.nick_name,
                                    "city": student.city,
                                    "qq": student.qq})

        return _render(dict(_ctx_dict, form=form))

    else:
        form = StudentForm(request.POST, instance=student)

        if not form.is_valid():
            return _render(dict(_ctx_dict, form=form))

        cleaned_data = form.cleaned_data

        student.email=cleaned_data["email"]
        student.username=cleaned_data["username"]
        student.mobile=cleaned_data["mobile"]
        student.nick_name=cleaned_data["nick_name"]
        student.city=cleaned_data["city"]
        student.qq=cleaned_data["qq"]

        try:
            student.save()
            messages.success(request, u"修改学生信息成功")

            return redirect(reverse("nadmin:students_edit", args=[student.id]))

        except Exception as e:
            logger.error(e)
            messages.error(request, u"修改学生信息失败，请稍后再试")
            return _render(dict(_ctx_dict, form=form))

    return _render(_ctx_dict)


@authenticated
@require_GET
@StudentsBaseView
def student_individual_courses(request, student_id, **kwargs):
    """学生信息 零散课程"""

    _render = partial(render, request, "mz_nadmin/student_individual_courses.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    # 返回的只是 course id
    query_set = MyCourse.objects.filter(
                    user=student,
                    course_type=1
                ).order_by(
                    "index",
                    "-id"
                )

    individual_course_ids = page_items(query_set, page_num)
    courses = map(_get_individual_course, individual_course_ids)

    _ctx_dict = {"is_students_edit": True,
                 "tabs_active": "individual_courses",
                 "extra_info": extra_info,
                 "courses": courses,
                 "messages": msgs,
                 "student": student}

    return _render(_ctx_dict)


@route(url_regex="^users/students/(\d+)/career_courses$", name="students_career_courses")
@authenticated
@require_GET
@StudentsBaseView
def student_career_courses(request, student_id, **kwargs):
    """学生信息 职业课程"""

    _render = partial(render, request, "mz_nadmin/students_career_courses.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    # 职业课程
    my_courses_qs = MyCourse.objects.filter(
                        user=student,
                        course_type=2
                    ).order_by(
                        "index",
                        "-id"
                    )

    my_courses = page_items(my_courses_qs, page_num)
    career_courses = map(partial(_get_career_course, student),
                         [my_course.course for my_course in my_courses])

    _ctx_dict = {"is_students_edit": True,

                 "extra_info": extra_info,
                 "career_courses": career_courses,
                 "my_courses": my_courses,
                 "tabs_active": "career_courses",

                 "messages": msgs,
                 "student": student}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/career_courses/(\d+)$", name="students_career_courses_info")
@authenticated
@require_GET
@StudentsBaseView
def student_career_course_info(request, student_id, career_course_id, **kwargs):
    """职业课程详情 显示职业课程信息 以及 阶段列表"""

    _render = partial(render, request, "mz_nadmin/students_career_courses_info.html")

    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    career_course_with_student_info = _get_career_course(student,
                                                         career_course.id)

    stages_query_set = Stage.objects.filter(career_course__id=career_course_id)
    stages = page_items(stages_query_set, page_num)

    # 取出阶段解锁数据
    for stage in stages:
        # @XXX 数据库访问优化
        unlock_stages = get_or_none(UserUnlockStage, user=student, stage=stage)

        if unlock_stages != None:
            stage.unlock = True

    _ctx_dict = {"is_students_edit": True,

                 "extra_info": extra_info,
                 "career_course": career_course_with_student_info,
                 "student": student,
                 "stages": stages}

    return _render(_ctx_dict)


def _is_stage_unlocked(user, stage):
    """判断指定的阶段对于指定的用户是否 *解锁*"""

    unlock_stages = get_or_none(UserUnlockStage, user=user, stage=stage)
    if unlock_stages == None:
        return False

    else:
        return True


def _is_user_finash_lesson(user_id, lesson_id):
    """判断用户是否已经看完指定课程"""

    is_complete = False
    try:
        user_learning_lessons = UserLearningLesson.objects.get(
                                    user=user_id,
                                    lesson=lesson_id
                                )

        if user_learning_lessons.is_complete:
            is_complete = True

    except Exception as e:
        logger.error(e)

    return is_complete


def _is_user_finash_all_lesson(user_id, course):
    """判断用户是否已看完课程中的全部 lesson"""

    lessons = Lesson.objects.filter(course=course)
    is_complete = True

    for lesson in lessons:
        if not _is_user_finash_lesson(user_id, lesson.id):
            is_complete = False
            break

    return is_complete


def _is_user_pass_course(user, course):
    """判断用户是否已经通过某课程"""

    # 根据最后一次重修成绩进行判断
    course_scores = CourseScore.objects.filter(course__in=courses,
                                               user__in=students.values("user"))

    if get_course_score(course_score) > 60:
        return True

    else:
        return False


def _get_course_score(user, course):
    """返回某用户对于某课程的最后分数"""
    pass


@route(url_regex=r"^users/students/(\d+)/career_courses/(\d+)/stage/(\d+)$", name="students_stages_info")
@authenticated
@require_GET
@StudentsBaseView
def student_stage_info(request, student_id, career_course_id, stage_id, **kwargs):
    """阶段信息"""

    _render = partial(render, request, "mz_nadmin/students_stage_info.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    career_course_id = intval(career_course_id)
    career_course = get_object_or_404(CareerCourse, id=career_course_id)

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    stage_id = intval(stage_id)
    stage = get_object_or_404(Stage, id=stage_id)
    stage.islock = not _is_stage_unlocked(student, stage)

    # 获取阶段中的课程
    courses_qs = Course.objects.filter(stages=stage)
    courses = page_items(courses_qs, page_num)

    # 课程中关联用户信息
    for course in courses:
        course.is_complete = _is_user_finash_all_lesson(student, course)

        # 获取通过状态 最后一次重修成绩进行判断
        course_scores_qs = CourseScore.objects.filter(
                                course=course,
                                user=student
                           ).order_by(
                                "-rebuild_count"
                           )

        course.course_score = None
        for course_score in course_scores_qs:
            course.course_score = course_score
            course.course_score.is_pass = get_course_score(course_score) >= 60
            break

    _ctx_dict = {"extra_info": extra_info,
                 "career_course": career_course,
                 "student": student,
                 "stage": stage,
                 "courses": courses}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/courses/(\d+)$", name="students_courses_info")
@authenticated
@require_GET
@StudentsBaseView
def student_course_info(request, student_id, course_id, **kwargs):
    """用户课程详情 章节列表"""

    _render = partial(render, request, "mz_nadmin/students_courses_info.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    course_id = intval(course_id)
    course = get_or_none(Course, id=course_id)

    # @XXX 是否应该是 课程的学力? 而不是职业课程的
    # class 只能和 carrer_course 关联 独立课程的学分就没有意义
    career_course = course.stages.career_course
    study_point = current_study_point(career_course, student)

    # 获取章节列表
    lessons_qs = Lesson.objects.filter(course=course_id)
    lessons = page_items(lessons_qs, page_num)

    for lesson in lessons:
        lesson.is_complete = _is_user_finash_lesson(student_id, lesson.id)

    _ctx_dict = {"is_students_edit": True,

                 "extra_info": extra_info,
                 "tabs_active": "lessons",

                 "student": student,
                 "course": course,
                 "lessons": lessons,
                 "study_point": study_point}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/courses/(\d+)/lessons/papers$",
       name="students_courses_info_lessons_papers")
@authenticated
@require_GET
@StudentsBaseView
def student_course_lesson_papers(request, student_id, course_id, **kwargs):
    """用户课程详情 随堂测验"""

    _render = partial(render, request, "mz_nadmin/students_courses_lesson_papers.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    course_id = intval(course_id)
    course = get_or_none(Course, id=course_id)

    lessons_qs = Lesson.objects.filter(course=course_id)

    lesson_papers_qs = Paper.objects.filter(**dict(LESSON_PAPER, relation_id__in=lessons_qs.values("id")))
    lesson_papers = page_items(lesson_papers_qs, page_num)

    for lesson_paper in lesson_papers:

        lesson = lessons_qs.get(id=lesson_paper.relation_id)
        lesson_paper.lesson = lesson

        lesson_is_complete = _is_user_finash_lesson(student_id, lesson.id)
        lesson_paper.lesson_is_complete = lesson_is_complete

        paper_records = PaperRecord.objects.filter(
                        paper=lesson_paper,
                        student=student.id
                    ).order_by(
                        "-rebuild_count"
                    )

        if len(paper_records) > 0:
            lesson_paper.accuracy = int(paper_records[0].accuracy * 100)

        else:
            lesson_paper.accuracy = -1

    _ctx_dict = {"tabs_active": "lesson_papers",
                 "is_students_edit": True,

                 "extra_info": extra_info,
                 "student": student,
                 "course": course,
                 "lesson_papers": lesson_papers}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/courses/(\d+)/lessons_homeworks$",
       name="students_courses_info_lessons_homeworks")
@authenticated
@require_GET
@StudentsBaseView
def student_course_lesson_homeworks(request, student_id, course_id, **kwargs):
    """用户课程详情 随堂作业"""

    _render = partial(render, request, "mz_nadmin/students_courses_lesson_homework.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    course_id = intval(course_id)
    course = get_or_none(Course, id=course_id)

    lessons_qs = Lesson.objects.filter(course=course_id)

    lesson_homeworks_qs = Paper.objects.filter(**dict(LESSON_HOMEWORK, relation_id__in=lessons_qs.values("id")))
    lesson_homeworks = page_items(lesson_homeworks_qs, page_num)

    # @XXX 同样数据库访问次数问题
    for lesson_homework in lesson_homeworks:

        lesson = lessons_qs.get(id=lesson_homework.relation_id)
        lesson_paper.lesson = lesson

        homework_records = HomeworkRecord.objects.filter(
                        homework=lesson_homework,
                        student=user_id
                    ).order_by(
                        "-rebuild_count"
                    )

        if len(homework_records) > 0:
            lesson_homework.upload_file = homework_records[0].upload_file

        else:
            lesson_homework.upload_file = None

    _ctx_dict = {"extra_info": extra_info,
                 "tabs_active": "lesson_homeworks",
                 "is_students_edit": True,

                 "student": student,
                 "course": course,
                 "lesson_homeworks": lesson_homeworks}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/courses/(\d+)/paper$",
       name="students_courses_paper")
@authenticated
@require_GET
@StudentsBaseView
def students_courses_paper(request, student_id, course_id, **kwargs):
    """用户课程详情 课程总测验"""

    _render = partial(render, request, "mz_nadmin/students_courses_paper.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    course_id = intval(course_id)
    course = get_or_none(Course, id=course_id)

    lessons_qs = Lesson.objects.filter(course=course_id)

    course_paper = Paper.objects.filter(**dict(COURSE_PAPER, relation_id=course.id))

    course_paper_records = PaperRecord.objects.filter(
                                paper=course_paper,
                                student=student_id
                            ).order_by(
                                "-rebuild_count"
                            )

    if len(course_paper_records) > 0:
        course_paper.accuracy = int(course_paper_records[0].accuracy * 100)

    else:
        course_paper.accuracy = -1

    _ctx_dict = {"extra_info": extra_info,
                 "tabs_active": "course_paper",
                 "is_students_edit": True,

                 "student": student,
                 "course": course,
                 "course_paper": course_paper}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/courses/(\d+)/project$",
       name="students_courses_project")
@authenticated
@require_GET
@StudentsBaseView
def students_courses_project(request, student_id, course_id, **kwargs):
    """用户课程详情 项目制作"""

    _render = partial(render, request, "mz_nadmin/students_courses_project.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    course_id = intval(course_id)
    course = get_or_none(Course, id=course_id)

    lessons_qs = Lesson.objects.filter(course=course_id)

    course_project = Paper.objects.filter(**dict(COURSE_PROJECT, relation_id=course.id))

    course_project_records = ProjectRecord.objects.filter(project=course_project,
                                                          student=student.id)

    if len(course_project_records) > 0:
        course_project.record_id = course_project_records[0].id
        course_project.upload_file = course_project_records[0].upload_file
        course_project.score = course_project_records[0].score

    else:
        course_project.upload_file = None
        course_project.score = -1

    _ctx_dict = {"extra_info": extra_info,
                 "tabs_active": "course_project",
                 "is_students_edit": True,

                 "student": student,
                 "course": course,
                 "course_project": course_project}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/favor_courses$",
       name="students_favor_courses")
@authenticated
@require_GET
@StudentsBaseView
def student_favor_courses(request, student_id, **kwargs):
    """用户收藏的课程 (不是职业课程)"""

    _render = partial(render, request, "mz_nadmin/students_favor_courses.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    courses_qs = Course.objects.filter(userprofile__id=student.id)
    courses = page_items(courses_qs, page_num)

    _ctx_dict = {"extra_info": extra_info,
                 "tabs_active": "favor_courses",
                 "is_students_edit": True,

                 "courses": courses,
                 "messages": msgs,
                 "student": student}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/messages$",
       name="students_messages")
@authenticated
@require_GET
@StudentsBaseView
def student_messages(request, student_id, **kwargs):
    """用户的消息列表"""

    _render = partial(render, request, "mz_nadmin/students_messages.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    query_set = MyMessage.objects.filter(userB=student.id)
    recive_messages = page_items(query_set, page_num)

    _ctx_dict = {"extra_info": extra_info,
                 "tabs_active": "messages",
                 "is_students_edit": True,

                 "messages": msgs,
                 "recive_messages": recive_messages,
                 "student": student}

    return _render(_ctx_dict)


@route(url_regex=r"^users/students/(\d+)/certificates$",
       name="students_certificates")
@authenticated
@require_GET
@StudentsBaseView
def student_certificates(request, student_id, **kwargs):
    """用户证书"""

    _render = partial(render, request, "mz_nadmin/students_certificates.html")
    msgs = messages.get_messages(request)
    extra_info = kwargs["extra_info"]

    page_num = intval(request.GET.get("page_num", 1))

    student_id = intval(student_id)
    student = get_object_or_404(UserProfile, id=student_id)

    query_set = Certificate.objects.filter(userprofile__id=student.id)
    certificates = page_items(query_set, page_num)

    _ctx_dict = {"kwargs": kwargs,
                 "tabs_active": "certificates",
                 "is_students_edit": True,

                 "extra_info": extra_info,
                 "messages": msgs,
                 "certificates": certificates,
                 "student": student}

    return _render(_ctx_dict)


# apis


@require_GET
def user_search(request):
    """用户搜索"""

    pass


@require_GET
def get_city(province_id):
    """ 获取指定 province 的城市列表 """

    province_id = intval(province_id)
    citys = CityDict.objects.filter(province=province_id)

    return citys


