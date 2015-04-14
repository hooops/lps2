# -*- coding: utf-8 -*-
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
from models import *
from decimal import * # import by duhaoyu
from mz_lps import * # import by duhaoyu
from mz_course import * #import by duhaoyu
import operator   # import by duhaoyu
from django.template import loader,Context # import by duhaoyu
import  string #import by duhaoyu
logger = logging.getLogger('mz_lps2.chart_views')
#界面图表所需数据

def _get_stu_overview(request):
    #本周完成任务度
    # careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data=course_data_class.courseusertask_set.filter(user=request.user)
    print course_data
    real_course = Decimal(course_data[0].real_study_time)/Decimal( course_data[0].plan_study_time)
    no_real_course = 1-real_course
    print 'real_course',real_course
    print 'no_real_course',no_real_course
    #状态
    stu_statu=career_course_data_stu.planning_set.filter(user=request.user)[0]
    statu=stu_statu.planningpause_set.all()
    print 'k',statu[0].pause_date
    if statu[0].pause_date>statu[0].restore_date:
        statu_class_stu= '暂停'
    elif statu[0].pause_date<statu[0].restore_date:
        statu_class_stu='正常'
    print statu_class_stu
    #班级排名
    rank_in_class_print = course_data[0].rank_in_class

    #总学习时长
    total_study_time_print = course_data[0].total_study_time

    #预计毕业时间
    plan_gradute_time_print = course_data[0].plan_gradute_time

    #学习状态
    t = loader.get_template('test_main.html')
    c=Context({'real_Course':real_course,
              'no_real_Course':no_real_course,
              'rank_in_class_print':rank_in_class_print,
              'total_study_time_print':total_study_time_print,
               'plan_gradute_time_print':plan_gradute_time_print,
                'statu_class_stu':statu_class_stu
               })
    return HttpResponse(t.render(c))

