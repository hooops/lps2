# -*- coding: utf-8 -*-
from __future__ import division
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q
from datetime import datetime, timedelta
from mz_user.models import *
from mz_course.models import *
from mz_lps.models import *
from mz_common.views import get_rebuild_count,get_uncomplete_quiz,check_exam_is_complete,update_study_point_score,\
    current_study_point,all_stu_ranking,current_user_ranking,file_upload, get_course_score, sys_send_message,\
    app_send_message,check_course_score
from mz_course.views import get_real_amount
from mz_common.decorators import student_required
import logging, os, json, re

logger = logging.getLogger('mz_lps.views')

def learning_plan_view(request, careercourse_id):
    '''
    学生个人学习计划
    :param request:
    :param careercourse_id:
    :return:
    '''
    ################# 个人中心 -- 左边 开始  ########################
    user = request.user
    cur_careercourse = None    # 当前职业课程
    cur_stage = None       # 当前阶段
    cur_class = None       # 当前班级
    cur_careercourse_stage_list = []   # 当前职业课程阶段列表

    if not user.is_authenticated() or not user.is_student():
        return render(request, 'mz_common/failure.html',{'reason':'没有访问权限，请先登录。<a href="'+str(settings.SITE_URL)+'">返回首页</a>'})

    # 获取当前职业课程对象
    try:
        cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
        # 如果没有观看过视频，也没有传递stage_id过来，则默认跳到第一阶段
    except CareerCourse.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'没有该职业课程'})

    # 根据不同情况获取不同的支付金额
    cur_careercourse = get_real_amount(user, cur_careercourse)
    # 获取该职业课程下所有开放的班级
    cur_careercourse_class_list = cur_careercourse.class_set.filter(is_active=True, status=1)
    # 职业课程下是否有阶段解锁
    setattr(cur_careercourse, "is_unlockstage", False)
    # 职业课程学习计划天数
    setattr(cur_careercourse, "plan_days_count", 0)

    # 当前职业课程列表
    cur_careercourse_stage_list_temp = cur_careercourse.stage_set.all().order_by("index", "id")
    if len(cur_careercourse_stage_list_temp) == 0:
        return render(request, 'mz_common/failure.html',{'reason':'该课程还没有阶段信息'})
        # 查看用户解锁了哪些阶段，更改当前职业课程列表解锁信息
    user_careercourse_unlockstage_list = UserUnlockStage.objects.filter(user=user, stage__career_course=careercourse_id)
    for stage in cur_careercourse_stage_list_temp:
        # 给stage增加一个状态，0 加锁,1 已解锁,2 已完成，默认是0
        setattr(stage, "status", 0)
        for unlockstage in user_careercourse_unlockstage_list:
            if stage.id == unlockstage.stage.id:
                cur_careercourse.is_unlockstage = True
                stage.status = 1
                break
            #判断是否通过该阶段所有课程，通过则状态改为2
        cur_careercourse_stage_list.append(stage)

    # 获取当前正在看哪个学习阶段
    stage_id = request.GET.get("stage_id", None)
    if stage_id == None :
        recent_learned_lesson = UserLearningLesson.objects.filter(user=user, lesson__course__stages__career_course=careercourse_id).order_by("-date_learning")
        if recent_learned_lesson:
            cur_stage = Stage.objects.get(course__lesson=recent_learned_lesson[0].lesson)
        else:
            cur_stage = cur_careercourse_stage_list[0]
    else:
        cur_stage = Stage.objects.get(pk=stage_id)

    cur_stage_course_list = []
    # 获取当前阶段下面的所有课程
    cur_stage_course_list_temp = cur_stage.course_set.all().order_by("index", "id")
    if len(cur_stage_course_list_temp) == 0:
        return render(request, 'mz_common/failure.html',{'reason':'该阶段下还没有课程'})

    # 获取当前阶段所有课程-所有章节及其观看状态
    setattr(cur_stage, "is_unlockstage", False)   # 课程所属阶段是否已经解锁
    for course in cur_stage_course_list_temp:
        setattr(course, "lesson", [])   # 课程下章节列表
        setattr(course, "lesson_count", course.lesson_set.all().count())  # 课程下章节总数
        setattr(course, "lesson_has_exam_count", 0)  # 课程下有测验题的章节总数
        setattr(course, "lesson_has_homework_count", 0)  # 课程下有课后作业的章节总数
        setattr(course, "lesson_complete_count", 0)  # 已完成课程总数
        setattr(course, "homework_complete_count", 0)  # 已上传课后作业总数
        setattr(course, "lesson_exam_complete_count", 0)  # 已完成随堂测验总数
        setattr(course, "project", {"description": "", "upload_file": "", "score": 0,"setting_url":settings.SITE_URL+settings.MEDIA_URL,"remark":""})  # 项目需求描述
        setattr(course, "is_unlockstage", False)   # 课程所属阶段是否已经解锁
        setattr(course, "score", 0)         # 课程评测得分
        setattr(course, "is_complete", False)   # 是否完成该课程
        setattr(course, "rebuild_count", get_rebuild_count(user.id, course.id))   # 获取当前学生第几次重修
        setattr(course, "has_paper", False)  # 该课程是否已经出了试卷
        setattr(course, "is_complete_paper", False)  # 学生是否已经完成该试卷的课堂总测验
        setattr(course, "alllesson_is_complete_paper", True)  # 学生是否已经完成所有随堂测验
        setattr(course, "uncomplete_quiz", [])  # 该试卷下学生未做完的题目列表

        # 判断当前阶段是否已经解锁
        for unlockstage in user_careercourse_unlockstage_list:
            if cur_stage.id == unlockstage.stage.id:
                course.is_unlockstage = True
                cur_stage.is_unlockstage = True
                break

        # 获取课程总测验测试试卷和题目
        quiz_record_list = [] # 某个试卷下已经做过的试题列表
        paper = Paper.objects.filter(examine_type=2, relation_type=2, relation_id=course.id)
        if len(paper) > 0:
            course.has_paper = True
            # 已经做过的题目则不再显示
            course.uncomplete_quiz = get_uncomplete_quiz(user, paper, course.rebuild_count)
            if len(course.uncomplete_quiz)==0:
                course.is_complete_paper = True

        check_course_score(user, course) # 检查是否有course_score记录,没有则创建
        # 获取该课程是否完成，并计算当前得分
        course_score = CourseScore.objects.filter(user=user, course=course.id, rebuild_count=course.rebuild_count)
        if len(course_score) > 0 and cur_stage.is_unlockstage:
            if check_exam_is_complete(user, course) == 1:
                course.is_complete = True
            if course.is_complete:
                if course_score[0].lesson_score is None: course_score[0].lesson_score = 0
                if course_score[0].course_score is None: course_score[0].course_score = 0
                if course_score[0].project_score is None: course_score[0].project_score = 0
                course.score = get_course_score(course_score[0], course)   # 计算当前测验分得分

        # 检查是否完成项目考核作品上传
        project = Project.objects.filter(examine_type=5, relation_type=2, relation_id=course.id)
        if len(project) > 0:
            course.project["description"] = project[0].description
            project_record = ProjectRecord.objects.filter(project=project[0], student=user, rebuild_count=course.rebuild_count)
            if len(project_record) > 0:
                course.project["upload_file"] = project_record[0].upload_file
                course.project["score"] = project_record[0].score
                course.project["remark"] = project_record[0].remark

        for lesson in course.lesson_set.order_by("index", "id"):
            setattr(lesson, "is_complete", False)   # 是否完成章节学习
            setattr(lesson, "has_exam", False)   # 是否有测验题
            setattr(lesson, "has_homework", False)   # 是否有课后作业
            setattr(lesson, "is_complete_paper", False)  # 学生是否已经完成该试卷的测验
            learning_lesson = UserLearningLesson.objects.filter(user=user, lesson=lesson)
            if len(learning_lesson) > 0:
                lesson.is_complete = learning_lesson[0].is_complete
                if lesson.is_complete:
                    course.lesson_complete_count += 1

            setattr(lesson, "homework", "")         # 是否完成作业提交，下载地址不为空则表示作业已经提交
            # 获取当前课程的Homework信息
            homework = Homework.objects.filter(examine_type=1, relation_type=1, relation_id=lesson.id)
            if len(homework) > 0:
                lesson.has_homework = True
                course.lesson_has_homework_count+=1
                # homework_record = HomeworkRecord.objects.filter(homework=homework[0], student=user,rebuild_count=course.rebuild_count)
                # 后续需求改动，重修后课后作业不需要再上传
                homework_record = HomeworkRecord.objects.filter(homework=homework[0], student=user)
                if len(homework_record) > 0:
                    lesson.homework = homework_record[0].upload_file
                    course.homework_complete_count += 1

            setattr(lesson, "exam_accuracy", None)         # 随堂测验准确率
            # 获取当前课程的随堂测验信息
            paper = Paper.objects.filter(examine_type=2, relation_type=1, relation_id=lesson.id)
            if len(paper) > 0:
                lesson.has_exam = True
                course.lesson_has_exam_count+=1
                quiz_count = Quiz.objects.filter(paper=paper).count() #试卷拥有的题目数量
                paper_record = PaperRecord.objects.filter(Q(paper=paper[0]),Q(student=user),Q(rebuild_count=course.rebuild_count),~Q(score=None)) #试卷对应考核记录
                if len(paper_record) > 0:
                    quizrecord_count = QuizRecord.objects.filter(paper_record=paper_record).count() # 学生已做的试题数量
                    if quiz_count > quizrecord_count:
                        lesson.is_complete_paper = False
                        course.alllesson_is_complete_paper = False
                    elif quiz_count == quizrecord_count:
                        lesson.is_complete_paper = True
                        if paper_record[0].accuracy is not None:
                            lesson.exam_accuracy = str(int(paper_record[0].accuracy * 100)) + "%"
                            course.lesson_exam_complete_count += 1
                else:
                    lesson.is_complete_paper = False
                    course.alllesson_is_complete_paper = False
            course.lesson.append(lesson)
        cur_stage_course_list.append(course)

        #获取当前阶段下班级对应的老师的人工任务列表
        mission_list = []
        mission_list_count = 0
        mission_list_complete_count = 0
        mission_list_score = 0
        try:
            cur_class = ClassStudents.objects.filter(user=user, student_class__career_course=cur_careercourse)
            if cur_class.count() > 0:
                cur_class = cur_class[0]
                mission_list_tmp = Mission.objects.filter(teacher=cur_class.teacher, examine_type=4, relation_type=3, relation_id=cur_stage.id)
                if len(mission_list_tmp) > 0:
                    for i, mission in enumerate(mission_list_tmp):
                        setattr(mission, "is_complete", False)   # 学生是否已做该人工任务
                        setattr(mission, "is_odd", False)  # 当前是否是奇数条数据
                        mission_record = MissionRecord.objects.filter(student=user, mission=mission)
                        if len(mission_record) > 0:
                            mission.is_complete = True
                            mission_list_score = mission_list_score + mission_record[0].score
                            mission_list_complete_count += 1
                        if (i+1)%2 == 1:
                            mission.is_odd = True
                        mission_list.append(mission)
                        if (i+1) == len(mission_list_tmp):
                            mission_list_score = int(mission_list_score / (i+1))
                            mission_list_count = (i+1)
        except Exception,e:
            logger.error(e)

    ################# 个人中心 -- 左边 结束  ########################

    ################# 个人中心 -- 右边 开始  ########################
    #调用当前学力
    ret = current_study_point(cur_careercourse, user)
    if ret !='NotSignUp':
        #调用学力排行
        curren_all_stu =  all_stu_ranking(cur_careercourse, user)
        for i,cu in enumerate(curren_all_stu):
            setattr(cu, "rankid", i+1)
        all_stu_page = []
        for i in range(0,len(curren_all_stu),settings.RANKING_PAGESIZE):
            all_stu_page.append(curren_all_stu[i:i+settings.RANKING_PAGESIZE])
        #获取用户当前排名
        rank =  current_user_ranking(cur_careercourse, user)
    ################# 个人中心 -- 右边 结束  ########################

    ################# 个人中心 -- 上边图表 开始  ########################
    # 检查学生是否设置过学习计划
    setattr(cur_careercourse, "is_set_plan", False)  # 是否设置过计划
    setattr(cur_careercourse, "is_pause", False)  # 是否请假且还未恢复学习，暂停状态
    setattr(cur_careercourse, "stages_list", [])  # 职业课程下阶段列表
    chart_data = [] #图表所需数据

    # 如果购买了课程
    if cur_careercourse.is_unlockstage:
        # 获取职业课程下所有阶段和课程
        for stage in cur_careercourse.stage_set.all():
            setattr(stage, "courses_list", [])  # 阶段下的课程列表
            stage.courses_list = Course.objects.filter(stages=stage).order_by("index", "id")
            cur_careercourse.stages_list.append(stage)

    planning = Planning.objects.filter(user=user, career_course=cur_careercourse, is_active=True).order_by("version","date_publish")
    if len(planning) > 0:
        planning = planning[0]
        cur_careercourse.is_set_plan = True
        planning_pause = PlanningPause.objects.filter(planning=planning).order_by("-id")
        if len(planning_pause) > 0:
            if planning_pause[0].restore_date == None :
                    cur_careercourse.is_pause = True
        before_cur_course_need_days_total = 0 #在课程之前已经累计了多少天其他的课程计划时间
        # 获取所有的计划项
        for i,stage in enumerate(cur_careercourse.stages_list):
            for j,course in enumerate(stage.courses_list):
                setattr(course, "start_date", None)  # 课程开始学习具体时间
                setattr(course, "end_date", None)  # 课程结束学习具体时间
                setattr(course, "is_rest", None)  # 课程是否有请假情况
                # 获取每个节点上应该显示的数据和比例,默认假设都未进行重修，取rebuild_count=0的相关数据
                node_data = get_learning_progress_rate(user, course, 0)
                node_data_msg = get_node_data_msg(node_data)
                # 查找对应课程计划项
                planning_item = PlanningItem.objects.filter(planning=planning,course=course)
                if len(planning_item) > 0:
                    course.need_days = planning_item[0].need_days
                if course.need_days <= 0: course.need_days = 1                # 获取职业课程学习计划天数
                cur_careercourse.plan_days_count += course.need_days
                # 计算该课程开始学习和结束学习的时间
                course.start_date = planning.date_publish + timedelta(before_cur_course_need_days_total)
                course.end_date = course.start_date + timedelta(course.need_days)
                # 知道了课程开始学习和结束学习的具体时间，则获取该课程学习计划期间是否有请假的记录
                planning_pause = PlanningPause.objects.filter(Q(planning=planning),
                                                              Q(pause_date__lt=course.end_date),
                                                              Q(pause_date__gt=course.start_date),
                                                              ~Q(restore_date=None)).order_by("id")
                if len(planning_pause) > 0:
                    # 获取请假记录的开始时间和结束时间
                    rest_days_total = 0  #记录这段时间总共请假的天数
                    for k,pause in enumerate(planning_pause):
                        # 判断请假时间是否超过一天，未超过一天的忽略不计
                        if (pause.restore_date - pause.pause_date).days < 1:
                            continue
                        # 计划当前累计到的时间
                        cur_planning_date = planning.date_publish + timedelta(before_cur_course_need_days_total)
                        course.is_rest = True

                        actual_learning_days = (pause.pause_date - cur_planning_date).days
                        if actual_learning_days <= 0: actual_learning_days = 1
                        before_cur_course_need_days_total += actual_learning_days
                        chart_data.append({ "process": "阶段"+str(i+1),
                                            "iclass": "第"+str(j+1)+"课",
                                            "state": "on",
                                            "rank": node_data["rate"],
                                            "msg": node_data_msg,
                                            "need_days": actual_learning_days,
                                            "cur_date": planning.date_publish + timedelta(before_cur_course_need_days_total),
                                            "course_id": course.id})

                        rest_days = (pause.restore_date - pause.pause_date).days  # 休息天数
                        if rest_days <= 0: rest_days = 1
                        before_cur_course_need_days_total += rest_days
                        rest_days_total += rest_days
                        chart_data.append({ "process": "阶段"+str(i+1),
                                            "iclass": "第"+str(j+1)+"课",
                                            "state": "rest",
                                            "rank": node_data["rate"],
                                            "msg": "['"+pause.reason+"']",
                                            "need_days": rest_days,
                                            "cur_date": planning.date_publish + timedelta(before_cur_course_need_days_total),
                                            "course_id": course.id})

                        if (k+1) == len(planning_pause):
                            cur_planning_date = planning.date_publish + timedelta(before_cur_course_need_days_total)
                            # 该课程实际还剩下的天数
                            actual_learning_days = (course.end_date - cur_planning_date).days + rest_days_total
                            if actual_learning_days <= 0: actual_learning_days = 1
                            before_cur_course_need_days_total += actual_learning_days
                            chart_data.append({ "process": "阶段"+str(i+1),
                                                "iclass": "第"+str(j+1)+"课",
                                                "state": "on",
                                                "rank": node_data["rate"],
                                                "msg": node_data_msg,
                                                "need_days": actual_learning_days,
                                                "cur_date": planning.date_publish + timedelta(before_cur_course_need_days_total),
                                                "course_id": course.id})

                # 如果课程学习过程中没有请假的情况，累加总时间并添加相应的图表节点
                if not course.is_rest:
                    before_cur_course_need_days_total += course.need_days
                    chart_data.append({ "process": "阶段"+str(i+1),
                                        "iclass": "第"+str(j+1)+"课",
                                        "state": "on",
                                        "rank": node_data["rate"],
                                        "msg": node_data_msg,
                                        "need_days": course.need_days,
                                        "cur_date": planning.date_publish + timedelta(before_cur_course_need_days_total),
                                        "course_id": course.id})

        # 超出学习计划的score记录列表
        over_plan_score_tmp=[]
        # 超出学习计划的score记录对应stage名列表
        over_plan_score_stage = []
        # 超出学习计划的score记录对应的course列表
        over_plan_score_course = []
        # 获取该课程是否有挂科和重修记录,并根据记录插入到时间主线的Chat_data
        for i,stage in enumerate(cur_careercourse.stages_list):
            for j,course in enumerate(stage.courses_list):
                course_score = CourseScore.objects.filter(course=course, user=user).order_by("rebuild_count")
                if len(course_score) > 0:
                    for score in course_score:
                        if score.rebuild_count > 0:
                            node_data = get_learning_progress_rate(user, course, score.rebuild_count)
                            # 如果没有通过考核
                            # 从chart_data比较，更新chart_data数

                            # 记录当次循环是否插入了新的节点
                            is_insert_new_node = False
                            # 某一门课程非第一次挂科情况
                            before_chart = None
                            for m,chart in enumerate(chart_data):
                                if m == 0: before_chart = chart
                                # 如果不是首次挂科，则要根据重修创建的时间状态找到对应的插入位置，并需要更新该节点后面的时间
                                if chart["cur_date"] >= score.date_publish and not is_insert_new_node and chart["state"] != "rest":
                                    # 在chart当前节点前插入一个新的节点
                                    # 如果是课程已经处于完成状态，则属于挂科状态
                                    if score.is_complete and get_course_score(score, course) < 60:
                                        node_data_msg = get_node_data_msg(node_data,"off")
                                        chart_data.insert(m, {"process": "阶段"+str(i+1),
                                                               "iclass": "第"+str(j+1)+"课",
                                                                "state": "off",
                                                                "rank": node_data["rate"],
                                                                "msg":node_data_msg,
                                                                "need_days": course.need_days,
                                                                "cur_date": before_chart["cur_date"]+timedelta(course.need_days),
                                                                "course_id": course.id})
                                    if get_course_score(score, course) >= 60 or not score.is_complete:
                                        # 凡是分数大于了60，或者是is_complete不为True时，表示还在重修的状态
                                        # 没有处于完成状态，且rebuild_count不为0，则为重修状态
                                        node_data_msg = get_node_data_msg(node_data)
                                        chart_data.insert(m, {"process": "阶段"+str(i+1),
                                                              "iclass": "第"+str(j+1)+"课",
                                                              "state": "reset",
                                                              "rank": node_data["rate"],
                                                              "msg": node_data_msg,
                                                              "need_days": course.need_days,
                                                              "cur_date": before_chart["cur_date"]+timedelta(course.need_days),
                                                              "course_id": course.id})
                                    is_insert_new_node = True # 标记插入了新的节点
                                    before_cur_course_need_days_total += course.need_days  # 更新时间轴总线
                                    before_chart = chart
                                    continue
                                if is_insert_new_node and chart["state"] != "rest":
                                    # 更新新节点之后的所有节点的日期往后推相应天数
                                    chart["cur_date"] += timedelta(course.need_days)

                                before_chart = chart

                            # 如果是已经超出了图表计划的正常的时间进行重修，则将重修的内容加到最后成为独立的点
                            # 先加入over_plan_score_tmp列表
                            if score.date_publish > before_chart["cur_date"]:
                                over_plan_score_tmp.append(score.id)
                                over_plan_score_stage.append(i+1)
                                over_plan_score_course.append(j+1)
                        else:
                            # 某一门课程第一次挂科情况，直接修改已有课程节点为off并更新msg
                            if score.is_complete and get_course_score(score, course) < 60:
                                for chart in chart_data:
                                    if chart["course_id"] == course.id and chart["state"] == "on":
                                        chart["state"] = "off"
                                        if chart["msg"].find('章节测验') > -1:
                                            chart["msg"] = "['章"+re.compile(r"\['视频观看：[^\\]*\,'章").sub("", chart["msg"])
                                        elif chart["msg"].find('课程测验') > -1:
                                            chart["msg"] = "['课"+re.compile(r"\['视频观看：[^\\]*\,'课").sub("", chart["msg"])
                                        elif chart["msg"].find('项目制作') > -1:
                                            chart["msg"] = "['项"+re.compile(r"\['视频观看：[^\\]*\,'项").sub("", chart["msg"])

        # 对over_plan_score_tmp里面的值按时间进行升序排序，并追加值到chart_data
        if len(over_plan_score_tmp) > 0:
            over_plan_score = CourseScore.objects.filter(id__in=over_plan_score_tmp).order_by("date_publish")
            before_over_score = 0
            for n,over_score in enumerate(over_plan_score):
                # 课程对象
                course = over_score.course
                planning_item = PlanningItem.objects.filter(planning=planning,course=course)
                if len(planning_item) > 0:
                    course.need_days = planning_item[0].need_days  # 实际计划学习天数
                # 图表最后一个项
                chart_end_item = chart_data[len(chart_data)-1]
                temp_need_days = (over_score.date_publish - chart_end_item["cur_date"]).days
                if temp_need_days > 0:
                    need_days = (over_score.date_publish - chart_end_item["cur_date"]).days + course.need_days
                else:
                    need_days = course.need_days
                # 时间轴线总计数
                before_cur_course_need_days_total += need_days
                # 判断是重修还是挂科
                node_data = get_learning_progress_rate(user, course, over_score.rebuild_count)
                if over_score.is_complete and get_course_score(over_score, course) < 60:
                    # 重修再挂科
                    chart_item_status = "off"
                    node_data_msg = get_node_data_msg(node_data,"off")
                else:
                    chart_item_status = "reset"
                    node_data_msg = get_node_data_msg(node_data)
                chart_data.append({"process": "阶段"+str(over_plan_score_stage[n]),
                                   "iclass": "第"+str(over_plan_score_course[n])+"课",
                                   "state": chart_item_status,
                                   "rank": node_data["rate"],
                                   "msg": node_data_msg,
                                   "need_days": need_days,
                                   "cur_date": planning.date_publish + timedelta(before_cur_course_need_days_total),
                                   "course_id": course.id})

                before_over_score = over_score

    ################# 个人中心 -- 上边图表 结束  ########################

    ################ 直播室 开始  #################################
    live_room = None
    try:
        if cur_class is not None and cur_careercourse.is_unlockstage:
            live_room = LiveRoom.objects.get(live_class=cur_class.student_class)
    except Exception as e:
        logger.error(e)
    ################ 直播室 结束  #################################
    return render(request, 'mz_lps/learning_plan.html',locals())

