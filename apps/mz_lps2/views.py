# -*- coding: utf-8 -*-
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


logger = logging.getLogger('mz_lps2.views')


# global value setting
HOURS_PER_VIDEO = 1
HOURS_PER_PROJ = 5
DEFAULT_HOURS_PER_WEEK = 15


def _get_task_list():
    pass

# 判读是否有重修课程
def __has_rebuild():
    return False

# 判断是否存在变更的课程（如新增章节或项目制作）
def __has_updated_courses():
    return False

# 处理变更课程
def __handle_updated_courses():
    pass

# 判断职业课程是否已结束
def __is_end_careercourse():
    return False

# 比较两个课程间的先后顺序
def __handle_cmp(a, b):
    if a.stages.index > b.stages.index:
        return 1
    elif a.stages.index < b.stages.index:
        return -1
    else:
        if a.stages.id > b.stages.id:
            return 1
        elif a.stages.id < b.stages.id:
            return -1
        else:
            if a.index > b.index:
                return 1
            elif a.index < b.index:
                return -1
            else:
                return a.id >= b.id and 1 or -1

# 计算下次任务起始课程及章节
def __calc_next_course(pre_task_content):
    recent_course_proj = None # 最近学习课程(项目制作)
    recent_course_video = None # 最近学习课程（视频）
    recent_course = None # 最近学习课程
    recent_course_flag = None # 最近学习课程标志
    recent_lesson = None # 最近学习章节

    start_type = None # 下次任务起始项类型： 'P' 或者 'V'
    next_course = None # 下次任务起始课程
    next_lesson = None # 下次任务起始章节

    # 如果有额外完成项目制作任务
    if pre_task_content.has_key('EP'):
        course_id_set = pre_task_content['EP'].keys() # 上周额外完成的项目制作任务所属的课程ID集合
        try:
            course_set = Course.objects.select_related().filter(id__in=course_id_set)#.order_by('-index', '-id')
        except:
            assert False

        sorted_set = sorted(course_set, cmp=__handle_cmp, key=lambda e:e, reverse=True)
        recent_course_proj = sorted_set[0] #获得项目制作所属最近学习课程

    # 如果有额外完成视频章节任务
    if pre_task_content.has_key('EV'):
        course_id_set = pre_task_content['EV'].keys() # 上周额外完成的视频章节任务所属的课程ID集合
        try:
            course_set = Course.objects.select_related().filter(id__in=course_id_set)#.order_by('-index', '-id')
        except:
            assert False

        sorted_set = sorted(course_set, cmp=__handle_cmp, key=lambda e:e, reverse=True)
        recent_course_video = sorted_set[0] #获得视频章节所属最近学习课程
        lesson_id_set = pre_task_content['EV'][str(recent_course_video.id)]
        try:
            lesson_set = Lesson.objects.select_related().filter(id__in=lesson_id_set).order_by('-index', '-id')
        except:
            assert False
        recent_lesson = lesson_set[0] # 获得最近学习视频章节

    # 没有额外完成任务
    if not pre_task_content.has_key('EP') and not pre_task_content.has_key('EV'):
        if pre_task_content.has_key('P'):
            course_id_set = pre_task_content['P'].keys() # 上周规定完成项目制作任务所属的课程ID集合
            try:
                course_set = Course.objects.select_related().filter(id__in=course_id_set)#.order_by('-index', '-id')
            except:
                assert False

            sorted_set = sorted(course_set, cmp=__handle_cmp, key=lambda e:e, reverse=True)
            recent_course_proj = sorted_set[0] #获得项目制作所属最近学习课程

        if pre_task_content.has_key('V'):
            course_id_set = pre_task_content['V'].keys() # 上周规定完成视频章节任务所属的课程ID集合

            try:
                course_set = Course.objects.select_related().filter(id__in=course_id_set)#.order_by('-index', '-id')
            except:
                assert False

            sorted_set = sorted(course_set, cmp=__handle_cmp, key=lambda e:e, reverse=True)

            recent_course_video = sorted_set[0] #获得视频章节所属最近学习课程
            recent_lesson_id = pre_task_content['V'][str(recent_course_video.id)][1]
            try:
                recent_lesson = Lesson.objects.get(id=recent_lesson_id)
            except:
                # 上周实际工作量为0
                return None


    # 计算下一周任务的起始课程和对应视频章节或项目制作
    if recent_course_proj and recent_course_video:
        if recent_course_proj.index > recent_course_video.index or \
                (recent_course_proj.index == recent_course_video.index and
                 recent_course_proj.id >= recent_course_video.id):
            recent_course_flag = 'P'
            recent_course = recent_course_proj
        else:
            recent_course_flag = 'V'
            recent_course = recent_course_video
    elif recent_course_proj: # 上周只有项目制作任务
        recent_course_flag = 'P'
        recent_course = recent_course_proj
    elif recent_course_video: # 上周只有视频章节任务
        recent_course_flag = 'V'
        recent_course = recent_course_video
    else:
        assert False

    if recent_course_flag is 'P':
        start_type = 'V'

        try:
            my_stage = recent_course.stages
            course_set = my_stage.getCourseSet().order_by('index', 'id')
        except:
            assert False

        i = 0
        for each_course in course_set:
            if each_course == recent_course:
                break
            i += 1
        if i < course_set.count() - 1: # 本阶段下课程尚未结束
            next_course = course_set[i+1]
        else: # 本阶段下课程已经全部完成，进入下一阶段学习
            try:
                stage_set = Stage.objects.select_related().filter(career_course=my_stage.career_course).order_by('index', 'id')
            except:
                assert False

            i = 0
            for each_stage in stage_set:
                if each_stage == my_stage:
                    break
                i += 1
            if i < stage_set.count() - 1: # 职业课程还未结束
                i += 1
                course_set = stage_set[i].getCourseSet().order_by('index', 'id')
                while not course_set: # 如果该阶段下课程为空
                    i += 1
                    if i >= stage_set.count():
                        # 在职业课程最后处理存在变更的课程（如新增章节或项目制作）
                        __handle_updated_courses()
                        print "职业课程学习完毕！"
                        return None
                    course_set = stage_set[i].getCourseSet().order_by('index', 'id')
                next_course = course_set[0]
            else: # 职业课程已经全部完成
                # 在职业课程最后处理存在变更的课程（如新增章节或项目制作）
                __handle_updated_courses()
                print "职业课程学习完毕！"
                return None

    elif recent_course_flag is 'V':
        try:
            lesson_set = Lesson.objects.select_related().filter(course=recent_course).order_by('index', 'id')
        except:
            assert False

        i = 0
        for each_lesson in lesson_set:
            if each_lesson == recent_lesson:
                break
            i += 1
        if i < lesson_set.count() - 1: # 同上
            next_lesson = lesson_set[i+1]
            next_course = recent_course
            start_type = 'V'
        else:
            next_course = recent_course
            start_type = 'P'

    return [start_type, next_course, next_lesson]