def _get_task_list(request):
    # careerCourse_name='orm'
    # # careerCourse_name = request.POST.get('careerCourse_name')
    # # careerCourse_name='orm'
    # #
    # # JoinClassUserTask_data=JoinClassUserTask.objects.filter(user=request.user)
    # # if JoinClassUserTask_data[0].finish_date is  None:
    # #     JoinClassUserTask_data1=JoinClassUserTask_data
    # #
    # #     JoinClassUserTask_data2=None
    # # else:
    # #     JoinClassUserTask_data2=JoinClassUserTask_data
    # #
    # #     JoinClassUserTask_data1=None
    # #
    # # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # # career_course_data_stu_class=career_course_data_stu.class_set.all()[0]
    # # viewcontractusertask_data = career_course_data_stu_class.viewcontractusertask_set.all()
    # #
    # # if viewcontractusertask_data[0].finish_date is  None:
    # #
    # #     viewcontractusertask_data1=viewcontractusertask_data
    # #
    # #     viewcontractusertask_data2=None
    # # else:
    # #     viewcontractusertask_data2=viewcontractusertask_data
    # #
    # #     viewcontractusertask_data1=None
    # #
    # #
    # # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # # course_data_class = career_course_data_stu.class_set.all()[0]
    # # course_data_week_task=course_data_class.courseusertask_set.filter(user=request.user)
    # # if course_data_week_task[0].plan_study_time!=course_data_week_task[0].total_study_time:
    # #
    # #     course_data_week_task1=course_data_week_task
    # #
    # #
    # #     course_data_week_task2=None
    # # else:
    # #     course_data_week_task2=course_data_week_task
    # #
    # #
    # #     course_data_week_task1=None
    # #
    # #
    # # # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # # # course_data_class = career_course_data_stu.class_set.all()[0]
    # # # fullprofileusertask=course_data_class.fullprofileusertask_set.filter(user=request.user)
    # # fullprofileusertask=FullProfileUserTask.objects.filter(user=request.user)[0]
    # # if fullprofileusertask.finish_date is not None:
    # #
    # #     fullprofileusertask1=fullprofileusertask
    # #
    # #     fullprofileusertask2=None
    # # else:
    # #     fullprofileusertask2=fullprofileusertask
    # #
    # #     fullprofileusertask1=None
    # #
    # # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # # course_data_class = career_course_data_stu.class_set.all()[0]
    # # course_data_week_meet=course_data_class.classmeetingtask_set.filter(user=request.user)
    # # # if JoinClassUserTask_data is not None:
    # # #     JoinClassUserTask_data_v={'JoinClassUserTask_data_vv':'班级已加入'}
    # # # if viewcontractusertask_data is not None:
    # # #     viewcontractusertask_data_v={'JoinClassUserTask_data_vv':'协议已查看'}
    # # #
    # # # if fullprofileusertask is not None:
    # # #
    # # #     fullContractUsertask_v={'JoinClassUserTask_data_vv':'资料已完善'}
    # # # if course_data_week_task is not None:
    # # #     course_data_week_task_v={'JoinClassUserTask_data_vv':'协议已生成'}
    # # #
    # # # if course_data_week_meet is not None:
    # # #     course_data_week_meet_v={'JoinClassUserTask_data_vv':'会议创建'}
    # # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # # course_data_class = career_course_data_stu.class_set.all()[0]
    # # course_data=course_data_class.courseusertask_set.filter(user=request.user)
    # # v_class=viewcontractusertask_data[0].finish_date
    # # v_join_class=JoinClassUserTask_data[0].finish_date
    # # time_line=[v_class,v_join_class]
    # #
    # # dic_arr=[{'date_now':v_class,
    # #           'date_stau':(viewcontractusertask_data1[0].finish_date).strftime('%Y%m%d')[4:6],
    # #          'date_stauto':(viewcontractusertask_data1[0].finish_date).strftime('%Y%m%d')[6:8]},
    # #          {'date_now':v_join_class,
    # #           'date_stau':viewcontractusertask_data1[0].finish_date.strftime('%Y%m%d')[4:6],
    # #           'date_stauto':viewcontractusertask_data1[0].finish_date.strftime('%Y%m%d')[6:8] }]
    # #
    # #
    # #
    # # dic_arr2=[{'date_now':v_class,
    # #           'date_stau':(viewcontractusertask_data2[0].finish_date).strftime('%Y%m%d')[4:6],
    # #          'date_stauto':(viewcontractusertask_data2[0].finish_date).strftime('%Y%m%d')[6:8]},
    # #          {'date_now':v_join_class,
    # #           'date_stau':viewcontractusertask_data2[0].finish_date.strftime('%Y%m%d')[4:6],
    # #           'date_stauto':viewcontractusertask_data2[0].finish_date.strftime('%Y%m%d')[6:8]
    # #
    # #           }]
    # #
    # #
    # # print '----',time_line,datetime.datetime.now().strftime("%Y-%m-%d")
    # # # v_course=course_data_week_task[0].finish_date
    # # # print v_class,v_join_class,v_course
    # # sorted_x = sorted(dic_arr, key=operator.itemgetter('date_now'), reverse=True)
    # # sorted_x2 = sorted(dic_arr2, key=operator.itemgetter('date_now'), reverse=True)
    # # # print sorted_x
    # #
    # # m_class=(viewcontractusertask_data[0].finish_date).strftime('%Y%m%d')[4:6]
    # # d_class=(viewcontractusertask_data[0].finish_date).strftime('%Y%m%d')[6:8]
    # # m_view=viewcontractusertask_data[0].finish_date.strftime('%Y%m%d')[4:6]
    # # d_view=viewcontractusertask_data[0].finish_date.strftime('%Y%m%d')[6:8]
    #
    #
    # # course_data_week_task[0].
    # # t = loader.get_template('test_main7.html')
    # # c=Context({'JoinClassUserTask_data_vv':'班级已加入',
    # #         'viewcontractusertask_data':'协议以查看',
    # #         'fullContractUsertask_v':'资料已完成',
    # #         'course_data_week_task_v':'协议生成',
    # #         'course_data_week_meet_v':'会议创建',
    # #         'date_class_m':m_class,
    # #         'd_class':d_class,
    # #         'm_view':m_view,
    # #         'd_view':d_view,
    # #         #'sorted_x':sorted_x,
    # #         'sorted_x2':sorted_x2
    # # 'date_course':course_data_week_task[0].finish_date,
    # # 'date_fullprofileusertask':fullprofileusertask[0].finish_datefinish_date,
    # # 'date_course_data_week_meet':course_data_week_meet[0].finish_date
    #
    #
    #
    # # })
    # # return HttpResponse(t.render(c))
    # jonclass_key=JoinClassUserTask.objects.filter(user=request.user)
    # viewcon_key=ViewContractUserTask.objects.filter(user=request.user)
    # fullpro_key=FullProfileUserTask.objects.filter(user=request.user)
    # readme_key=ReadMeUserTask.objects.filter(user=request.user)
    # teacharpro_key=TeacherProfileUserTask.objects.filter(user=request.user)
    # stusta_key=StuStatusUserTask.objects.filter(user=request.user)
    # career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    # course_data_class = career_course_data_stu.class_set.all()[0]
    # course_data=course_data_class.courseusertask_set.filter(user=request.user)
    # if jonclass_key.status==2 or jonclass_key.status==0:
    #
    # else:
    #
    # if viewcon_key.status==2 or viewcon_key.status==0:
    #
    # else:
    #
    # if fullpro_key.status==2 or fullpro_key.status==0:
    #
    # else:
    #
    # if readme_key.status==2 or readme_key.status==0:
    #
    # else:
    #
    # if teacharpro_key.status==2 or teacharpro_key.status==0:
    #
    # else:
    #
    # if stusta_key.status==2 or stusta_key.status==0:
    #
    # else:
    #
    # if course_data.status==2 or course_data.status==0:
    #
    # else:
    #