# 获取图标节点应该显示的msg
def get_node_data_msg(node_data, state="on"):
    node_data_msg = "["
    # 如果是挂科状态
    if state != "off" and node_data["lesson_count"] !=0:
        node_data_msg += "'视频观看："+str(node_data["learning_lesson_count"])+"/"+str(node_data["lesson_count"])+"',"
    if node_data["lesson_exam_count"] !=0:
        node_data_msg += "'章节测验："+str(node_data["learning_lesson_exam_count"])+"/"+str(node_data["lesson_exam_count"])+"',"
    if node_data["course_exam_count"] !=0:
        node_data_msg += "'课程测验："+str(node_data["learning_course_exam_count"])+"/"+str(node_data["course_exam_count"])+"',"
    if node_data["project_exam_count"] !=0:
        node_data_msg += "'项目制作："+str(node_data["learning_project_exam_count"])+"/"+str(node_data["project_exam_count"])+"'"
    node_data_msg += "]"
    return node_data_msg

# 获取学习进度和比列
def get_learning_progress_rate(user, course, rebuild_count=None):

    # 如果为空则查询当前的rebuild_count
    if rebuild_count is None:
        rebuild_count = get_rebuild_count(user, course)

    # 获取课程下所有lesson id列表
    lesson_id_list = course.lesson_set.all().values_list("id")
    # 视频完成数目/实际数目
    lesson_count = len(lesson_id_list)
    learning_lesson_count = UserLearningLesson.objects.filter(user=user, lesson__course=course, is_complete=True).count()
    # 已完成随堂测验/随堂测验总数
    paper_id_list = Paper.objects.filter(examine_type=2, relation_type=1, relation_id__in=lesson_id_list).values_list("id")
    lesson_exam_count = len(paper_id_list)
    learning_lesson_exam_count = PaperRecord.objects.filter(paper__in=paper_id_list, student=user, rebuild_count=rebuild_count).count()
    # 课程测验
    course_exam_count = 0
    learning_course_exam_count = 0
    paper_id_list = Paper.objects.filter(examine_type=2, relation_type=2, relation_id=course.id).values_list("id")
    if len(paper_id_list) > 0 and course.has_examine:
        course_exam_count = 1
        if PaperRecord.objects.filter(paper__in=paper_id_list, student=user, rebuild_count=rebuild_count).count() > 0:
            learning_course_exam_count = 1
    # 项目制作
    project_exam_count = 0
    learning_project_exam_count = 0
    project_id_list = Project.objects.filter(examine_type=5, relation_type=2, relation_id=course.id).values_list("id")
    if len(project_id_list) > 0 and course.has_project:
        project_exam_count = 1
        if ProjectRecord.objects.filter(project__in=project_id_list, student=user, rebuild_count=rebuild_count).count() > 0:
            learning_project_exam_count = 1

    # 计算rank
    count = lesson_count + lesson_exam_count + course_exam_count + project_exam_count
    learning_count = learning_lesson_count + learning_lesson_exam_count + learning_course_exam_count + learning_project_exam_count
    if count != 0:
        rate = int(round(learning_count / count, 2) * 100)
    else:
        rate = 100

    return {"rate": rate, "lesson_count":lesson_count, "learning_lesson_count":learning_lesson_count,
            "lesson_exam_count":lesson_exam_count, "learning_lesson_exam_count":learning_lesson_exam_count,
            "course_exam_count":course_exam_count, "learning_course_exam_count":learning_course_exam_count,
            "project_exam_count":project_exam_count, "learning_project_exam_count":learning_project_exam_count}

