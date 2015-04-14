# -*- coding: utf-8 -*-
import logging
import json
import re
import uuid
import urllib
import urllib2
import requests
import xlrd
import xlwt
import os

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate,login,logout
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.mail import send_mail
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.cache import cache
from datetime import datetime
from mz_common.decorators import superuser_required
from mz_common.models import Log,Coupon,Coupon_Details,RecommendedReading, MsgBox
from mz_backend.forms import UserForm
from mz_user.models import UserProfile, UserUnlockStage, MyCourse
from mz_course.models import Lesson
from mz_lps.models import Class, ClassStudents, Planning, LiveRoom
from mz_pay.models import UserPurchase
from utils import xinge
from mz_common.views import get_study_point, sys_send_message, app_send_message
from aca_course.models import *
from utils.tool import generate_random

logger = logging.getLogger('mz_backend.views')

# 后台首页
@superuser_required
def admin_index_view(request):
    return render(request, 'mz_backend/index.html',locals())

#后台登录
def admin_login(request):
    if request.method == 'POST':
        uf = UserForm(request.POST)
        if uf.is_valid():
            #获取表单用户密码
            username = uf.cleaned_data['username']
            password = uf.cleaned_data['password']
            #获取的表单数据与数据库进行比较
            #登录验证
            user = authenticate(username=username, password=password)
            if user is not None:
                # 登录
                if user.is_superuser or user.is_staff:
                    login(request, user)
                    return HttpResponseRedirect('/backend/index/')
    else:
        uf = UserForm()
    return render(request, 'mz_backend/login.html',locals())

# 后台注销
@superuser_required
def admin_logout(request):
    '''
    后台注销
    :param request:
    :return:
    '''
    logout(request)
    return HttpResponseRedirect(reverse('backend:admin_login'))

# 更新视频长度view
@superuser_required
def update_video_length_view(request):
    return render(request, 'mz_backend/update_video_length.html',locals())

# 获取章节列表
@superuser_required
def get_lessons_list(request):
    min_id = request.GET.get('min_id', None)
    count = request.GET.get('count', None)
    if min_id:
        lessons = Lesson.objects.filter(id__gte=min_id).order_by('id').all()
    else:
        lessons = Lesson.objects.order_by('id').all()

    if count and int(count) < len(lessons):
        lessons = lessons[0:int(count)]
    lessons = [{'id': lesson.id, 'title': str(lesson), 'length': lesson.video_length} for lesson in lessons]
    return HttpResponse(json.dumps(lessons), content_type='application/json')

# 更新视频长度
@superuser_required
def update_video_length(request, lesson_id):
    success = True
    lesson = Lesson.objects.get(pk=lesson_id)
    duration = 0
    try:
        resp = requests.get(lesson.video_url + '?avinfo', timeout=5)
        if resp.status_code == requests.codes.ok:
            data = json.loads(resp.text)
            duration = int(round(float(data['format']['duration'])))
            lesson.video_length = duration
            lesson.save()
    except Exception as e:
        logger.error(e)
        success = False
    return HttpResponse(json.dumps({'status': 'success' if success else 'fail', 'length': duration}), content_type='application/json')

# 加入班级界面
@superuser_required
def join_class_1_view(request):
    return render(request, 'mz_backend/join_class_1.html',locals())

@superuser_required
def join_class_2_view(request):
    account = request.POST.get('account', None)
    class_no = request.POST.get('class_no', None)
    try:
        user = UserProfile.objects.get(Q(email=account) | Q(mobile=account), Q(is_active=True))
        classobj = Class.objects.get(Q(coding=class_no), Q(is_active=True))
        if classobj.students.filter(id=user.id).count() == 0:
            if classobj.current_student_count >= classobj.student_limit:
                return render(request, 'mz_common/failure.html',{'reason':'当前班级人数已经达到人数上限'})
        # 判断用户是否已经在职业课程所属的某个班级
        if ClassStudents.objects.filter(Q(user=user), Q(student_class__career_course=classobj.career_course), ~Q(student_class=classobj)).count() > 0:
            class_students = ClassStudents.objects.get(Q(user=user), Q(student_class__career_course=classobj.career_course), ~Q(student_class=classobj))
            retval = render(request, 'mz_common/failure.html',{'reason':'该用户已经加入该职业课程下的其他班级('+class_students.student_class.coding+')，不能重复加班'})
            transaction.rollback()
            return retval
        # 查询该班级对应的职业课程及阶段信息
        stages = classobj.career_course.stage_set.all().order_by("index")
        for stage in stages:
            setattr(stage,"is_unlock",False)  # 默认未解锁阶段
            # 查询学生是否已经解锁阶段
            if UserUnlockStage.objects.filter(user=user, stage=stage).count() > 0:
                stage.is_unlock = True
    except UserProfile.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到该学生信息或学生被禁用'})
    except Class.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到该班级信息或班级被禁用'})
    except Exception as e:
        logger.error(e)
        return render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})
    return render(request, 'mz_backend/join_class_2.html',locals())

