# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse,HttpResponsePermanentRedirect,HttpResponseRedirect
from django.db import models
from django.conf import settings
from aca_course.models import *
from mz_pay.models import *
from mz_user.models import *

from mz_lps.models import *

from mz_lps.models import Class
from mz_user.models import UserProfile
from mz_pay.models import UserPurchase
from datetime import datetime
from datetime import timedelta
from django.dispatch import Signal
from django.db.models.signals import post_save
import time

# Create your models here.
import logging, os, json, re
from django.db.models.signals import *


# class StudentCard(models.Model):
#     user=models.ForeignKey(settings.AUTH_USER_MODEL, related_name=u"user", verbose_name=u"用户")
#     user_class=models.ForeignKey(Class, verbose_name=u"班级")
#     stage_index=models.IntegerField(u"阶段索引", null=False, blank=False)
#     stage_id=models.IntegerField(u"阶段ID", null=False, blank=False)
#     course_index=models.IntegerField(u"课程索引", null=False, blank=False)
#     course_id=models.IntegerField(u"课程ID", null=False, blank=False)
#     l_index=models.IntegerField(u"章节或项目索引", null=True, blank=True)
#     l_id=models.IntegerField(u"章节或项目ID", null=False, blank=False)
#     l_type=models.SmallIntegerField(u"内容类型", choices=((0,"视频+[作业]"),(1,"项目"),),default=0)
#     is_done=models.BooleanField(u"是否完成", default=False)
#     usertask=models.ForeignKey(u"相关任务", )
#     relate_id
#     relate_type #RELATE_TYPE
#     is_plan #是否计划
#     is_done #是否完成
#     is_current #是否当前正在计划的任务
#     is_addin #是否后期插入
#     rebuild_count
#     plan_datetime
#     done_datetime #完成时间


# 每周班会
class ClassMeetingTask(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, related_name=u"user", verbose_name=u"用户")
    user_class=models.ForeignKey(Class, verbose_name=u"班级")
    create_datetime=models.DateTimeField(u"创建时间",auto_now_add=True)
    startline=models.DateTimeField(u"班会时间",null=True, blank=True) #开始日期-截至日期 是每周任务必须的,除了评测模块，其他任务的时间为00：00：00
    status=models.SmallIntegerField(u"状态",default=1, choices=((0,"未开始"),(1,"已结束"),(2,"进行中")))
    finish_date=models.DateField(u"实际完成时间", null=True, blank=True)
    content=models.CharField(u"内容", null=True,blank=True, max_length=100)

    class Meta:
        verbose_name = "直播班会用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)


    #用户任务
class UserTask(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u"用户")
    create_datetime=models.DateTimeField(u"创建时间",auto_now_add=True)
    startline=models.DateTimeField(u"开始日期",null=True, blank=True) #开始日期-截至日期 是每周任务必须的,除了评测模块，其他任务的时间为00：00：00
    deadline=models.DateTimeField(u"截至日期", null=True, blank=True) #WeekUserTask截至日期为空，去班会时间为截至日期
    status=models.SmallIntegerField(u"状态",default=1, choices=((0,"未完成"),(1,"已完成"),(2,"进行中")))


    class Meta:
        verbose_name = "用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class JoinClassUserTask(UserTask):
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "加入班级用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class ViewContractUserTask(UserTask):
    user_class=models.ForeignKey(Class, verbose_name=u"班级")
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "查看协议用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class FullProfileUserTask(UserTask):
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "完善资料用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class CourseUserTask(UserTask):
    user_class=models.ForeignKey(Class, verbose_name=u"班级")
    #complete_degree= models.IntegerField(u"完成度", default=0) # 0~100
    rank_in_class=models.IntegerField(u"班级排名", default=0)
    plan_study_time=models.IntegerField(u"计划学时",default=15)
    real_study_time=models.IntegerField(u"计划内实际学时",default=0)
    real_study_time_ext=models.IntegerField(u"额外学时",default=0)
    total_study_time=models.IntegerField(u"总学时",default=0)
    ava_score=models.IntegerField(u"平均评测分",default=0)
    plan_gradute_time=models.DateField(u"预计毕业时间",null=True,blank=True)
    study_point=models.IntegerField(u"累计学力",null=True,blank=True)
    relate_content=models.CharField(u"相关内容",null=True,blank=True,max_length=10000)
    comment_count=models.IntegerField(u"评论次数",default=-1)
    liveroom_comment_count=models.IntegerField(u"直播课评论次数",default=-1)
    week=models.ForeignKey(ClassMeetingTask,null=True,blank=True)

    class Meta:
        verbose_name = "课程模块用户任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class ReadMeUserTask(UserTask):
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "阅读须知老师任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class TeacherProfileUserTask(UserTask):
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "完善资料老师任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