# 恢复学习
def learning_restore(request, careercourse_id):
    try:
        cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
    except CareerCourse.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"不存在该职业课程"}', content_type="application/json")
    planning = Planning.objects.filter(user=request.user, career_course=cur_careercourse, is_active=True).order_by("version","date_publish")
    if len(planning) > 0:
        planning_pause = PlanningPause.objects.filter(planning=planning[0]).order_by("-id")
        if len(planning_pause) > 0:
            planning_pause[0].restore_date = datetime.now()
            planning_pause[0].save()
            return HttpResponse('{"status":"success","message":"学习恢复成功"}', content_type="application/json")
    return HttpResponse('{"status":"failure","message":"学习恢复失败"}', content_type="application/json")

# 获取所有课程是否是新手课程的信息
def get_all_course_novice_info(request, careercourse_id):
    try:
        cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
    except CareerCourse.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"不存在该职业课程"}', content_type="application/json")
    courses = Course.objects.filter(stages__career_course=cur_careercourse).order_by("index", "id")
    courses = [{"id": course.id,
                "is_novice": course.is_novice} for course in courses]
    return HttpResponse(json.dumps(courses),content_type="application/json")

# 生成学习计划
@csrf_exempt
def build_learning_plan(request, careercourse_id):
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="application/json")
    # 获取该职业课程下有哪些课程
    try:
        cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
        # 判断学生是否有购买某个职业课程
        if UserUnlockStage.objects.filter(user=request.user, stage__career_course=cur_careercourse).count() == 0:
            return HttpResponse('{"status":"failure","message":"还未购买该课程，不能生成学习计划"}', content_type="application/json")
    except CareerCourse.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"不存在该职业课程"}', content_type="application/json")
    try:
        planning = Planning.objects.filter(user=request.user, career_course=cur_careercourse).order_by("-version","-id")
        if len(planning) == 0:
            planning = Planning()
            planning.user = request.user
            planning.career_course = cur_careercourse
            planning.save()
        else:
            planning = planning[0]
        all_course_list = Course.objects.filter(stages__career_course=cur_careercourse)
        # 获取用户提交的选择数据
        for course in all_course_list:
            cur_select = request.POST.get("iCheck_"+str(course.id),None) # 用户选择项
            need_days = course.need_days
            if cur_select == "know":
                need_days = course.need_days_base
            planning_item = PlanningItem()
            planning_item.planning = planning
            planning_item.course = course
            planning_item.need_days = need_days
            planning_item.save()
    except Exception,e:
        logger.error(e)
        return HttpResponse('{"status":"failure","message":"发生异常"}', content_type="application/json")
    return HttpResponse('{"status":"success","message":"学习计划生成成功"}', content_type="application/json")

