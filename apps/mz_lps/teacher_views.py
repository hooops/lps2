#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

from django.core.exceptions import ObjectDoesNotExist

from django.http import Http404, HttpResponse
from django.shortcuts import render
from mz_user.models import *
from mz_course.models import *
from mz_common.models import MyMessage
from mz_lps.models import *
from mz_common.decorators import student_required, teacher_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from mz_common.views import get_course_score, get_rebuild_count,update_study_point_score,check_course_score,\
    sys_send_message, app_send_message

import logging

logger = logging.getLogger("mz_lps.views")


@teacher_required
def class_manage(request, class_id):
    ''' 个人中心 我的班级（教师）管理班级
        在 课程列表中 点击管理课程之后 进入
    '''

    try:
        class_ = Class.objects.get(pk=class_id)
    except:
        return render(request,
                      "mz_common/failure.html",
                      {"reason": u"没有相应的班级"})

    if class_.teacher != request.user:
        return render(request, 'mz_common/failure.html', {'reason': '你不属于该班级，不能进入该班级。'})

    students = ClassStudents.objects.filter(student_class__id=class_id)

    # class 中 career_course 下所有的 stages
    stages = Stage.objects.filter(career_course__id=class_.career_course.id)

    # stages 下的所有 课程
    courses = Course.objects.filter(stages__in=stages.values("id")).order_by("index", "id")

    # course_scores 中 user 在 students, 同时 course 在 courses 集合中的成绩
    course_scores = CourseScore.objects.filter(course__in=courses, user__in=students.values("user"))

    # 统计 course_scores 中每一个学生最后一次重修通过的课程数量

    # 按课程将 course_scores 过滤，仅保存每一个 (course, user) 中 rebuild_count 最大的记录
    last_rebuild_course_scores = {}
    for course_score in course_scores:

        _course_id = course_score.course.id
        _user_id = course_score.user.id

        if "%s:%s" % (_course_id, _user_id) in last_rebuild_course_scores:
            # 比较 rebuild 次数，保存较大的一次
            # 如果多条记录的 rebuild_count 都是 0 则保存第一次的
            if last_rebuild_course_scores["%s:%s" % (_course_id, _user_id)].rebuild_count < course_score.rebuild_count:
                last_rebuild_course_scores["%s:%s" % (_course_id, _user_id)] = course_score
        else:
            last_rebuild_course_scores["%s:%s" % (_course_id, _user_id) ] = course_score

    # 统计每个学生通过的课程数量
    for student in students:
        _passed_courses_count = 0

        # 如果是高校老师需要单独获取学生的真实姓名
        if request.user.is_academic_teacher():
            setattr(student.user, 'real_name', '')
            student_list = student.user.academicuser_set.all()
            if len(student_list):
                student.user.real_name = student_list[0].stu_name

        for k in last_rebuild_course_scores:

            course_id, user_id = k.split(":")
            course_score = last_rebuild_course_scores[k]

            if course_score.user.id == student.user.id:
                if get_course_score(course_score) >= 60:
                    _passed_courses_count += 1

        student.passed_courses_count = _passed_courses_count

    # 获取总课程数量 作为 y 轴
    courses_count = courses.count()

    # 学力总数
    study_point_count = 0

    # 随堂测验学力数
    # 获取有随堂测验的节总数
    for course in courses:
        course_lesson_list = course.lesson_set.all().values_list("id")
        # 观看视频学力数
        study_point_count += len(course_lesson_list) * 1
        # 课后作业学力数
        study_point_count += len(course_lesson_list) * 1
        # 获取有随堂测验的章节总数
        #study_point_count += Paper.objects.filter(examine_type=2,
        #                                                relation_type=1,
        #                                                relation_id__in=course_lesson_list).count() * 1
        pagers =  Paper.objects.filter(examine_type=2,
                                       relation_type=1,
                                       relation_id__in=course_lesson_list)
        study_point_count += Quiz.objects.filter(paper__in=pagers).count()

        #课程总测验学力数
        study_point_count += Paper.objects.filter(examine_type=2,
                                                        relation_type=2,
                                                        relation_id=course.id).count() * 10

        # 项目制作学力数
        study_point_count += Project.objects.filter(examine_type=5,
                                                        relation_type=2,
                                                        relation_id=course.id).count() * 10

    study_points = [s.study_point for s in students]
    if len(study_points) > 0:
        study_points = sorted(study_points)
        if study_points[-1] > study_point_count:
            study_point_count = study_points[-1]

    # 获取直播室信息
    try:
        live_room = LiveRoom.objects.get(live_class=class_)
    except LiveRoom.DoesNotExist:
        live_room = None


    return render(request,
                  "mz_lps/teacher_class_manage.html",
                  {"class_": class_,
                   "live_room": live_room,
                   "courses_count": courses_count,
                   "study_point_count": study_point_count,
                   "students": students})