# 计算下次任务
def __calc_next_task(is_first_task, start_type, next_course, next_lesson, pre_learning_hours, career_course):
    learning_hours = 0
    learning_plans = {}
    if not is_first_task:
        # 第一轮课程查询 (处理拆分课程)
        if start_type == 'P':
            # 判断该课程下是否有项目制作
            if not Project.objects.filter(examine_type=5, relation_type=2, relation_id=next_course.id):
                pass
            else:
                tmp = {}
                tmp[next_course.id] = False
                try:
                    learning_plans['P'].update(tmp)
                except:
                    learning_plans['P'] = tmp
                learning_hours += HOURS_PER_PROJ
        elif start_type == 'V':
            if next_lesson: # 从对应课程下特定视频章节(非首章节)开始
                lesson_set = Lesson.objects.filter(course=next_course).order_by('index', 'id')

                tmp = {}
                tmp[next_course.id] = [0, 0, []]

                tmp_flag = False
                i = 0
                for each_lesson in lesson_set:
                    if each_lesson == next_lesson:
                        tmp_flag = True
                    if tmp_flag:
                        if learning_hours + HOURS_PER_VIDEO > pre_learning_hours:
                            break
                        tmp[next_course.id][2].append(lesson_set[i].id)
                        learning_hours += HOURS_PER_VIDEO
                    i += 1

                to_do_lessons = tmp[next_course.id][2]
                tmp[next_course.id][0] = len(to_do_lessons)
                tmp[next_course.id][1] = to_do_lessons[-1]
                try:
                    learning_plans['V'].update(tmp)
                except:
                    learning_plans['V'] = tmp

                if learning_hours >= pre_learning_hours:
                    # print learning_plans, learning_hours
                    # pdb.set_trace()
                    return [learning_plans, learning_hours]
                else:
                    # 判断课程下是否有项目制作
                    if not Project.objects.filter(examine_type=5, relation_type=2, relation_id=next_course.id):
                        pass
                    else:
                        tmp = {}
                        tmp[next_course.id] = False
                        try:
                            learning_plans['P'].update(tmp)
                        except:
                            learning_plans['P'] = tmp
                        learning_hours += HOURS_PER_PROJ

        if learning_hours >= pre_learning_hours:
            # print learning_plans, learning_hours
            # pdb.set_trace()
            return [learning_plans, learning_hours]


        # 处理重修课程
        #############
        #to do
        ##############
        if __has_rebuild():
            pass

        # 除video 首章节以外所有情况，都需要跳到下一课
        if not (start_type == 'V' and not next_lesson):
            course_set = Course.objects.filter(stages=next_course.stages).order_by('index', 'id')
            i = 0
            for each_course in course_set:
                if each_course == next_course:
                    break
                i += 1

            if i < course_set.count() - 1: # 同上
                next_course = course_set[i+1]
            else:
                stage_set = Stage.objects.filter(career_course=next_course.stages.career_course).order_by('index', 'id')
                i = 0
                for each_stage in stage_set:
                    if each_stage == next_course.stages:
                        break
                    i += 1

                if i < stage_set.count() - 1: # 同上
                    i += 1
                    course_set = stage_set[i].getCourseSet().order_by('index', 'id')
                    while not course_set: # 如果该阶段下课程为空
                        i += 1
                        if i >= stage_set.count():
                            # 在职业课程最后处理存在变更的课程（如新增章节或项目制作）
                            __handle_updated_courses()
                            print "职业课程学习完毕！"
                            return None
                        course_set = stage_set[i].getCourseSet().order_by('index', 'id')
                    next_course = course_set[0]
                else: # 同上
                    # 在职业课程最后处理存在变更的课程（如新增章节或项目制作）
                    __handle_updated_courses()
                    print "职业课程已学习完毕！"
                    # print learning_plans, learning_hours
                    # pdb.set_trace()
                    return [learning_plans, learning_hours]


    # 后续课程查询
    IS_ACTION = False
    try:
        stage_set = Stage.objects.select_related().filter(career_course=career_course).order_by('index', 'id')
    except:
        assert False

    for each_stage in stage_set:
        try:
            course_set = each_stage.getCourseSet().order_by('index', 'id')
        except:
            assert False
        for each_course in course_set:
            if is_first_task or each_course == next_course:
                IS_ACTION = True
                is_first_task = False
            if IS_ACTION:
                current_course = each_course
                lesson_set = Lesson.objects.filter(course=current_course).order_by('index', 'id')

                if not lesson_set: #如果课程下无视频章节，则跳过该课程
                    continue

                tmp = {}
                tmp[current_course.id] = [0, 0, []]

                for each_lesson in lesson_set:
                    if learning_hours + HOURS_PER_VIDEO > pre_learning_hours:
                        break
                    tmp[current_course.id][2].append(each_lesson.id)
                    learning_hours += HOURS_PER_VIDEO

                to_do_lessons = tmp[current_course.id][2]
                tmp[current_course.id][0] = len(to_do_lessons)
                tmp[current_course.id][1] = to_do_lessons[-1]
                try:
                    learning_plans['V'].update(tmp)
                except:
                    learning_plans['V'] = tmp
                if learning_hours >= pre_learning_hours:
                    # print learning_plans, learning_hours
                    # pdb.set_trace()
                    return [learning_plans, learning_hours]
                else:
                    tmp = {}
                    tmp[current_course.id] = False
                    try:
                        learning_plans['P'].update(tmp)
                    except:
                        learning_plans['P'] = tmp
                    learning_hours += HOURS_PER_PROJ

                if learning_hours >= pre_learning_hours:
                    # print learning_plans, learning_hours
                    # pdb.set_trace()
                    return [learning_plans, learning_hours]
    # print learning_plans, learning_hours
    # pdb.set_trace()
    return [learning_plans, learning_hours]