# 保存加入班级的信息
@transaction.commit_manually
@superuser_required
def join_class_save(request):
    user_id = request.POST.get("user_id", None)
    coding = request.POST.get("coding", None)
    stages = request.POST.getlist("stages")

    if not stages:
        retval = render(request, 'mz_common/failure.html',{'reason':'至少包含一个阶段信息'})
        transaction.rollback()
        return retval
    # 对应班级
    try:
        cur_class = Class.objects.get(coding=coding)
        if cur_class.students.filter(id=user_id).count() == 0:
            if cur_class.current_student_count >= cur_class.student_limit:
                retval = render(request, 'mz_common/failure.html',{'reason':'当前班级人数已经达到人数上限'})
                transaction.rollback()
                return retval
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'没有找到对应班级信息'})
        transaction.rollback()
        return retval

    # 对应用户
    try:
        user = UserProfile.objects.get(pk=user_id)
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'没有找到对应的用户信息'})
        transaction.rollback()
        return retval

    try:
        # 判断用户是否已经在职业课程所属的其他某个班级
        if ClassStudents.objects.filter(Q(user=user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class)).count() > 0:
            class_students = ClassStudents.objects.get(Q(user=user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class))
            retval = render(request, 'mz_common/failure.html',{'reason':'该用户已经加入该职业课程下的其他班级('+class_students.student_class.coding+')，不能重复加班'})
            transaction.rollback()
            return retval
        # 获取对应的阶段并添加到对应表
        for stage in stages:
            try:
                UserUnlockStage.objects.get(user=user, stage=stage)
            except UserUnlockStage.DoesNotExist:
                unlock_stage = UserUnlockStage()
                unlock_stage.user = user
                unlock_stage.stage_id = stage
                unlock_stage.save()
        # 查询没有在选择中的阶段列表，并从用户权限中删除该阶段
        UserUnlockStage.objects.filter(Q(user=user), Q(stage__career_course=cur_class.career_course), ~Q(stage__in=stages)).delete()
        #修改班级目前报名人数和更新学员到对应班级
        if cur_class.students.filter(pk=user.id).count() == 0:
            cur_class.current_student_count += 1
            cur_class.save()
            class_students = ClassStudents()
            class_students.student_class = cur_class
            class_students.user = user
            # 获取当前学力
            class_students.study_point = get_study_point(user, cur_class.career_course)
            class_students.save()

            #### 给学生发送通知消息 开始 ####

            # 发送站内信
            alert_msg = "恭喜你报名成功，请加入"+str(cur_class.coding)+"班QQ群"+str(cur_class.qq)+"开始和同学一起学习吧！"
            sys_send_message(0,user.id,1,alert_msg + "<a href='"+str(settings.SITE_URL)+"/lps/learning/plan/"+str(cur_class.career_course.id)+"'>进入课程LPS</a>")

            # 发送邮件
            if user.email is not None:
                try:
                    send_mail(settings.EMAIL_SUBJECT_PREFIX + "班级报名成功邮件", alert_msg, settings.EMAIL_FROM, [user.email])
                except Exception,e:
                    logger.error(e)

            # app推送
            app_send_message("系统消息", alert_msg, [user.username])

            #### 给学生发送通知消息 结束 ####

            #### 给对应带班老师发送通知消息 开始 ####
            alert_msg = "有新生报名了你的班级"+str(cur_class.coding)+"，<a href='"+str(settings.SITE_URL)+"/lps/user/teacher/class_manage/"+str(cur_class.id)+"/'>快去看看吧！</a>"
            sys_send_message(0,cur_class.teacher.id,1,alert_msg)

            alert_msg = "有新生报名了你的班级"+str(cur_class.coding)+"，快去看看吧！</a>"
            app_send_message("系统消息", alert_msg, [cur_class.teacher.username])
            #### 给对应带班老师发送通知消息 结束 ####

        #添加职业课程到我的课程
        if MyCourse.objects.filter(user=user, course=cur_class.career_course.id, course_type=2).count() == 0:
            my_course = MyCourse()
            my_course.user = user
            my_course.course = cur_class.career_course.id
            my_course.course_type = 2
            my_course.index = 1
            my_course.save()
        # 保存班级更新日志
        log = Log()
        log.userA = request.user.id
        log.userB = user_id
        log.log_type = '1'
        log.log_content = str(request.user.nick_name)+"更新"+str(user.nick_name)+"的班级信息：加入班级" \
                          +str(cur_class.coding)+"；解锁的阶段"+str(stages)
        log.save()

        retval = render(request, 'mz_common/success.html',{'reason':'加班信息更新成功'})
        transaction.commit()
    except Exception as e:
        print e
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'服务器出错啦'})
        transaction.rollback()
    return retval

# 学生退出班级第一步
@superuser_required
def quit_class_1_view(request):
    return render(request, 'mz_backend/quit_class_1.html',locals())