def _get_course_info(course, user_id, rebuild_count):
    """ 获取课程相关信息 挂载到原 course 对象上 """

    # 章节信息
    lessons = Lesson.objects.filter(course=course)
    lesson_is_complete_count = 0

    lesson_paper_count = 0
    lesson_paper_has_accuracy_count = 0
    lesson_papers = []

    lesson_homework_count = 0
    lesson_homework_complete_count = 0
    lesson_homeworks = []

    for lesson in lessons:
        # 添加额外信息
        lesson = _get_lesson_info(lesson, user_id, rebuild_count)

        # 已经完成的 lesson 数量
        if lesson.is_complete:
            lesson_is_complete_count += 1

        # 随堂测验信息以及总数
        if lesson.lesson_paper:
            lesson_papers.append({"lesson_name": lesson.name,
                                  "accuracy": lesson.lesson_paper.accuracy})
            lesson_paper_count += 1

        # 已经完成的随堂测验个数
        # 此处不能直接使用 if 来判断因为有 accuracy 为 0 的情况
        if lesson.lesson_paper.accuracy != None:
            lesson_paper_has_accuracy_count += 1

        # 存在相应随堂作业
        if lesson.lesson_homework:
            lesson_homeworks.append({"lesson_name": lesson.name,
                                     "upload_file": lesson.lesson_homework.upload_file})
            lesson_homework_count += 1

        # 相应的随堂作业已经完成（已经上传文件）
        if lesson.lesson_homework.upload_file != None:
            lesson_homework_complete_count += 1

    course.lessons_count = len(lessons)
    course.lesson_is_complete_count = lesson_is_complete_count

    course.lesson_paper_count = lesson_paper_count
    course.lesson_paper_has_accuracy_count = lesson_paper_has_accuracy_count
    course.lesson_papers = enumerate(lesson_papers)

    course.lesson_homework_count = lesson_homework_count
    course.lesson_homework_complete_count = lesson_homework_complete_count
    course.lesson_homeworks = enumerate(lesson_homeworks)

    # 用来显示 lesson
    course.lessons = enumerate(lessons, start=1)


    # 课程总测验
    course_paper = Paper.objects.filter(
                        examine_type=2,
                        relation_type=2,
                        relation_id=course.id
                    )
    course_paper_records = PaperRecord.objects.filter(
                                paper=course_paper,
                                student=user_id,
                                rebuild_count=rebuild_count
                            )
    if len(course_paper_records) > 0:
        if course_paper_records[0].accuracy is not None:
            course_paper.accuracy = int(course_paper_records[0].accuracy * 100)
        else:
            course_paper.accuracy = None
    else:
        course_paper.accuracy = None

    course.course_paper = course_paper


    # 获取项目制作信息
    course_project = Project.objects.filter(
                            examine_type=5,
                            relation_type=2,
                            relation_id=course.id
                        )
    if len(course_project) > 0:
        course_project_records = ProjectRecord.objects.filter(project=course_project[0],
                                                              student=user_id,
                                                              rebuild_count=rebuild_count
                                                            )
        if len(course_project_records) > 0:
            course_project[0].record_id = course_project_records[0].id
            course_project[0].upload_file = settings.SITE_URL+settings.MEDIA_URL + str(course_project_records[0].upload_file)
            course_project[0].score = course_project_records[0].score
            course_project[0].remark = course_project_records[0].remark

        else:
            course_project[0].upload_file = None
            course_project[0].score = None

        course.course_project = course_project[0]
    else:
        course.course_project = None
    return course