# 生成下周任务
# learning_plans 数据格式：{"P": {course1_id: False, course2_id: False, },
# "V":{course1_id: [to_do_lessons_count, end_lesson_id, [to_do_lesson1_id, to_do_lesson2_id,]],}
# "EP":{course1_id: True,},
# "EV":{course1_id: [done_lesson1_id,]}}
# P代表项目制作，V代表章节（视频+随堂测验），
# to_do_lessons_count代表对应课程course_id下本任务中应完成章节数，
# [to_do_lesson1_id,]为课程course1_id下待完成章节列表
# end_lesson_id 为课程course1_id下最末章节
#  [done_lesson1_id,]为course11_id下按序超额完成的章节列表
def plan_for_nextweek(user_id, class_id):
    if __is_end_careercourse():
        if __has_updated_courses():
            __handle_updated_courses()
            return None
    try:
        my_class = Class.objects.get(id=class_id)
    except:
        assert False

    try:
        user = UserProfile.objects.get(id=user_id)
    except:
        assert False

    career_course = my_class.career_course
    is_first_task = False

    start_type = None
    next_course = None
    next_lesson = None

    learning_plans = {}
    learning_hours = 0

    # 获得上周任务表
    try:
        pre_course_user_task = CourseUserTask.objects.select_related().filter(user=user, user_class=my_class).order_by('-create_datetime')[0] #默认按建立时间从近到远返回结果集
    except: # 刚开始进入该职业课程
        pre_learning_hours = DEFAULT_HOURS_PER_WEEK
        is_first_task = True
    else:
        # 当前根据上周实际完成学时数，生成下周计划学时数，可据此小幅调整（由于不可切分项目制作缘故）
        # 获得上周实际完成学时数及任务完成情况
        pre_learning_hours = pre_course_user_task.real_study_time
        pre_task_content = json.loads(pre_course_user_task.relate_content)

        # 获得上周最近任务项（可能是视频章节或项目制作）, 计算下次任务起始课程
        start_type, next_course, next_lesson = __calc_next_course(pre_task_content)

    # 计算下次任务
    learning_plans, learning_hours = __calc_next_task(is_first_task, start_type, next_course, next_lesson, pre_learning_hours, career_course)
    return [learning_plans, learning_hours]

def plan_module(): # 时间到了，要生成下一个课程的计划
    ret=False
    return ret
def finish_module(): #定期判断，课程是否完成，进度情况
    ret=False
    return ret