#项目提交
@csrf_exempt
def project_upload(request):
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="text/plain")
    ret="0"
    course_id = request.POST['course_id']
    files = request.FILES.get("Filedata_"+str(course_id),None)
    try:
        cur_course = Course.objects.get(pk=course_id)
        # 判断学生是否有购买某个阶段
        if UserUnlockStage.objects.filter(user=request.user, stage=cur_course.stages).count() == 0:
            return HttpResponse('{"status":"failure","message":"还未购买该阶段，不能上传项目"}', content_type="application/json")
    except Course.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"没有该课程"}', content_type="application/json")
    except Exception,e:
        logger.error(e)
    if files:
        result =file_upload(files, 'project')
        if result[0] == True:
            project = Project() # 项目考核对象
            project_record = ProjectRecord()  # 项目上传记录对象
            rebuild_count = get_rebuild_count(request.user.id, course_id)  # 重修次数
            try:
                project = Project.objects.get(examine_type=5, relation_type=2, relation_id=course_id)
                # 如果已经上传，先删除对应的文件后再执行更新操作
                project_record = ProjectRecord.objects.get(project=project, student=request.user, rebuild_count=rebuild_count)
                project_record_path = os.path.join(settings.MEDIA_ROOT)+"/"+str(project_record.upload_file)
                if os.path.exists(project_record_path) :
                    os.remove(project_record_path)
                project_record.upload_file = result[2]
                project_record.save()
            except Project.DoesNotExist :
                ret='{"status":"failure","message":"保存失败"}'
            except ProjectRecord.DoesNotExist:
                try:
                    project_record.upload_file = result[2]
                    project_record.student = request.user
                    project_record.examine_id = project.examine_ptr_id
                    project_record.project = project
                    project_record.rebuild_count = rebuild_count
                    project_record.save()
                    # 首次上传时加10学力
                    update_study_point_score(request.user, 10, examine=project, examine_record=project_record)
                except Exception as e:
                    logger.error(e)
            except Exception as e:
                logger.error(e)

            try:
                #### 给对应带班老师推送消息 开始 ####
                # 获取班级信息
                class_student = ClassStudents.objects.get(user=request.user, student_class__career_course=cur_course.stages.career_course)
                # 获取该职业课程老师班级下的所有学员
                alert_msg = str(request.user.nick_name)+"已上传了"+str(cur_course.name)+\
                            "课程的项目制作，<a href='"+str(settings.SITE_URL)+"/lps/user/teacher/class_manage/"+str(class_student.student_class.id)+\
                            "/"+str(request.user.id)+"/'>赶快去看看吧</a>！"
                sys_send_message(0,class_student.student_class.teacher.id,1,alert_msg)

                alert_msg = str(request.user.nick_name)+"已上传了"+str(cur_course.name)+"课程的项目制作，赶快去看看吧！"
                app_send_message("系统消息", alert_msg, [class_student.student_class.teacher.token])
                #### 给对应带班老师推送消息 结束 ####
            except Exception as e:
                logger.error(e)
            ret='{"status":"success","message":"'+str(result[1])+'","pro_url":"'+settings.SITE_URL+settings.MEDIA_URL+str(result[2])+'"}'
            return HttpResponse(ret, content_type="text/plain")
        else:
            ret='{"status":"failure","message":"'+str(result[1])+'"}'
    return HttpResponse(ret, content_type="text/plain")