def _get_lesson_info(lesson, user_id, rebuild_count):
    """ 获取学生课程相关信息 挂载到原 lesson 对象上 """

    # 课程完成记录
    lesson.is_complete = False
    try:
        user_learning_lessons = UserLearningLesson.objects.get(
                                    user=user_id,
                                    lesson=lesson
                                )
        #lesson.user_learning_lessons = user_learning_lessons
        lesson.is_complete = user_learning_lessons.is_complete

    except ObjectDoesNotExist as e:
        pass
    except Exception as e:
        logger.error(e)

    # 随堂测验及结果
    lesson_paper = Paper.objects.filter(
                        examine_type=2,
                        relation_type=1,
                        relation_id=lesson.id
                    )
    paper_records = PaperRecord.objects.filter(
                        paper=lesson_paper,
                        student=user_id,
                        rebuild_count=rebuild_count
                    )
    if len(paper_records) > 0:
        if paper_records[0].accuracy is not None:
            lesson_paper.accuracy = int(paper_records[0].accuracy * 100)
        else:
            lesson_paper.accuracy = None
    else:
        lesson_paper.accuracy = None

    lesson.lesson_paper = lesson_paper

    # 随堂作业以及结果
    lesson_homework = Homework.objects.filter(
                        examine_type=1,
                        relation_type=1,
                        relation_id=lesson.id
                    )
    homework_records = HomeworkRecord.objects.filter(
                            homework=lesson_homework,
                            student=user_id
                        )
    if len(homework_records) > 0:
        lesson_homework.upload_file = homework_records[0].upload_file

    else:
        lesson_homework.upload_file = None

    lesson.lesson_homework = lesson_homework

    return lesson


@teacher_required
def student_detail(request, class_id, user_id):
    ''' 学员详情 显示班级中某学生的学习计划 '''

    try:
        class_ = Class.objects.get(pk=class_id)
        class_student = ClassStudents.objects.get(student_class=class_id,
                                                  user=user_id)
    except Class.DoesNotExist:
        return render(request,
                      "mz_common/failure.html",
                      {"reason": u"班级不存在"})

    if class_.teacher != request.user:
        return render(request, 'mz_common/failure.html', {'reason': '你不属于该班级，不能进入该班级。'})

    # 获取最新学习计划
    planning_list = Planning.objects.filter(
                        user=user_id,
                        career_course=class_.career_course
                    ).order_by(
                        "-version",
                        "-id"
                    )

    is_pause = False
    planning = None
    if len(planning_list) > 0:
        planning = planning_list[0]

        # 是否暂停状态 最近一次的 restore_date 是不是为空
        planning_pauses = PlanningPause.objects.filter(planning=planning.id).order_by("-id")
        if len(planning_pauses) > 0:

            is_pause = True
            planning_pause = planning_pauses[0]

            # 不合法的时间，返回 None
            if planning_pause.restore_date:
                is_pause = False

    # 职业课程的相应阶段
    stages = Stage.objects.filter(career_course=class_.career_course)

    for stage in stages:

        # 获取阶段中的课程
        courses = Course.objects.filter(stages=stage).order_by("index", "id")

        for course in courses:
            # 获取当前课程重修次数
            rebuild_count = get_rebuild_count(user_id, course)
            course = _get_course_info(course, user_id, rebuild_count)

        stage.courses = enumerate(courses, start=1)

        # 阶段任务
        stage_missons = Mission.objects.filter(teacher=class_.teacher,
                                               examine_type=4,
                                               relation_type=3,
                                               relation_id=stage.id)
        for stage_misson in stage_missons:
            stage_mission_records = MissionRecord.objects.filter(
                                        mission=stage_misson.id
                                    )

            if len(stage_mission_records) > 0:
                stage_misson.score = stage_mission_records[0].score

            else:
                stage_misson.score = None

        stage.stage_missons = enumerate(stage_missons, start=1)

    return render(request,
                  "mz_lps/teacher_student_planning.html",
                  {"class_": class_,
                   "is_pause": is_pause,
                   "class_student": class_student,
                   "stages": enumerate(stages, start=1),
                   "planning": planning})