def _find_all_week_task(request):

    careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_week_task=course_data_class.courseusertask_set.filter(user=request.user)
    print 'course_data_week_task',course_data_week_task


    t = loader.get_template('test_main2.html')
    c=Context({'course_data_week_task':course_data_week_task})
    return HttpResponse(t.render(c))





def _find_all_course_score(request):
    careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_score=course_data_class.courseusertask_set.filter(user=request.user)

    t = loader.get_template('test_main3.html')
    c=Context({'course_data_score':course_data_score,
                               })
    return HttpResponse(t.render(c))


def _find_all_study_point(request):
    careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_study_point=course_data_class.courseusertask_set.filter(user=request.user)

    t = loader.get_template('test_main4.html')
    c=Context({'course_data_study_point':course_data_study_point, })
    return HttpResponse(t.render(c))



def _calc_stu_quality():
    pass

def _calc_stu_radarchart():
    pass

def _calc_stu_quality_diff():
    pass

def _find_all_student_progress(request):
    careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_student_progress=course_data_class.students.all()
    # print 'sss',course_data_student_progress[].username
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_study_now=course_data_class.courseusertask_set.filter(user=request.user)


    arrx=[]
    for s in range(0,len(course_data_study_now),1):
        progress_data=Decimal(course_data_study_now[s].plan_study_time)/Decimal(course_data_study_now[s].real_study_time)
        # x={}
        # x['key']=progress_data
        # x['value']=progress_data
        arrx.append(progress_data)

    print 'cc',arrx
    t = loader.get_template('test_main6.html')
    c=Context({'course_data_student_progress':course_data_student_progress,'arrx':arrx})
    return HttpResponse(t.render(c))


def _find_all_student_rank(request):
    careerCourse_name = request.POST.get('careerCourse_name')
    careerCourse_name='orm'
    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    class_student_name=course_data_class.students.all()
    course_data_student_rank=course_data_class.courseusertask_set.filter(user=request.user)

    career_course_data_stu = CareerCourse.objects.filter(name = careerCourse_name)[0]
    course_data_class = career_course_data_stu.class_set.all()[0]
    course_data_student_rank=course_data_class.courseusertask_set.filter(user=request.user)

    t = loader.get_template('test_main5.html')
    c=Context({'course_data_student_rank':course_data_student_rank,
               'class_student_name':class_student_name})
    return HttpResponse(t.render(c))