# 课程重修
def rebuild_course(request, course_id):
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="application/json")

    try:
        cur_course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"不存在该课程"}', content_type="application/json")

    try:
        # 检查请求课程是否需要重修
        course_score = CourseScore.objects.filter(user=request.user, course=cur_course).order_by("-rebuild_count")
        if len(course_score) > 0:
            if check_exam_is_complete(request.user, cur_course) == 1:
                is_complete = True
            else:
                is_complete = False
            if not is_complete or get_course_score(course_score[0], cur_course)>=60:
               return HttpResponse('{"status":"failure","message":"该课程不满足重修的条件"}', content_type="application/json")
        else:
            return HttpResponse('{"status":"failure","message":"查不到该学生的学分记录"}', content_type="application/json")
        # 需要重修
        # 1、插入一条新的重修记录
        course_score = CourseScore()
        course_score.user = request.user
        course_score.course = cur_course
        course_score.rebuild_count = get_rebuild_count(request.user, cur_course) + 1
        course_score.save()
        # 2、设置对应的课程视频播放记录为未完成状态
        # UserLearningLesson.objects.filter(user=request.user, lesson__course=cur_course).update(is_complete=False)
    except Exception,e:
        logger.error(e)
        return HttpResponse('{"status":"failure","message":"发生异常，请联系管理员"}', content_type="application/json")
    return HttpResponse('{"status":"success","message":"课程初始化成功，可以开始重新学习"}', content_type="application/json")