class StuStatusUserTask(UserTask):
    STATUS_TYPE = {
        (1,"完成项目制作"),
        (2,"进度落后太多"),
        (3,"通过课程"),
        (4,"未通过课程"),
        }
    stu_status=models.SmallIntegerField(u"提醒类型",choices=STATUS_TYPE)
    student_id=models.IntegerField(u"学生ID",null=False,blank=False)
    relate_id=models.IntegerField(u"相关ID",null=True,blank=True)
    finish_date=models.DateField(u"实际完成日期", null=True, blank=True)
    class Meta:
        verbose_name = "学生状态老师任务"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 用户素质项得分
class UserQualityModelItems(models.Model):
    QUALITY_TYPE = {
        (1,"执行力"),
        (2,"沟通力"),
        (3,"主动性"),
        }
    user=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u"用户")
    quality_type=models.SmallIntegerField(u"素质类型",choices=QUALITY_TYPE)
    subject_score=models.IntegerField(u"老师打分", default=-1)
    score= models.IntegerField(u"素质项分数", default=-1)
    week=models.ForeignKey(ClassMeetingTask,null=True,blank=True)
    calc_datetime=models.DateTimeField(u"计算时间", auto_now_add=True)

    class Meta:
        verbose_name = "用户模型项"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)


# 队列，用来做后台计算的排队
class AsyncMethod(models.Model):
    CALC_TYPES = (
        ('1','计算学力'),
        ('2','完成评测模块'),
    )
    name = models.CharField(u"名称",null = True,blank= True, max_length=10)
    methods= models.CharField(u"方法体", null=True, blank=True, max_length=300)
    calc_type= models.SmallIntegerField(u"计算类型",choices=CALC_TYPES)
    calc_datetime=models.DateTimeField(u"计算时间",null=True,blank=True)
    submit_datetime=models.DateTimeField(u"提交时间",auto_now_add=True)
    priority=models.SmallIntegerField(u"优先级",default=3) #1,2,3:1最高
    is_calc=models.BooleanField(u"已计算",default=False) #当已计蒜=False，但是计蒜时间有值，表示预期执行的时间

    class Meta:
        verbose_name = u'异步方法'
        verbose_name_plural = verbose_name
        ordering = ['-priority', 'submit_datetime', 'id']
    def __unicode__(self):
        return self.name

ISOTIMEFORMAT='%Y-%m-%d'

def _create_class(**kwargs):
    obj=kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']
    ret=True
    if created and (obj is AcademicCourse):
        inst=kwargs['instance']
        if not len(AcademicClass.objects.filter(career_course=inst)):
            cl = AcademicClass();
            cl.coding = inst.short_name+'001'

            cl.date_open = time.strftime(ISOTIMEFORMAT)
            cl.student_limit = 100000
            cl.qq="###"
            cl.career_course=inst
            cl.save()
    else:
        ret=False
    return ret


# function:推送加入班级任务
# param: **kwargs
# ret : Task_id
def _need_join_class(**kwargs):
    obj = kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']
        if created and (obj is UserProfile):
            instance = kwargs['instance']
            task_lsit = JoinClassUserTask.objects.filter(user = instance)
            if len(task_lsit) < 1:
                now = datetime.now()
                aDay = timedelta(days=3)
                now = now + aDay
                return JoinClassUserTask.objects.create(
                    user = instance,create_datetime = datetime.now(),startline = datetime.now(),deadline = now,status = 2)
    return 0




#function:当支付成功时,触发更新加入班级事件,且时间不超过三天,将其状态置为1.完成
#param : **kwargs
#ret : task_id 返回被更新任务的id
#如果正确产生UserTask，ret=UserTask实例的ID
def _update_join_class(**kwargs):

    obj = kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']
        if created and (obj is UserPurchase):
            #更新状态前必须检查状态id必须为2.进行中
            #所需条件  1.用户id
            instance = kwargs['instance']
            user = instance.user
            task_list = JoinClassUserTask.objects.filter(user = user,status = 2)
            if len(task_list) == 1:  #确定在数据库里面只有一条记录
                task = task_list[0]
                task.status = 1
                task.save()
                return task.id
    return 0