# 学生退出班级第二步
@superuser_required
def quit_class_2_view(request):
    account = request.POST.get('account', None)
    class_no = request.POST.get('class_no', None)
    try:
        user = UserProfile.objects.get(Q(email=account) | Q(mobile=account), Q(is_active=True))
        classobj = Class.objects.get(Q(coding=class_no), Q(is_active=True))
        if ClassStudents.objects.filter(user=user, student_class=classobj).count() == 0:
            return render(request, 'mz_common/failure.html',{'reason':'该学生不在这个班级中'})
    except UserProfile.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到该学生信息或学生被禁用'})
    except Class.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到该班级信息或班级被禁用'})
    except Exception as e:
        logger.error(e)
        return render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})
    return render(request, 'mz_backend/quit_class_2.html',locals())

# 学生退班处理
@transaction.commit_manually
@superuser_required
def quit_class_save(request):
    user_id = request.POST.get("user_id", None)
    coding = request.POST.get("coding", None)

    # 对应班级，报名人数减一
    try:
        cur_class = Class.objects.get(coding=coding)
        cur_class.current_student_count -= 1
        cur_class.save()
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'没有找到对应班级信息'})
        transaction.rollback()
        return retval

    # 对应用户
    try:
        user = UserProfile.objects.get(pk=user_id)
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'没有找到对应的用户信息'})
        transaction.rollback()
        return retval

    # 移除班级信息
    try:
        class_student = ClassStudents.objects.get(user=user, student_class=cur_class)
        class_student.delete()

        # 删除已经解锁的阶段
        stages_list = cur_class.career_course.stage_set.all().values_list("id")
        UserUnlockStage.objects.filter(Q(user=user), Q(stage__in=stages_list)).delete()

        # 删除对应的计划和计划相关的项
        Planning.objects.filter(Q(user=user),Q(career_course=cur_class.career_course)).delete()

        # 保存班级更新日志
        log = Log()
        log.userA = request.user.id
        log.userB = user.id
        log.log_type = '1'
        log.log_content = str(request.user.nick_name)+"更新"+str(user.nick_name)+"的班级信息：从" \
                          +str(cur_class.coding)+"班级移除；并取消了用户该职业课程对应的所有已经解锁的阶段"
        log.save()
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})
        transaction.rollback()
        return retval

    retval = render(request, 'mz_common/success.html',{'reason':'学生已经成功退出班级'})
    transaction.commit()
    return retval

# 学生转换班级第一步
@superuser_required
def change_class_1_view(request):
    return render(request, 'mz_backend/change_class_1.html',locals())

# 学生转换班级第二步
@superuser_required
def change_class_2_view(request):
    account = request.POST.get('account', None)
    old_class_no = request.POST.get('old_class_no', None)
    new_class_no = request.POST.get('new_class_no', None)
    try:
        user = UserProfile.objects.get(Q(email=account) | Q(mobile=account), Q(is_active=True))
        old_classobj = Class.objects.get(Q(coding=old_class_no), Q(is_active=True))
        new_classobj = Class.objects.get(Q(coding=new_class_no), Q(is_active=True))
        if old_classobj == new_classobj:
            return render(request, 'mz_common/failure.html',{'reason':'原班级和新班级不能是同一个班级'})
        if new_classobj.current_student_count >= new_classobj.student_limit:
            return render(request, 'mz_common/failure.html',{'reason':'新班级报名人数已达上限'})
        if old_classobj.career_course != new_classobj.career_course:
            return render(request, 'mz_common/failure.html',{'reason':'不是同一个职业课程下的班级，不能转班'})
        if ClassStudents.objects.filter(user=user, student_class=old_classobj).count() == 0:
            return render(request, 'mz_common/failure.html',{'reason':'该学生不在原班级里面'})
        if ClassStudents.objects.filter(user=user, student_class=new_classobj).count() > 0:
            return render(request, 'mz_common/failure.html',{'reason':'该学生已经在新班级里面了'})
    except UserProfile.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到该学生信息'})
    except Class.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'未查询到班级信息'})
    except Exception as e:
        logger.error(e)
        return render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})
    return render(request, 'mz_backend/change_class_2.html',locals())

