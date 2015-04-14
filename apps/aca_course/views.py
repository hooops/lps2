# -*- coding: utf-8 -*-
from __future__ import division
from django.shortcuts import render
from aca_course.models import *
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse,HttpResponseRedirect
from django.conf import settings
from django.db.models import Q
from datetime import datetime, timedelta
from aca_course.models import *
from django.core.urlresolvers import reverse
from mz_common.views import *
from mz_user.models import *

import logging, os, json, re

logger = logging.getLogger('mz_lps.views')

# 得到高校专区首页
def academic_home_view(request):
    template_vars = cache.get('academic_home_view')
    if not template_vars:
        #省份/城市列表
        try:
            citys = ProvinceCity.objects.all().order_by("index", "id")
        except Exception as e:
            logger.error(e)

        template_vars = {'citys': citys}

        cache.set('academic_home_view', template_vars, settings.CACHE_TIME)

    return render(request, 'aca_course/academic_home.html', template_vars)

@csrf_exempt
def academic_school_list(request):
    data = []
    city_id = request.POST['city_id'] or None
    template_vars = cache.get('academic_school_list_'+str(city_id))
    if not template_vars:
        if city_id is not None:
            orgs = AcademicOrg.objects.filter(province_city_id=city_id,level = 1)
            data = [{"href": '/academic/'+str(o.id)+'/',
                     "src":settings.MEDIA_URL+str(o.image),
                     "text": o.description} for o in orgs]

        template_vars = data
        cache.set('academic_school_list_'+str(city_id), template_vars, settings.CACHE_TIME)

    return HttpResponse(json.dumps(template_vars), content_type="application/json")



# 得到专业列表
def academiccourse_list_view(request, university_id=-1):
    try:
        template_vars = cache.get('academiccourse_list_view_'+str(university_id))
        if not template_vars:
            #得到专业列表：academiccourse
            #得到高校通知列表:notification
            if university_id !=-1 and university_id is not None:
                school = AcademicOrg.objects.get(id=university_id,level = 1)
                aorg = AcademicOrg.objects.filter(level=2,parent=university_id).values_list('id')
                acourse = AcademicCourse.objects.filter(owner__in =aorg)
                msgs = Notification.objects.filter(owner_id = university_id ).order_by("index", "-id")[:5]

            template_vars = {'school': school, 'acourse': acourse, 'msgs': msgs, 'university_id': university_id}
            cache.set('academiccourse_list_view_'+str(university_id), template_vars, settings.CACHE_TIME)

        return render(request, 'aca_course/academiccourse_list.html', template_vars)
    except Exception as e:
        logger.error(e)
        result = '{"status":"error","message":"学校不存在！"}'
        return HttpResponse(result, content_type="application/json")

# 打开验证页面
@csrf_exempt
def student_verify_view(request, university_id, course_id):
    if not request.user.is_authenticated():
        return render(request, 'mz_common/failure.html',{'reason':'没有访问权限，请先登录。<a href="'+str(settings.SITE_URL)+'">返回首页</a>'})

    if university_id != "0":
        try:
            cur_university=AcademicOrg.objects.get(pk=university_id, level= 1)
        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':e.message})

        try:
            cur_course=AcademicCourse.objects.get(pk=course_id)
        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':e.message})

        try:
            sv_list=request.user.academicuser_set.filter(owner_university=cur_university, academic_course=cur_course)
            if len(sv_list):
                return HttpResponseRedirect(reverse('course:course_detail_academic',
                                                    kwargs={"course_id": course_id,"university_id": university_id})) #'course/'+str(course_id)+'/')#
        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':e.message})

    return render(request, 'aca_course/student_verify_popup.html',locals())

# 验证用户身份
@csrf_exempt
def student_verify_post(request,university_id,course_id):
    # Post请求，来自student_verify_popup.html
    if not request.user.is_authenticated():
        return HttpResponse('{"status":"failure","message":"没有权限"}', content_type="application/json")

    if university_id != "0":
        # 是否具有该大学
        try:
            cur_university = AcademicOrg.objects.get(pk=university_id, level=1)
        except AcademicOrg.DoesNotExist:
            return HttpResponse('{"status":"failure","message":"不存在大学"}', content_type="application/json")

        try:
            cur_course=AcademicCourse.objects.get(pk=course_id)
            #cur_career_course=CareerCourse.objects.get(pk=course_id)
        except Exception as e:
            logger.error(e)
            return HttpResponse('{"status":"failure","message":"不存在该专业课程"}', content_type="application/json")

    try:
        stu_name=request.POST.get("stu_name")
        user_no=request.POST.get("stu_no")
        verify_code=request.POST.get("verify_code")

        if university_id != "0":
            sv_list = AcademicUser.objects.filter(Q(owner_university=cur_university), Q(academic_course=cur_course),
                                               Q(stu_name=stu_name), Q(user_no= user_no), Q(verify_code = verify_code)) #, Q(user=None))
        else:
            sv_list = AcademicUser.objects.filter(Q(stu_name=stu_name), Q(user_no= user_no), Q(verify_code = verify_code))#, Q(user=None))

        if len(sv_list):
            if sv_list[0].is_binded:
                return HttpResponse('{"status":"failure","message":"该学员信息已经验证过啦"}', content_type="application/json")

            sv_list[0].user = request.user
            sv_list[0].is_binded=True
            sv_list[0].binded_date= datetime.today()
            sv_list[0].save()

            #通过导入表获得对应的大学和专业课程
            cur_university=sv_list[0].owner_university
            cur_course=sv_list[0].academic_course

            #检查是否建立了对应的班级
            try:
                ac_list=AcademicClass.objects.filter(career_course = cur_course)
                cur_class=ac_list[0]
            except Exception as e:
                logger.error(e)
                return HttpResponse('{"status":"failure","message":"尚未建立该专业课程的班级"}', content_type="application/json")

            #解锁阶段
            for stage in cur_course.stage_set.all() :
                try:
                    UserUnlockStage.objects.get(user=request.user, stage=stage)
                except UserUnlockStage.DoesNotExist:
                    unlock_stage = UserUnlockStage()
                    unlock_stage.user = request.user
                    unlock_stage.stage = stage
                    unlock_stage.save()

            #加入班级
            if cur_class.students.filter(pk=request.user.id).count() == 0:
                class_students = ClassStudents()
                class_students.student_class = cur_class
                class_students.user = request.user
                # 获取当前学力
                class_students.study_point = get_study_point(request.user, cur_class.career_course)
                class_students.save()

                cur_class.current_student_count += 1
                cur_class.save()

            return HttpResponse('{"status":"success","message":"验证成功","university":"'
                                +str(cur_university.id)+'","course":"'+str(cur_course.id)+'"}', content_type="application/json")
        else:
            return HttpResponse('{"status":"failure","message":"您输入的信息有误，请重试"}', content_type="application/json")

    except Exception,e:
        logger.error(e)
        return HttpResponse('{"status":"failure","message":"发生异常"}', content_type="application/json")