# 回答试题验证
def answer_quiz(request, quiz_id, select):
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="application/json")

    try:
        cur_quiz = Quiz.objects.get(pk=quiz_id)
        cur_paper = cur_quiz.paper
        user = request.user
    except Quiz.DoesNotExist:
        return HttpResponse('{"status":"failure","message":"没有该试题"}', content_type="application/json")
    # 获取到course对象
    try:
        if cur_paper.relation_type == 1:
            # 章节
            cur_course = Lesson.objects.get(pk=cur_paper.relation_id).course
        elif cur_paper.relation_type == 2:
            # 课程
            cur_course = Course.objects.get(pk=cur_paper.relation_id)
    except Exception as e:
        logger.error(e)
    # 检查用户是否做过该题
    rebuild_count = get_rebuild_count(user, cur_course)
    if QuizRecord.objects.filter(paper_record__student=user, quiz=cur_quiz, paper_record__rebuild_count=rebuild_count).count() > 0:
        return HttpResponse('{"status":"failure","message":"用户已经做过该试题"}', content_type="application/json")
    # 生成做题记录
    # 查询是否有paper_record的记录，如果没有则生成一条新的paper_record记录
    paper_record = PaperRecord.objects.filter(paper=cur_paper, student=user, rebuild_count=rebuild_count)
    if len(paper_record)>0:
        paper_record = paper_record[0]
    else:
        paper_record = PaperRecord()
        paper_record.paper = cur_paper
        paper_record.examine_id = cur_paper.examine_ptr_id
        paper_record.score = 0
        paper_record.study_point = 0
        paper_record.student = user
        paper_record.rebuild_count = rebuild_count
        paper_record.save()

    quiz_record = QuizRecord()
    quiz_record.quiz = cur_quiz
    quiz_record.result = select
    quiz_record.paper_record = paper_record
    quiz_record.save()

    # 如果已经完成所有测验试题
    if len(get_uncomplete_quiz(user, cur_paper, rebuild_count)) == 0:
        # 计算试卷准确率并更新
        # 获取所有答题记录
        quiz_record_list = QuizRecord.objects.filter(paper_record__student=user, quiz__paper=cur_paper, paper_record__rebuild_count=rebuild_count)
        quiz_right_count = 0
        for quiz_record in quiz_record_list:
            if quiz_record.quiz.result.lower() == quiz_record.result.lower():
                quiz_right_count += 1
        #该试卷下的总题数
        quiz_all_count = Quiz.objects.filter(paper=cur_paper).count()
        paper_accuracy = round(quiz_right_count / quiz_all_count, 2)
        paper_score = 100 * paper_accuracy
        paper_record.accuracy = paper_accuracy
        paper_record.save()

        # 在考核记录中更新学力和测验分
        paper_study_point = 0
        if cur_paper.relation_type == 1:
            paper_study_point = 1
        elif cur_paper.relation_type == 2:
            paper_study_point = 10
        update_study_point_score(user, paper_study_point, paper_score, cur_paper, paper_record, None, rebuild_count)
    return HttpResponse('{"status":"success","message":"答题成功","result":"'+cur_quiz.result+'"}', content_type="application/json")