# 学生转班处理
@transaction.commit_manually
@superuser_required
def change_class_save(request):
    user_id = request.POST.get('user_id', None)
    old_coding = request.POST.get('old_coding', None)
    new_coding = request.POST.get('new_coding', None)
    retval = None
    try:
        user = UserProfile.objects.get(Q(pk=user_id), Q(is_active=True))
        old_classobj = Class.objects.get(Q(coding=old_coding), Q(is_active=True))
        new_classobj = Class.objects.get(Q(coding=new_coding), Q(is_active=True))
        if old_classobj == new_classobj:
            retval = render(request, 'mz_common/failure.html',{'reason':'原班级和新班级不能是同一个班级'})
        elif new_classobj.current_student_count >= new_classobj.student_limit:
            retval = render(request, 'mz_common/failure.html',{'reason':'新班级报名人数已达上限'})
        elif old_classobj.career_course != new_classobj.career_course:
            retval = render(request, 'mz_common/failure.html',{'reason':'不是同一个职业课程下的班级，不能转班'})
        elif ClassStudents.objects.filter(user=user, student_class=old_classobj).count() == 0:
            retval = render(request, 'mz_common/failure.html',{'reason':'该学生不在原班级里面'})
        elif ClassStudents.objects.filter(user=user, student_class=new_classobj).count() > 0:
            retval = render(request, 'mz_common/failure.html',{'reason':'该学生已经在新班级里面了'})
    except UserProfile.DoesNotExist:
        retval = render(request, 'mz_common/failure.html',{'reason':'未查询到该学生信息或学生被禁用'})
    except Class.DoesNotExist:
        retval = render(request, 'mz_common/failure.html',{'reason':'未查询到班级信息或班级被禁用'})
    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})

    if retval:
        transaction.rollback()
        return retval

    # 执行班级转换的操作
    try:
        class_student = ClassStudents.objects.get(user=user, student_class=old_classobj)
        class_student.student_class = new_classobj
        class_student.save()
        # 原班级报名人数减一
        old_classobj.current_student_count -= 1
        old_classobj.save()
        # 新班级报名人数加一
        new_classobj.current_student_count += 1
        new_classobj.save()

        # 保存转换班级日志
        log = Log()
        log.userA = request.user.id
        log.userB = user.id
        log.log_type = '1'
        log.log_content = str(request.user.nick_name)+"更新"+str(user.nick_name)+"的班级信息：从" \
                          +str(old_classobj.coding)+"班级转换到"+str(new_classobj.coding)
        log.save()

    except Exception as e:
        logger.error(e)
        retval = render(request, 'mz_common/failure.html',{'reason':'服务器出错了'})
        transaction.rollback()
        return retval

    retval = render(request, 'mz_common/success.html',{'reason':'学生已经成功转换班级'})
    transaction.commit()
    return retval

# 订单查询
def order_list_view(request):
    if request.user.is_authenticated():
        if request.user.username != "919769614@qq.com" and \
            request.user.username != "admin@maiziedu.com" and \
            request.user.username != "editor@maiziedu.com":
            return render(request, 'mz_common/failure.html',{'reason':'权限不足，不能访问。'})
    else:
        return render(request, 'mz_common/failure.html',{'reason':'还未登录，请登录后再刷新该页面。'})

    keywords = request.REQUEST.get("keywords","")
    pay_status = request.REQUEST.get("pay_status","-1")
    if pay_status!='-1' and pay_status !='':
        order_list = UserPurchase.objects.filter(
            Q(user__username__icontains=keywords)|
            Q(order_no__icontains=keywords)|
            Q(trade_no__icontains=keywords),
            Q(pay_status=pay_status)
        ).order_by("-id")
    else:
        order_list = UserPurchase.objects.filter(
            Q(user__username__icontains=keywords)|
            Q(order_no__icontains=keywords)|
            Q(trade_no__icontains=keywords)
        ).order_by("-id")
    paginator = Paginator(order_list, 20)
    try:
        current_page = int(request.GET.get('page', '1'))
        order_list = paginator.page(current_page)
    except(PageNotAnInteger, ValueError):
        order_list = paginator.page(1)
    except EmptyPage:
        order_list = paginator.page(paginator.num_pages)
    return render(request, 'mz_backend/order_list.html', locals())

#生成优惠码
@superuser_required
def coupon_list_view(request):
    Money = request.REQUEST.get("Money","")
    if Money !="":
        c = Coupon()
        c.surplus = 100
        c.coupon_price = str(Money)
        c.save()
        save_obj = Coupon.objects.order_by('-id')[0]
        for i in range(100):
            cd = Coupon_Details()
            code_sno = generate_random(16,1)
            cd.code_sno = code_sno.upper()
            cd.coupon = save_obj
            cd.use_time = '0000-00-00 00:00:00'
            try:
                cd.save()
            except:
                i = i - 1
        status = '优惠码生成成功!'
        return render(request, 'mz_backend/coupon_list.html', locals())    
    else:
        coupon_list = Coupon.objects.order_by("id")
        paginator = Paginator(coupon_list, 20)
        try:
            current_page = int(request.GET.get('page', '1'))
            coupon_list = paginator.page(current_page)
        except(PageNotAnInteger, ValueError):
            coupon_list = paginator.page(1)
        except EmptyPage:
            coupon_list = paginator.page(paginator.num_pages)
        return render(request, 'mz_backend/coupon_list.html', locals())

# 优惠码列表
@superuser_required
def coupon_list_details(request,coupon_id):
    if coupon_id !="" :
        coupon_details = Coupon_Details.objects.filter(Q(coupon_id=coupon_id)).order_by("is_use","is_lock","id")
    return render(request, 'mz_backend/coupon_list_details.html', locals())

# 后台管理界面首页
@superuser_required
def admin_main(request):
    return render(request, 'mz_backend/main.html',locals())