@csrf_exempt
@teacher_required
def pause_planning(request):
    ''' 暂停学习进度 '''

    reason = request.POST.get("reason") or ""
    planning_id = request.POST.get("planning_id") or ""

    try:
        planning_id = int(planning_id)

    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        planning = Planning.objects.get(pk=planning_id)
    except:
        return HttpResponse(u"指定的 planning 不存在",
                            content_type="application/json")

    try:
        PlanningPause.objects.create(pause_date=datetime.now(),
                                     reason=reason,
                                     teacher=request.user,
                                     planning=planning)

        return HttpResponse(json.dumps("ok"),
                            content_type="application/json")

    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res


@csrf_exempt
@teacher_required
def restore_planning(request):
    ''' 恢复学习进度 '''

    planning_id = request.POST.get("planning_id") or ""

    try:
        planning_id = int(planning_id)

    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        planning = Planning.objects.get(pk=planning_id)
    except:
        return HttpResponse(u"指定的 planning 不存在",
                            content_type="application/json")

    try:
        planning_pauses = PlanningPause.objects.filter(planning=planning.id,
                                                       teacher=request.user).order_by("-id")

        if len(planning_pauses) > 0:
            last_planning_pause = planning_pauses[0]
            last_planning_pause.restore_date = datetime.now()
            last_planning_pause.save()

        return HttpResponse(json.dumps("ok"),
                            content_type="application/json")

    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res


