# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from mz_course.models import Lesson, Course, CareerCourse, Stage
from mz_user.models import UserProfile
from mz_lps.models import Class
from mz_common.models import Org
from django.dispatch import Signal,receiver
from django.db.models.signals import post_save
import time

# Create your models here.

# 省份/城市
class ProvinceCity(models.Model):
    name =  models.CharField(u"名称", unique=True, max_length=30)
    index = models.IntegerField("顺序(从小到大)",default=999)
    class Meta:
        verbose_name = u"省份/城市"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

# 组织结构
class AcademicOrg(Org):
    province_city = models.ForeignKey(ProvinceCity, verbose_name=u"省份/城市")
    class Meta:
        verbose_name = u"组织机构"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

# 课程类型
class CourseType(models.Model):
    name = models.CharField(u"名称", unique=True, max_length=30)
    index = models.IntegerField("顺序(从小到大)",default=999)
    class Meta:
        verbose_name = u"课程类型"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

# 专业课程
class AcademicCourse(CareerCourse):
    owner= models.ManyToManyField(AcademicOrg, verbose_name=u"所属组织") #关联到第2级
    course_type = models.ForeignKey(CourseType, verbose_name=u"课程类型")
    class Meta:
        verbose_name = u"专业课程"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

# 专业阶段
class AcademicStage(Stage):
    class Meta:
        verbose_name = u"专业阶段"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

# 专业班级
class AcademicClass(Class):
    class Meta:
        verbose_name = u"专业班级"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.coding

# 高校通知
class Notification(models.Model):
    title =  models.CharField(u"标题",  max_length=300)
    url =  models.CharField(u"连接地址", max_length=300)
    index = models.IntegerField("顺序(从小到大)",default=999)
    owner = models.ForeignKey(AcademicOrg, verbose_name=u"高校") #关联到第1级
    class Meta:
        verbose_name = u"高校通知"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.title

# 高校学生身份验证记录
class AcademicUser(models.Model):
    user_no =  models.CharField(u"编号", null=True, blank=True, max_length=60)
    stu_name =  models.CharField(u"真实姓名", null=False, max_length=30)
    is_binded= models.BooleanField(u"是否绑定", default=False)
    binded_date= models.DateTimeField(u"绑定时间", null=True, blank=True)
    verify_code=models.CharField(u"验证码", null=True, blank=True, max_length=100)
    user= models.ForeignKey(UserProfile, verbose_name=u"关联账户", null=True, blank=True)
    academic_course= models.ForeignKey(AcademicCourse, null=True, blank=True, verbose_name=u"专业课程")
    owner_college= models.ForeignKey(AcademicOrg, related_name=u"owner_college", verbose_name=u"学院") #关联到第2级
    owner_university = models.ForeignKey(AcademicOrg, related_name=u"owner_university", verbose_name=u"大学")
    class Meta:
        verbose_name = u"高校学生身份验证记录"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.stu_name

ISOTIMEFORMAT='%Y-%m-%d'

def Post_Save_Handle(**kwargs):
    obj=kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']

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

Signal.connect(post_save,Post_Save_Handle)