# 同步主站到论坛的头像
@superuser_required
def sync_avatar_view(request):
    return render(request, 'mz_backend/sync_avatar_view.html', locals())

# 返回所有影响到的用户
@superuser_required
def get_user_list(request):
    min_id = request.GET.get('min_id', None)
    count = request.GET.get('count', None)
    if min_id:
        users = UserProfile.objects.filter(uid__gte=min_id).order_by('uid').all()
    else:
        users = UserProfile.objects.filter(uid__gte=0).order_by('uid').all()

    if count and int(count) < len(users):
        users = users[0:int(count)]
    users = [user.uid for user in users]
    return HttpResponse(json.dumps(users), content_type='application/json')

# 更新一组用户的头像
@superuser_required
def sync_avatar(request):
    success = True
    print request.POST['user_uids']
    user_uids = json.loads(request.POST['user_uids'])
    users = UserProfile.objects.filter(uid__in=user_uids)

    try:
        for user in users:
            if user.avatar_url != 'avatar/default_big.png':
                sync_avatar_action(user.uid, unicode(user.avatar_url))
    except Exception as e:
        logger.error(e)
        print e
        success = False
    sync_avatar_action(user.uid, unicode(user.avatar_url))
    return HttpResponse(json.dumps({'status': 'success' if success else 'fail'}), content_type='application/json')


def sync_avatar_action(forum_uid, avatar):
    import os
    from django.conf import settings
    import shutil

    root_path = settings.PROJECT_ROOT
    filename, extension = os.path.splitext(avatar)
    filename = 'uploads/' + filename
    name_parts = filename.split('_')
    size = name_parts[-1]
    pure_name = '_'.join(name_parts[:-1])

    if size != 'big':
        return

    forum_uid = "%09d" % forum_uid
    dir1 = forum_uid[0:3]
    dir2 = forum_uid[3:5]
    dir3 = forum_uid[5:7]
    prefix = forum_uid[-2:]

    for size in ('big', 'middle', 'small'):
        main_avatar_path = root_path + "/" + pure_name + '_' + size + extension

        forum_avatar_dir_path = root_path + '/forum/uc_server/data/avatar/' + dir1 + '/' + dir2 + '/' + dir3

        if not os.path.exists(forum_avatar_dir_path):
            os.makedirs(forum_avatar_dir_path)

        avatar_name = prefix + '_avatar_' + size + extension
        forum_avatar_path = forum_avatar_dir_path + '/' + avatar_name
        if os.path.exists(forum_avatar_path):
            os.remove(forum_avatar_path)

        shutil.copyfile(main_avatar_path, forum_avatar_path)


# 显示当前的推荐阅读列表
@superuser_required
def recommend_reading_index(request):
    #messages.info(request, 'test')
    reading_type = request.REQUEST.get("reading_type", None)
    if reading_type and reading_type != '-1':
        readings = RecommendedReading.objects.filter(reading_type=reading_type)
    else:
        readings = RecommendedReading.objects.all()
    rearranged_readings = {RecommendedReading.ACTIVITY: [], RecommendedReading.NEWS: [], RecommendedReading.DISCUSS: []}
    for reading in readings:
        rearranged_readings[reading.reading_type] = reading
    return render(request, 'mz_backend/recommended_reading_index.html',
                  {'readings': readings, 'rearranged_readings': rearranged_readings,
                   'choices': RecommendedReading.READING_TYPES})

class RecommendedReadingForm(ModelForm):
    class Meta:
        model = RecommendedReading
        files = ['reading_type', 'title', 'url']
        labels = {
            'reading_type': _('类型'),
            'title': _('标题'),
            'url': _('链接')
        }
# 增加或者编辑推荐阅读的文章
@superuser_required
def recommend_reading_edit(request, reading_id=None):
    template_vars = {'choices': RecommendedReading.READING_TYPES}
    if request.method == 'POST':
        reading = None
        if reading_id:
            try:
                reading = RecommendedReading.objects.get(id=reading_id)
            except Exception as e:
                logger.error(e)
        form = RecommendedReadingForm(request.POST, instance=reading)
        if form.is_valid():
            form.save()
            template_vars['messages'] = '保存成功'
        else:
            template_vars['errors'] = form.errors

    if reading_id:
        try:
            reading = RecommendedReading.objects.get(pk=reading_id)
            template_vars['reading'] = reading
        except Exception as e:
            print e
            logger.error(e)
    return render(request, 'mz_backend/recommended_reading_edit.html', template_vars)

# 删除推荐阅读的文章
@superuser_required
def recommend_reading_delete(request, reading_id):
    try:
        reading = RecommendedReading.objects.get(id=reading_id)
        reading.delete()
        #messages.info(request, '测试消息')
    except Exception as e:
        logger.error(e)

    url = reverse('backend:recommend_reading_index')
    return HttpResponseRedirect(url)

# 批量更新用户的uuid
@superuser_required
def update_uuid(request):
    user_list = UserProfile.objects.filter(uuid=None)
    for user in user_list:
        user.uuid = str(uuid.uuid4()).replace('-', '')
        user.save()
    return render(request, 'mz_common/success.html',{'reason':'uuid更新成功'})