#查看学习协议
#如果正确产生UserTask，ret=UserTask实例的ID
def _need_view_contract(**kwargs):
    #需要的数据,用户id,通过UserPurchase外键关系获得用户id
    obj = kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']
        if created and (obj is UserPurchase): #报班的时候查看学习协议
            instance = kwargs['instance']
            contract = ViewContractUserTask.objects.filter(user = instance.user)
            if len(contract) < 1:
                user = instance.user
                now = datetime.now()
                aDay = timedelta(days=3)
                now = now + aDay
                #获取班级
                classs = user.students.all()[0]
                return ViewContractUserTask.objects.create(
                    user = user,create_datetime = datetime.now(),startline = datetime.now(),deadline = now,status = 2,user_class = classs)
    return 0
#更新学习协议
def _update_view_contract(**kwargs):
    ret=0
    #如果正确产生UserTask，ret=UserTask实例的ID
    return ret

#支付成功，创建提醒完善资料任务
#资料全部字段完善后，更改状态为完善

import datetime

import  time
def _need_full_profile(**kwargs):


    obj=kwargs['sender']

    save = False

    if kwargs.has_key('created'):
        save = kwargs['created']

        try:
            if save and (obj is UserPurchase):#如果支付成功会触发监听，随后创建一条提醒完善资料任务
                inst=kwargs['instance']

                list = FullProfileUserTask.objects.all()

                if len(list)!=0:#如果FullProfileUserTask，列表为空说明还没有写入，为空就写入

                    p=FullProfileUserTask(finish_date=datetime.datetime.now(),user_id=inst.user_id)#写入FullProfileUserTask一条创建时间字段
                    # add.finish_date=datetime.datetime.now()
                    #
                    # add.save()

                    p.save()
                    s=UserTask(status=0,user_id=inst.user_id)#写入完善资料为0，未完成
                    s.save()



                    return p.id#成功就返回1，失败返回0
                else:
                    return 0
            else:
                return -2
        except Exception as e:
              print e
              return  -3
    else:
        return -1#异常返回负数





def _update_full_profile(**kwargs):




    obj=kwargs['sender']

    try:

        if kwargs.has_key('created'):
            save = False
            save = kwargs['created']

            if save and (obj is UserProfile):#如果资料被保存，触发监听，随后修改资料完善状态为已完成
                inst=kwargs['instance']

                all_save=UserProfile.objects.get(uid=inst.uid)

                if all_save is not None:#如果待完善的资料不为空，则随后写入数据（存在这条记录，只是没有完善）

                    key_value=False
                    for key in all_save.__dict__:
                        if all_save.__dict__[key] is None:#遍历对象元素，如果有一个为空则key_value=True
                            key_value=True

                        pass

                    if key_value==False:#key_value=False则写入数据

                        #以下是数据库没有的字段

                        #any(all_save.register_way)any(all_save.city) and and any(all_save.badge)and any(all_save.certificate)
                        #and any(all_save.mylession)and any(all_save.mystage) and any(all_save.myfavorite)

                        add_=UserTask(user=inst,startline=datetime.datetime.now(),deadline=None,status=1)
                        add_.save()
                        return add_.id#成功返回1


                    else:
                        return 0#失败返回0



                else:
                    return -1#其他返回负数
            else:
                return -2
        else:
             return -5

    except:
        return -3









def _need_create_plan(**kwargs):
    ret=0
    #如果正确产生UserTask，ret=UserTask实例的ID
    return ret
def _update_create_plan(**kwargs):
    ret=0
    #如果正确产生UserTask，ret=UserTask实例的ID
    return ret
def _need_finish_course(**kwargs):
    ret=0
    #如果正确产生UserTask，ret=UserTask实例的ID
    return ret
def _update_finish_course(**kwargs):
    ret=0
    #如果正确产生UserTask，ret=UserTask实例的ID
    return ret

from django.shortcuts import render_to_response
def Post_Save_Handle(**kwargs):
    if _create_class(**kwargs):
        return
    if _need_join_class(**kwargs):
        return render_to_response('',{})  #返回的页面?
    if _update_join_class(**kwargs):
        return render_to_response('',{})  #返回的页面?
    if _need_view_contract(**kwargs):
        return render_to_response('',{})  #返回的页面?
    if _update_view_contract(**kwargs):
        return
    if _need_full_profile(**kwargs):
        return
    if _update_full_profile(**kwargs):
        return
    if _need_create_plan(**kwargs):
        return
    if _update_create_plan(**kwargs):
        return
    if _need_finish_course(**kwargs):
        return
    if _update_finish_course(**kwargs):
        return


Signal.connect(post_save,Post_Save_Handle)
