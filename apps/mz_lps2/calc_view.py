__author__ = 'Steven'
from django.shortcuts import render
from django.http import HttpResponse,HttpResponsePermanentRedirect,HttpResponseRedirect
from django.db.models import Sum
from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger
from django.core.paginator import EmptyPage
from django.contrib.auth.models import Group
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.db.models import Q
from mz_common.models import *
from mz_user.forms import *
from mz_course.models import *
from mz_lps.models import *
from utils.tool import upload_generation_dir
from utils import xinge
import json, logging, os, uuid,urllib2,urllib
from itertools import chain
# from mz_async.models import *
from mz_user.models import *
from mz_common.views import *
import time
from models import CourseUserTask


logger = logging.getLogger('mz_lps2.calc_views')
#后台计算

def update_study_point_score(student, study_point=None, score=None, examine=None, examine_record=None, teacher=None, course=None, rebuild_count=None):
    '''
    更新学力和测验分
    :param student: 学生对象
    :param study_point: 学力加分（可选项）
    :param score: 测验分加分（可选项）
    :param examine: 考核对象（可选项）
    :param examine_record: 考核记录对象（可选项）
    :param teacher: 老师对象（可选项）
    :param course: 课程（可选项）,更新非考核产生的学力和学分时候需传入
    :param rebuild_count: 第几次重修（可选项）
    :return:
    '''

    if course is None:
        cur_course = Course()
    else:
        cur_course = course
        # 根据考核对象类型找到相应对象
    # 章节
    if examine is not None and examine_record is not None:
        if examine.relation_type == 1:
            cur_lesson = Lesson.objects.filter(pk=examine.relation_id)
            if len(cur_lesson) > 0:
                cur_course = cur_lesson[0].course
        #课程
        elif examine.relation_type == 2:
            cur_course = Course.objects.filter(pk=examine.relation_id)
            if len(cur_course)  > 0:
                cur_course = cur_course[0]

        if rebuild_count is None:
            rebuild_count = get_rebuild_count(student, cur_course)

        # 更新考核记录学力
        if score is not None:
            examine_record.score = score  # 计算该试卷测验得分
            if teacher is not None:
                examine_record.teacher = teacher
        if study_point is not None:
            examine_record.study_point = study_point   # 学力
        examine_record.save()

        # 在coursescore中更新测验分
        check_course_score(student, cur_course) # 检查是否有course_score记录,没有则创建
        if examine.examine_type in(2,5) and score is not None:
            course_score = CourseScore.objects.filter(user=student,course=cur_course,rebuild_count=rebuild_count)
            if len(course_score):
                # 考试测验
                # 试卷类型测验分
                if examine.examine_type == 2:
                    # 随堂测验
                    if examine.relation_type == 1:
                        # 获取所有章节id列表
                        lesson_list = cur_course.lesson_set.all().values_list("id")
                        lesson_total_score = 0
                        # 获取所有章节对应的paper
                        paper_list = Paper.objects.filter(examine_type=2, relation_type=1, relation_id__in=lesson_list).values_list("id")
                        # 获取所有章节对应的paperrecord
                        paper_record_list = PaperRecord.objects.filter(Q(student=student),Q(paper__in=paper_list),Q(rebuild_count=rebuild_count),~Q(score=None))
                        # 计算随堂测验总分
                        for paper_record in paper_record_list:
                            lesson_total_score += (100 / len(paper_list)) * paper_record.accuracy
                        course_score[0].lesson_score = int(round(lesson_total_score))
                    # 课程总测验
                    elif examine.relation_type == 2:
                        course_score[0].course_score = score
                # 项目类型测验分
                elif examine.examine_type == 5:
                    course_score[0].project_score = score
                    # 检查测验分考核项是否已经完全考核
                if check_exam_is_complete(student, cur_course) == 1:
                    course_score[0].is_complete = True  # 所有测验完成状态
                    course_score[0].complete_date = datetime.now()  # 测验完成时间

                    for stage in cur_course.stages_m.all():
                        stage_id = stage.id
                        career_course = Stage.objects.get(pk = stage_id).career_course
                        # 如已完成所有考核项，则发送课程通过与否的站内消息
                        total_score = get_course_score(course_score[0], cur_course)
                        if total_score >= 60:
                            sys_send_message(0, student.id, 1, "恭喜您已通过<a href='/lps/learning/plan/"+str(career_course.id)+"/'>"+
                                                               str(cur_course.name)+"</a>课程，总获得测验分"+str(total_score)+
                                                               "分！<a href='/lps/learning/plan/"+str(career_course.id)+"/'>继续学习下一课</a>")
                        else:
                            sys_send_message(0, student.id, 1, "您的课程<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_id)+"'>"+str(cur_course.name)+
                                                               "</a>挂科啦。不要灰心，<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_id)+"'>去重修</a>")
                            # 继续检查是否完成该阶段的所有考核项
                        if check_stage_exam_is_complete(student, cur_course, stage):
                            # 如果完成了所有考核项，则检查该课程对应职业课程的所有阶段和解锁信息
                            stage_list = Stage.objects.filter(career_course=stage.career_course)
                            cur_stage_count = 0
                            for i,stage in enumerate(stage_list):
                                if stage.id == stage_id:
                                    cur_stage_count = i
                                    break
                            if (cur_stage_count+1) < len(stage_list):
                                # 检查下一个阶段是否已经解锁
                                if UserUnlockStage.objects.filter(user=student, stage=stage_list[cur_stage_count+1]).count()>0:
                                    # 已经解锁
                                    msg = "恭喜您能努力坚持学完"+career_course.name+"的第"+str(cur_stage_count+1)+"阶段，赶快继续深造吧，你离梦想仅一步之遥了哦！<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_list[cur_stage_count+1].id)+"'>立即学习下一阶段</a>"
                                else:
                                    # 还未解锁
                                    msg = "恭喜您能努力坚持学完"+career_course.name+"的第"+str(cur_stage_count+1)+"阶段，赶快续费继续深造吧，你离梦想仅一步之遥了哦！<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_list[cur_stage_count+1].id)+"'>立即购买下一阶段</a>"
                            else:
                                msg = "恭喜您能努力坚持学完"+career_course.name+"所有课程，你还可以继续深造哦！<a href='/course/'>去选课程</a>"
                            sys_send_message(0, student.id, 1, msg)
                else:
                    # 如果是未完成所有考核项，但是测验分已经超过了60分，则可以判定课程通过，提前更新课程测验完成状态
                    if get_course_score(course_score[0], cur_course) >= 60:
                        course_score[0].is_complete = True  # 所有测验完成状态
                course_score[0].save()

    # 更新班级学力汇总信息
    if study_point > 0 and rebuild_count == 0:
        for stage in cur_course.stages_m:
            stage_id = stage.id
            class_students = ClassStudents.objects.filter(user=student,student_class__career_course=Stage.objects.get(pk = stage_id).career_course)
            if len(class_students)>0:
                class_students[0].study_point += study_point
                class_students[0].save()

calcing = False
def calc_study_point():
    try:
        global calcing
        if calcing:
            return
        calcing=True
        async_methods=AsyncMethod.objects.filter(is_calc = False) #.order_by("-priority","submit_datetime")
        print "aaa1"
        #time.sleep(60)
        if len(async_methods):
            am=async_methods[0]
            if am.calc_type==1:
                amdict=json.loads(am.methods)
                update_study_point_score(student=UserProfile.objects.get(pk=amdict["student"]),
                                         study_point=amdict["study_point"],
                                         score=amdict["score"],
                                         examine= None if amdict["examine"]<0 else Examine.objects.get(pk=amdict["examine"]),
                                         examine_record= None if amdict["examine_record"]<0 else ExamineRecord.objects.get(pk=amdict["examine_record"]),
                                         teacher= None if amdict["teacher"]<0 else UserProfile.objects.get(pk=amdict["teacher"]),
                                         course= None if amdict["course"]<0 else Course.objects.get(pk=amdict["course"]),
                                         rebuild_count=amdict["rebuild_count"])

            am.calc_datetime = datetime.now()
            am.is_calc=True
            am.save()

    except Exception as e:
        print e

    calcing=False