# 直播室列表
@superuser_required
def live_room_list(request):
    keywords = request.REQUEST.get("keywords","")
    live_is_open = request.REQUEST.get("live_is_open","-1")
    if live_is_open!='-1' and live_is_open !='':
        room_list = LiveRoom.objects.filter(
            Q(live_id__icontains=keywords)|
            Q(live_class__coding__icontains=keywords),
            Q(live_is_open=live_is_open)
        ).order_by("-id")
    else:
        room_list = LiveRoom.objects.filter(
            Q(live_id__icontains=keywords)|
            Q(live_class__coding__icontains=keywords)
        ).order_by("-id")
    paginator = Paginator(room_list, 20)
    try:
        current_page = int(request.GET.get('page', '1'))
        room_list = paginator.page(current_page)
    except(PageNotAnInteger, ValueError):
        room_list = paginator.page(1)
    except EmptyPage:
        room_list = paginator.page(paginator.num_pages)
    return render(request, 'mz_backend/live_room_list.html', locals())

# 创建直播室
@superuser_required
def create_live_room(request):
    if request.method == "POST":
        try:
            # 接受当前的班级号
            coding = request.REQUEST.get("coding",None)
            classobj = Class.objects.get(coding=coding)
            if LiveRoom.objects.filter(live_class=classobj).count() > 0:
                return render(request, 'mz_common/failure.html',{'reason':'该班级已经创建直播室，不能重复创建。'})
            # 创建直播室接口处理地址
            url = settings.LIVE_ROOM_CREATE_API
            values = {
                'loginName':settings.LIVE_ROOM_USERNAME,
                'password':settings.LIVE_ROOM_PASSWORD,
                'sec':'true',
                'subject':classobj.coding,
                'startDate':datetime.now(),
                'scene':1,
                'speakerInfo':classobj.teacher.nick_name+','+classobj.teacher.description,
                'scheduleInfo':classobj.career_course.description,
                'studentToken':generate_random(6,0),
                'description':'这里是'+coding+'班的直播课堂，欢迎加入课堂',
                'realtime':True,
                }
            data = urllib.urlencode(values)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            result = json.loads(response.read())
            # 保存直播室相关数据
            if result['code'] == '0':
                live_room = LiveRoom()
                live_room.live_id = result['id']
                live_room.live_code = result['number']
                live_room.assistant_token = result['assistantToken']
                live_room.student_token = result['studentToken']
                live_room.teacher_token = result['teacherToken']
                live_room.student_client_token = result['studentClientToken']
                live_room.student_join_url = result['studentJoinUrl']
                live_room.teacher_join_url = result['teacherJoinUrl']
                live_room.live_class = classobj
                live_room.save()
            else:
                return render(request, 'mz_common/failure.html',{'reason':'直播室创建失败。错误代码：'+str(result['code'])})
        except Class.DoesNotExist:
            return render(request, 'mz_common/failure.html',{'reason':'没有该班级。'})
        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':'服务器出错。'})
        return render(request, 'mz_common/success.html',{'reason':'直播室创建成功。'})
    else:
        return render(request, 'mz_backend/live_room_add.html')

# 修改直播室
@superuser_required
def update_live_room(request):
    if request.method == "POST":
        try:
            live_id = request.REQUEST.get("live_id",None)
            coding = request.REQUEST.get("coding",None)
            classobj = Class.objects.get(coding=coding)
            if LiveRoom.objects.filter(live_class=classobj).count() > 0:
                return render(request, 'mz_common/failure.html',{'reason':'新班级已经有对应的直播室。'})
            # 检查新班级是否和老班级同属于同一个职业课程
            live_room = LiveRoom.objects.get(live_id=live_id)
            if live_room.live_class.career_course != classobj.career_course:
                return render(request, 'mz_common/failure.html',{'reason':'新班级和老班级必须同属于同一职业课程。'})
            # 修改直播室接口处理地址
            url = settings.LIVE_ROOM_UPDATE_API
            values = {
                'loginName':settings.LIVE_ROOM_USERNAME,
                'password':settings.LIVE_ROOM_PASSWORD,
                'sec':'true',
                'subject':classobj.coding,
                'startDate':live_room.date_publish,
                'teacherToken':live_room.teacher_token,
                'assistantToken':live_room.assistant_token,
                'studentClientToken':live_room.student_client_token,
                'speakerInfo':classobj.teacher.nick_name+','+classobj.teacher.description,
                'scheduleInfo':classobj.career_course.description,
                'description':'这里是'+coding+'班的直播课堂，欢迎加入课堂',
                'id':live_id,
                }
            data = urllib.urlencode(values)
            req = urllib2.Request(url, data)
            response = urllib2.urlopen(req)
            result = json.loads(response.read())
            # 保存直播室相关数据
            if result['code'] == '0':
                # 修改对应的班级信息
                live_room.live_class = classobj
                live_room.save()
            else:
                return render(request, 'mz_common/failure.html',{'reason':'直播室创建失败。错误代码：'+str(result['code'])})
        except LiveRoom.DoesNotExist:
            return render(request, 'mz_common/failure.html',{'reason':'没有对应的直播室。'})
        except Class.DoesNotExist:
            return render(request, 'mz_common/failure.html',{'reason':'没有对应的新班级。'})
        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':'服务器出错。'})
        return render(request, 'mz_common/success.html',{'reason':'直播室修改成功。'})
    else:
        # 获取直播室ID
        return render(request, 'mz_backend/live_room_update.html',locals())