# 获得某个试卷的测验结果
def get_paper_result(request,type,type_id):
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="application/json")

    try:
        if type == "course":
            cur_course = Course.objects.get(pk=type_id)
            cur_paper = Paper.objects.get(examine_type=2,relation_type=2,relation_id=type_id)
        elif type == "lesson":
            cur_course = Lesson.objects.get(pk=type_id).course
            cur_paper = Paper.objects.get(examine_type=2,relation_type=1,relation_id=type_id)
        else:
            return HttpResponse('{"status":"failure","message":"未知的测试类型"}', content_type="application/json")
    except Exception, e:
        logger.error(e)
        return HttpResponse('{"status":"failure","message":"发生异常"}', content_type="application/json")

    rebuild_count = get_rebuild_count(request.user, cur_course)
    quiz_record_list = QuizRecord.objects.filter(paper_record__student=request.user, quiz__paper=cur_paper, paper_record__rebuild_count=rebuild_count)
    quiz_right_count = 0  # 答对题数
    for quiz_record in quiz_record_list:
        if quiz_record.quiz.result.lower() == quiz_record.result.lower():
            quiz_right_count += 1

    #该试卷下的总题数
    quiz_all_count = Quiz.objects.filter(paper=cur_paper).count()

    # 试卷正确率
    paper_accuracy = str(int(round(quiz_right_count / quiz_all_count, 2)*100))+"%"

    return HttpResponse('{"status":"success","quiz_right_count":"'+str(quiz_right_count)+'","quiz_wrong_count":"'+str(quiz_all_count-quiz_right_count)+'","paper_accuracy":"'+str(paper_accuracy)+'","study_point":"'+str(quiz_all_count)+'"}', content_type="application/json")


