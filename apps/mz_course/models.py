# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.dispatch import Signal,receiver
from django.db.models.signals import post_save
from mz_common.models import *

# Create your models here.

# 职业课程 models
class CareerCourse(models.Model):
    name = models.CharField("职业课程名称", max_length=50)
    short_name = models.CharField("职业课程英文名称简写", max_length=10)
    image = models.ImageField("课程小图标", upload_to="course/%Y/%m")
    app_image = models.ImageField("app端课程小图标", upload_to="course/%Y/%m", null=True, blank=True)
    description = models.TextField("文字介绍")
    student_count = models.IntegerField("学习人数", default=0)
    market_page_url = models.URLField("营销页面地址", blank=True, null=True)
    course_color = models.CharField("课程配色", max_length=50)
    discount = models.DecimalField("折扣", default=1, max_digits=3, decimal_places=2)
    click_count = models.IntegerField("点击次数",default=0)
    index = models.IntegerField("职业课程顺序(从小到大)",default=999)
    search_keywords = models.ManyToManyField(Keywords, null=True, blank=True, verbose_name="搜索关键词")
    seo_title = models.CharField("SEO标题", max_length=200, null=True, blank=True)
    seo_keyword = models.CharField("SEO关键词", max_length=200, null=True, blank=True)
    seo_description = models.TextField("SEO描述", null=True, blank=True)
    #add by Steven YU
    course_scope = models.SmallIntegerField("课程类型",null=True, blank=True, choices=((0,"高校专区"),(1,"企业专区"),))

    class Meta:
        verbose_name = "职业课程"
        verbose_name_plural = verbose_name
        ordering = ['-id']
    def __unicode__(self):
        return self.name

# 阶段 models
class Stage(models.Model):
    name = models.CharField("阶段名称", max_length=50)
    description = models.TextField("阶段描述")
    price = models.IntegerField("阶段价格")
    index = models.IntegerField("阶段顺序(从小到大)",default=999)
    is_try = models.BooleanField(default=False, verbose_name=u"是否是试学阶段")
    career_course = models.ForeignKey(CareerCourse, verbose_name="职业课程")

    class Meta:
        verbose_name = "课程阶段"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

    def getCourseSet(self):
        if self.course_set.count():
            return self.course_set.all()
        else:
            return Course.objects.filter(stages_m = self)

# 课程 models
class Course(models.Model):
    name = models.CharField("课程名称",max_length=50)
    image = models.ImageField("课程封面", upload_to="course/%Y/%m")
    description = models.TextField("课程描述")
    is_active = models.BooleanField("有效性", default=True)
    date_publish = models.DateTimeField("发布时间", auto_now_add=True)
    need_days = models.IntegerField("无基础学生完成天数", default=7)
    need_days_base = models.IntegerField("有基础学生完成天数", default=5)
    student_count = models.IntegerField("学习人数", default=0)
    favorite_count = models.IntegerField("收藏次数", default=0)
    click_count = models.IntegerField("点击次数",default=0)
    has_project = models.BooleanField("是否有项目考核", default=False)
    has_examine = models.BooleanField("是否有课程总测验", default=True)
    is_novice = models.BooleanField("是否是新手课程", default=False)
    is_click = models.BooleanField("是否点击能进入课程", default=False)
    index = models.IntegerField("课程顺序(从小到大)",default=999)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="老师")
    stages_m = models.ManyToManyField(Stage, related_name="stages_m", blank=True, null=True, verbose_name="多阶段")

    stages = models.ForeignKey(Stage, blank=True, null=True, verbose_name="阶段")

    search_keywords = models.ManyToManyField(Keywords, null=True, blank=True, verbose_name="小课程搜索关键词")
    #Add by Steven YU
    is_homeshow = models.BooleanField(u"是否在首页显示", default=False)
    is_required = models.BooleanField(u"是否必修", default=True) # add for lps2.0

    class Meta:
        verbose_name = "课程"
        verbose_name_plural = verbose_name

    def getStages(self, stage_id = -1):
        stage=self.stages
        if stage_id>0:
            stage=Stage.objects.get(pk=stage_id)
        return stage

    def __unicode__(self):
        return self.name

# 章节 models
class Lesson(models.Model):
    name = models.CharField("章节名称",max_length=50)
    video_url = models.CharField("视频资源URL", max_length=200)
    video_length = models.IntegerField("视频长度（秒）")
    play_count = models.IntegerField("播放次数",default=0)
    share_count = models.IntegerField("分享次数",default=0)
    index = models.IntegerField("章节顺序(从小到大)",default=999)
    is_popup = models.BooleanField("是否弹出提示框（支付、登录）", default=False)
    course = models.ForeignKey(Course, verbose_name="课程")
    seo_title = models.CharField("SEO标题", max_length=200, null=True, blank=True)
    seo_keyword = models.CharField("SEO关键词", max_length=200, null=True, blank=True)
    seo_description = models.TextField("SEO描述", null=True, blank=True)

    class Meta:
        verbose_name = "章节"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

# 章节资源 models
class LessonResource(models.Model):
    name = models.CharField("章节资源名称", max_length=50)
    download_url = models.FileField("下载地址", upload_to="lesson/%Y/%m")
    download_count = models.IntegerField("下载次数", default=0)
    lesson = models.ForeignKey(Lesson,verbose_name="章节")

    class Meta:
        verbose_name = "章节资源"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name


# 章节讨论 models
class Discuss(models.Model):
    content = models.TextField("讨论内容")
    parent_id = models.IntegerField("父讨论ID", blank=True, null=True)
    date_publish = models.DateTimeField("发布时间",auto_now_add = True)

    lesson = models.ForeignKey(Lesson, verbose_name="章节")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户")

    class Meta:
        verbose_name = "课程讨论"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

def Post_Save_Handle(**kwargs):
    obj=kwargs['sender']
    created = False
    if kwargs.has_key('created'):
        created = kwargs['created']

    # 如果是添加新的课程章节，更新章节对应课程Course对象的最新发布时间
    if created and (obj is Lesson):
        inst=kwargs['instance']
        inst.course.date_publish = datetime.now()
        inst.course.save()

Signal.connect(post_save, Post_Save_Handle)