# 历史消息列表
@superuser_required
def msg_send_list(request):
    keywords = request.REQUEST.get("keywords","")
    sendtarget = request.REQUEST.get("sendtarget","")

    if sendtarget!='-2' and sendtarget !='':
        msg_list = MsgBox.objects.filter(
            Q(content__icontains=keywords),
            Q(sendtarget=sendtarget)
        ).order_by("-id")
    else:
        msg_list = MsgBox.objects.filter(
            Q(content__icontains=keywords)
        ).order_by("-id")

    paginator = Paginator(msg_list, 20)
    try:
        current_page = int(request.GET.get('page', '1'))
        msg_list = paginator.page(current_page)
    except(PageNotAnInteger, ValueError):
        msg_list = paginator.page(1)
    except EmptyPage:
        msg_list = paginator.page(paginator.num_pages)
    return render(request, 'mz_backend/msg_send_list.html', locals())

#定义App推送方法
def PushMsgToApp(content,sendtarget):
    acountlist=[]
    if sendtarget == "-1":
        app_send_message("系统消息",content,acountlist)
        return
    users = UserProfile.objects.filter(is_active = True).all()
    for user in users:
        if (sendtarget == "0" and user.is_student())|(sendtarget == "1" and user.is_teacher()):
            acountlist.append(user.username)
    try:
        app_send_message("系统消息",content,acountlist)
    except:
        pass

#定义站内信推送方法
def PushMsgToSite(content, sendtarget):
    users = UserProfile.objects.filter(is_active = True).all()
    for user in users:
        if (sendtarget == "-1")|(sendtarget == "0" and user.is_student())|(sendtarget == "1" and user.is_teacher()):
            sys_send_message(0,user.id,1,content)

def PushMsgToEmail(content, sendtarget):
    emaillist=[]
    users = UserProfile.objects.filter(is_active = True).all()
    for user in users:
        if (sendtarget == "-1")|(sendtarget == "0" and user.is_student())|(sendtarget == "1" and user.is_teacher()):
            if user.email:
                emaillist.append(user.email)
    try:
        send_mail(settings.EMAIL_SUBJECT_PREFIX + "推送消息",content,settings.EMAIL_FROM,emaillist)
    except:
        pass

# 发送消息
@superuser_required
def create_msg(request):
    if request.method == "POST":
        try:
            sendtarget=request.REQUEST.get("sendtarget",-1)
            content=request.REQUEST.get("content","")
            is_sendmsg=request.REQUEST.get("is_sendmsg",False)
            is_sendemail=request.REQUEST.get("is_sendemail",False)
            is_sendappmsg=request.REQUEST.get("is_sendappmsg",False)

            if is_sendappmsg:
                PushMsgToApp(content,sendtarget)
            if is_sendmsg:
                PushMsgToSite(content, sendtarget)
            if is_sendemail:
                PushMsgToEmail(content, sendtarget)

        except Exception as e:
            logger.error(e)
            return render(request, 'mz_common/failure.html',{'reason':'服务器出错。'})
        msg= MsgBox()
        msg.sendtarget=sendtarget
        msg.content=content
        msg.is_sendmsg=is_sendmsg
        msg.is_sendemail=is_sendemail
        msg.is_sendappmsg=is_sendappmsg
        msg.save()
        return render(request, 'mz_common/success.html',{'reason':'消息发送成功。'})
    else:
        return render(request, 'mz_backend/msg_send_add.html')

#######################  高校后台代码 开始  ###############################

# 高校用户列表
def acauser_list(request):
    if request.user.is_authenticated():
        if request.user.username != "919769614@qq.com" and \
            request.user.username != "admin@maiziedu.com" and \
            request.user.username != "editor@maiziedu.com":
            return render(request, 'mz_common/failure.html',{'reason':'权限不足，不能访问。'})
    else:
        return render(request, 'mz_common/failure.html',{'reason':'还未登录，请登录后再刷新该页面。'})

    # 获取大学列表
    university_list = AcademicOrg.objects.filter(level=1)

    keywords = request.REQUEST.get("keywords", "")
    university = request.REQUEST.get("university", "-1")
    acausers = get_acauser_list(keywords, university)

    paginator = Paginator(acausers, 20)
    try:
        current_page = int(request.GET.get('page', '1'))
        acausers = paginator.page(current_page)
    except(PageNotAnInteger, ValueError):
        acausers = paginator.page(1)
    except EmptyPage:
        acausers = paginator.page(paginator.num_pages)

    return render(request, 'mz_backend/acauser_list.html', locals())