@csrf_exempt
@teacher_required
def set_course_project_score(request):
    ''' 给项目制作打分 '''
    course_id = request.POST.get("course_id") or ""
    user_id  = request.POST.get("user_id") or ""
    course_project_record_id = request.POST.get("course_project_record_id") or ""
    score = request.POST.get("score") or ""
    try:
        course_project_record_id = int(course_project_record_id)
        score = int(score)
        course_id = int(course_id)
        user_id = int(user_id)
    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        course_project_record = ProjectRecord.objects.get(pk=course_project_record_id)
    except:
        res = HttpResponse(u"指定的项目考核不存在",
                            content_type="application/json")
        res.status_code = 404
        return res

    try:
        user = UserProfile.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)
    except:
        res = HttpResponse(u"学生或课程信息不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        rebuild_count = get_rebuild_count(user, course)
        # 查找是否有学分考核记录,没有的话则创建一条
        check_course_score(user, course)
        # 更新课程得分表
        update_study_point_score(user, score=score, examine=course_project_record.project, examine_record=course_project_record, teacher=request.user, course=course, rebuild_count=rebuild_count)

        #### 给对应学员推送消息 开始 ####
        # 获取该职业课程老师班级下的所有学员
        alert_msg = "老师已给你<a href='"+str(settings.SITE_URL)+ \
                    "/lps/learning/plan/"+str(course.stages.career_course.id)+"/?stage_id="+ \
                    str(course.stages.id)+"'>"+str(course.name)+"</a>课程的项目制作打了分，<a href='"+str(settings.SITE_URL)+\
                    "/lps/learning/plan/"+str(course.stages.career_course.id)+"/?stage_id="+\
                    str(course.stages.id)+"'>赶快去看看吧</a>！"
        sys_send_message(0,user.id,1,alert_msg)

        alert_msg = "老师已给你"+str(course.name)+"课程的项目制作打了分，赶快去看看吧！"
        app_send_message("系统消息", alert_msg, [user.token])
        #### 给对应学员推送消息 结束 ####

        return HttpResponse(json.dumps("ok"),
                            content_type="application/json")
    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res

@csrf_exempt
@teacher_required
def add_mission(request):
    ''' 添加额外任务 '''

    stage_id = request.POST.get("stage_id", "")
    mission_name = request.POST.get("mission_name", "")
    mission_desc = request.POST.get("mission_desc", "")

    try:
        stage_id = int(stage_id)
        if mission_name == "":
            raise Exception(u"mission_name 不能为空")
    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        stage = Stage.objects.get(pk=stage_id)
    except:
        res = HttpResponse(u"指定的 stage 不存在",
                            content_type="application/json")
        res.status_code = 400
        return res

    try:
        Mission.objects.create(teacher=request.user,
                               name=mission_name,
                               description=mission_desc,
                               relation_type=3,
                               examine_type=4,
                               relation_id=stage_id)

        #### 给对应学员推送消息 开始 ####
        # 获取该职业课程老师班级下的所有学员
        class_list = Class.objects.filter(teacher=request.user, career_course=stage.career_course).values_list("id")
        student_list = UserProfile.objects.filter(id__in=
                ClassStudents.objects.filter(student_class_id__in=class_list).values_list("user_id"))
        for student in student_list:
            alert_msg = "老师在你的职业课程 - "+str(stage.career_course.name)+"添加了额外任务，<a href='"+\
                        str(settings.SITE_URL)+"/lps/learning/plan/"+str(stage.career_course.id)+\
                        "/?stage_id="+str(stage_id)+"'>赶快去看看吧！</a>"
            sys_send_message(0,student.id,1,alert_msg)

            alert_msg = "老师在你的职业课程 - "+str(stage.career_course.name)+"添加了额外任务，赶快去看看吧！"
            app_send_message("系统消息", alert_msg, [student.token])
        #### 给对应学员推送消息 结束 ####

        return HttpResponse(json.dumps("ok"),
                    content_type="application/json")
    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res


@csrf_exempt
@teacher_required
def edit_mission(request):
    ''' 修改额外任务 '''

    mission_id = request.POST.get("mission_id") or ""
    mission_name = request.POST.get("mission_name") or ""
    mission_desc = request.POST.get("mission_desc") or ""

    try:
        mission_id = int(mission_id)
        if mission_name == "":
            raise Exception(u"mission_name 不能为空")

    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        mission = Mission.objects.get(pk=mission_id)

    except:
        res = HttpResponse(u"指定的 mission 不存在",
                            content_type="application/json")
        res.status_code = 400
        return res

    try:
        mission.name = mission_name
        if mission_desc != "":
            mission.description = mission_desc

        mission.save()

        return HttpResponse(json.dumps("ok"),
                    content_type="application/json")

    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res


@csrf_exempt
@teacher_required
def set_mission_score(request):
    ''' 额外项目评分 '''

    mission_id = request.POST.get("mission_id")
    user_id = request.POST.get("user_id")
    score = request.POST.get("score")

    try:
        mission_id = int(mission_id)
        user_id = int(user_id)
        score = int(score)
        if score > 100 or score < 0:
            raise Exception(u"score 的范围错误")

    except:
        res = HttpResponse(u"参数不正确",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        user = UserProfile.objects.get(pk=user_id)
        mission = Mission.objects.get(pk=mission_id)
    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"参数不正确，指定的 user 或 mission 不存在",
                           content_type="application/json")
        res.status_code = 400
        return res

    try:
        # 获取重修次数最大的一次 如果还没有相应的记录 就生成一条
        mission_records = MissionRecord.objects.filter(student=user,
                                                        mission=mission).order_by("-rebuild_count")

        if len(mission_records) > 0:
            mission_record = mission_records[0]
            mission_record.teacher = request.user
            mission_record.study_point = score
            mission_record.save()

        else:
            MissionRecord.objects.create(examine_id=mission.id,
                                         student=user,
                                         score=score,
                                         mission=mission)

        try:
            stage = Stage.objects.get(pk=mission.relation_id)
        except Exception as e:
            logging.error(e)
            res = HttpResponse(u"查不到该任务对应的职业课程阶段",
                               content_type="application/json")
            res.status_code = 400
            return res

        # 更新班级学力汇总信息
        if score > 0:
            class_students = ClassStudents.objects.filter(user=user, student_class__career_course=stage.career_course)
            if len(class_students) > 0:
                class_students[0].study_point += score
                class_students[0].save()

        return HttpResponse(json.dumps("ok"),
                    content_type="application/json")

    except Exception as e:
        logging.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res

####################### 直播室 开始 ####################################
@csrf_exempt
@teacher_required
def update_live_room_status(request):
    try:
        live_id = request.POST.get("live_id", None)
        live_is_open = request.POST.get("live_is_open", None)
        live_room = LiveRoom.objects.get(live_id=live_id)
        if live_room.live_class.teacher != request.user:
            return HttpResponse(json.dumps("noauth"),
                                content_type="application/json")
        live_room.live_is_open = live_is_open
        live_room.save()
        # 如果是打开状态则需要发送消息提醒
        if live_is_open == "1":
            # 如果5分钟内没有新的直播室开启通知消息则给该班学生增加一条消息通知
            if MyMessage.objects.filter(userA=0, action_type=1,action_content__icontains=str(live_room.live_class.coding)+"班的直播教室",
                                     date_action__gt=datetime.now() - timedelta(minutes = 5)).count() == 0:
                #### 给对应班级学生推送消息 开始 ####
                # 获取对应班级的学生信息
                student_list = UserProfile.objects.filter(id__in=
                    ClassStudents.objects.filter(student_class=live_room.live_class).values_list("user_id"))
                for student in student_list:
                    alert_msg = str(live_room.live_class.coding)+"班的直播教室已开启，老师在教室里等你哦~,<a href='"+\
                                str(settings.SITE_URL)+"/lps/live/play/?live_id="+str(live_room.live_id)+"'>赶快进入吧</a>！"
                    sys_send_message(0,student.id,1,alert_msg)
                    alert_msg = str(live_room.live_class.coding)+"班的直播教室已开启，老师在教室里等你哦~"
                    app_send_message("系统消息", alert_msg, [student.token])
                #### 给对应班级学生推送消息 结束 ####
        return HttpResponse(json.dumps("ok"),
                            content_type="application/json")
    except Exception as e:
        logger.error(e)
        res = HttpResponse(u"操作失败",
                           content_type="application/json")
        res.status_code = 500
        return res

# 直播播放页面
@login_required
def live_play(request):
    try:
        # 接受当前的班级号
        live_id = request.GET.get("live_id", None)
        if live_id is not None:
            live_room = LiveRoom.objects.get(live_id=live_id)
            if live_room.live_is_open == 0:
                return render(request, 'mz_common/failure.html',{'reason':'直播室还未开启，请老师开启直播室后再试。'})
            # 判断当前用户是否属于该班级，如不属于该班级便不能进入直播室
            if (request.user.is_student() and ClassStudents.objects.filter(user=request.user, student_class=live_room.live_class).count() == 0) \
                or (request.user.is_teacher() and live_room.live_class.teacher != request.user):
                return render(request, 'mz_common/failure.html',{'reason':'你不属于该班级，不能进入该班级的直播室。'})
            nick_name = request.user.nick_name
            if request.user.is_student():
                join_url = live_room.student_join_url
                token = live_room.student_client_token
            elif request.user.is_teacher():
                join_url = live_room.teacher_join_url
                token = live_room.teacher_token
    except Class.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'没有该班级。'})
    except Exception as e:
        logger.error(e)
        return render(request, 'mz_common/failure.html',{'reason':'服务器出错啦。'})
    return render(request, 'mz_lps/live_play.html',locals())

# 直播室域名认证失败跳转到的地址
def domain_auth_failure(request):
    return render(request, 'mz_common/failure.html',{'reason':'请登录麦子官网后台再进入直播室。'})

####################### 直播室 结束 ####################################

@csrf_exempt
def teacher_save_remark(request):
    try:
        course_id = request.POST['course_id']
        user_id = request.POST['user_id']
        remark = request.POST['remark']
        rebuild_count = get_rebuild_count(user_id, course_id)
        project = Project.objects.get(examine_type=5, relation_type=2, relation_id=course_id)
        project_record = ProjectRecord.objects.get(project=project, student_id=user_id, rebuild_count=rebuild_count)
        project_record.remark = remark
        project_record.save()
    except Exception as e:
        return HttpResponse(json.dumps("no"),content_type="application/json")
    return HttpResponse(json.dumps("ok"),content_type="application/json")