class GeneralException(Exception):
    pass


def get_review_answer(request):
    user = request.user
    lesson_id = request.REQUEST.get('lesson_id')
    course_id = request.REQUEST.get('course_id')
    response = {
        'message': '未知错误',
        'success': False,
        'quizs': []
    }
    try:

        if not user:
            raise GeneralException('必须要登录')

        if lesson_id:
            #随堂测验
            try:
                lesson = Lesson.objects.get(pk=lesson_id)
            except Lesson.DoesNotExist:
                raise GeneralException('没有对应的章节')

            course = lesson.course

            try:
                paper = Paper.objects.get(examine_type=2, relation_type=1, relation_id=lesson_id)
            except Paper.DoesNotExist:
                raise GeneralException('没有随堂测验')

            rebuild_count = get_rebuild_count(user, course)

            try:
                paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, paper=paper, student=user)
                records = QuizRecord.objects.filter(paper_record=paper_record)
                completed_quiz = {record.quiz_id: record.result for record in records}
            except PaperRecord.DoesNotExist:
                completed_quiz = {}
            quizs = Quiz.objects.filter(paper=paper)

            for quiz in quizs:
                if quiz.id in completed_quiz and completed_quiz[quiz.id] != quiz.result:
                    response['quizs'].append({
                        'id': quiz.id,
                        'course_id': course.id,
                        'item_list': quiz.item_list,
                        'question': quiz.question,
                        'wrong': completed_quiz[quiz.id],
                        'right': quiz.result
                    })

            response['message'] = '提取成功'
            response['success'] = True


        elif course_id:
            #课程总测验
            try:
                course = Course.objects.get(pk=course_id)
            except Course.DoesNotExist:
                raise GeneralException('没有对应的课程')

            try:
                paper = Paper.objects.get(examine_type=2, relation_type=2, relation_id=course_id)
            except Paper.DoesNotExist:
                raise GeneralException('没有课程总测验')

            rebuild_count = get_rebuild_count(user, course)

            try:
                paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, paper=paper, student=user)
                records = QuizRecord.objects.filter(paper_record=paper_record)
                completed_quiz = {record.quiz_id: record.result for record in records}
            except PaperRecord.DoesNotExist:
                completed_quiz = {}
            quizs = Quiz.objects.filter(paper=paper)

            for quiz in quizs:
                if quiz.id in completed_quiz and completed_quiz[quiz.id] != quiz.result:
                    response['quizs'].append({
                        'id': quiz.id,
                        'course_id': course_id,
                        'item_list': quiz.item_list,
                        'question': quiz.question,
                        'wrong': completed_quiz[quiz.id],
                        'right': quiz.result
                    })

            response['message'] = '提取成功'
            response['success'] = True

    except GeneralException as e:
        response['message'] = e.message

    except Exception as e:
        response['message'] = e.message
        logger.error(e)

    return HttpResponse(json.dumps(response), content_type="application/json")