# 删除高校用户（高校信息）
def acauser_delete(request):
    aid = request.REQUEST.get("aid", None)
    try:
        AcademicUser.objects.get(pk=aid).delete()
    except Exception as e:
        logger.error(e)

    return HttpResponseRedirect(reverse('backend:acauser_list'))

# 高校用户导入
@csrf_exempt
@transaction.commit_manually
def acauser_import(request):
    try:

        # 上传excel文件
        files = request.FILES.get("Filedata",None)
        file_name=str(uuid.uuid1())+"."+str(files.name.split(".")[-1])
        path_file=os.path.join(settings.MEDIA_ROOT, 'temp', file_name)
        open(path_file, 'wb').write(files.file.read())

        # 写入excel文件内容到数据库
        data = xlrd.open_workbook(path_file)
        table = data.sheets()[0]
        for i in range(table.nrows):
            if i == 0: continue
            table_row = table.row_values(i)
            # 0 姓名 1 学号 2 大学 3 学院 4 专业
            # 获取大学对象
            university = AcademicOrg.objects.get(name=table_row[2].strip(), level=1, parent=None)
            # 获取学院对象
            college = AcademicOrg.objects.get(name=table_row[3].strip(), level=2, parent=university)
            # 获取专业对象
            academic_course = AcademicCourse.objects.get(name=table_row[4].strip(), owner=college)
            # 增加高校用户对象
            academic_user = AcademicUser()
            academic_user.user_no = int(table_row[1])
            academic_user.stu_name = table_row[0].strip()
            academic_user.academic_course = academic_course
            academic_user.owner_college = college
            academic_user.owner_university = university
            # 唯一标识码
            academic_user.verify_code = generate_random(8, 1)
            academic_user.save()
        transaction.commit()
    except Exception as e:
        logger.error(e)
        transaction.rollback()
        return HttpResponse("failure", content_type="text/plain")
    return HttpResponse("success", content_type="text/plain")

# 高校用户导出
@csrf_exempt
def acauser_export(request):
    try:
        # 导出当前查询结果并保存为excel文件并输出下载
        keywords = request.REQUEST.get("keywords", "")
        university = request.REQUEST.get("university", "-1")
        acausers = get_acauser_list(keywords, university)

        file_name = str(uuid.uuid1())+".xls"
        path_file = os.path.join(settings.MEDIA_ROOT, 'temp', file_name)
        book = xlwt.Workbook()
        sheet1 = book.add_sheet(u'高校用户')
        sheet1.col(0).width = 3000
        sheet1.col(1).width = 4000
        sheet1.col(2).width = 5000
        sheet1.col(3).width = 5000
        sheet1.col(4).width = 5000
        sheet1.col(5).width = 3000
        row = sheet1.row(0)
        row.write(0, u'姓名')
        row.write(1, u'学号')
        row.write(2, u'大学')
        row.write(3, u'学院')
        row.write(4, u'专业')
        row.write(5, u'唯一标识码')

        i = 1
        for acauser in acausers:
            if acauser.user_no is None or acauser.user_no == "" or \
                            acauser.verify_code is None or acauser.verify_code == "" or \
                            acauser.academic_course is None:
                continue

            row = sheet1.row(i)
            row.write(0, unicode(acauser.stu_name))
            row.write(1, unicode(acauser.user_no))
            row.write(2, unicode(acauser.owner_university.name))
            row.write(3, unicode(acauser.owner_college.name))
            row.write(4, unicode(acauser.academic_course.name))
            row.write(5, unicode(acauser.verify_code))
            i+=1

        book.save(path_file)
        return HttpResponseRedirect('/uploads/temp/'+file_name)
    except Exception as e:
        logger.error(e)
    return HttpResponse("failure", content_type="text/plain")

# 根据查询条件获取用户列表
def get_acauser_list(keywords, university):

    if university != '-1' and university != '':
        acausers = AcademicUser.objects.filter(
            Q(user__username__icontains=keywords)|
            Q(academic_course__name__icontains=keywords)|
            Q(owner_college__name__icontains=keywords, owner_college__level=2)|
            Q(stu_name__icontains=keywords)|
            Q(user_no__icontains=keywords),
            Q(owner_university__id=university, owner_university__level=1)
        ).order_by("-id")
    else:
        acausers = AcademicUser.objects.filter(
            Q(user__username__icontains=keywords)|
            Q(academic_course__name__icontains=keywords)|
            Q(owner_college__name__icontains=keywords, owner_college__level=2)|
            Q(stu_name__icontains=keywords)|
            Q(user_no__icontains=keywords)
        ).order_by("-id")

    return acausers

#######################  高校后台代码 结束  ###############################

# 清除缓存
def clear_cache(request):
	cache._cache.flush_all()
	return render(request, 'mz_common/success.html',{'reason':'缓存清除成功。'})