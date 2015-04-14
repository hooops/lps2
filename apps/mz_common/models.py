#!/usr/bin/python
#-*- coding:utf-8 -*-
from django.db import models
from datetime import datetime
from django.conf import settings
from datetime import datetime,timedelta


# Create your models here.
class MyMessage(models.Model):
    action_types = (
        ('1','系统消息'),
        ('2','课程讨论回复'),
        ('3','论坛讨论回复'),
    )
    class Meta:
        verbose_name = u'我的消息'
        verbose_name_plural = verbose_name
    userA = models.IntegerField(u"用户A")  #发送方，为0表示系统用户
    userB = models.IntegerField(u"用户B")   #接收方，为0就给所有用户发送消息
    action_type = models.CharField(u'类型',choices = action_types,max_length = 1)
    action_id = models.IntegerField(u'动作id',blank = True,null = True)
    action_content = models.TextField(u'消息内容',blank = True,null = True)
    date_action = models.DateTimeField(u"添加日期",auto_now_add = True)
    is_new = models.BooleanField(u'是否为最新',default=True)
    def __unicode__(self):
        return str(self.id)

class Log(models.Model):
    log_types = (
        ('1','班级管理'),
    )
    class Meta:
        verbose_name = u'日志'
        verbose_name_plural = verbose_name
    userA = models.IntegerField(u"用户A")
    userB = models.IntegerField(u"用户B",blank = True,null = True)
    log_type = models.CharField(u'类型',choices = log_types,max_length = 1)
    log_id = models.IntegerField(u'动作id',blank = True,null = True)
    log_content = models.TextField(u'消息内容',blank = True,null = True)
    date_action = models.DateTimeField(u'添加日期', auto_now_add = True)
    def __unicode__(self):
        return str(self.id)

class Ad(models.Model):
    class Meta:
        verbose_name = u'网站广告'
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    title = models.CharField(u'广告标题',max_length = 50)
    description = models.CharField(u'广告描述',max_length = 200)
    image_url = models.ImageField(u'图片路径',upload_to='ad/%Y/%m')
    callback_url = models.URLField(u'回调url', null=True, blank=True)
    index = models.IntegerField("排列顺序(从小到大)",default=999)
    def __unicode__(self):
        return self.title

class AppAd(models.Model):
    ad_types = (
        ('0','课程'),
        ('1','职业课程'),
    )
    class Meta:
        verbose_name = u'App广告'
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    title = models.CharField(u'广告标题',max_length = 50)
    description = models.CharField(u'广告描述',max_length = 200,blank = True,null = True)
    image_url = models.ImageField(u'图片路径',upload_to='ad/%Y/%m')
    ad_type = models.CharField(u'广告类型',choices = ad_types,max_length = 1)
    target_id = models.IntegerField(u'跳转目标ID')
    index = models.IntegerField("排列顺序(从小到大)",default=999)
    def __unicode__(self):
        return self.title

class Links(models.Model):
    title =  models.CharField(u'标题',max_length = 50)
    description = models.CharField(u'友情链接描述',max_length = 200)
    image_url = models.ImageField(u'图片路径',upload_to='links/%Y/%m',null=True,blank=True)
    callback_url = models.URLField(u'回调url')
    is_pic = models.BooleanField(u'是否为图片',default=False)
    class Meta:
        verbose_name = u'友情链接'
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.title

class Keywords(models.Model):
    name = models.CharField(u'关键词',max_length = 50)
    class Meta:
        verbose_name = u'关键词'
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

class RecommendKeywords(models.Model):
    name = models.CharField(u'推荐搜索关键词',max_length = 50)
    class Meta:
        verbose_name = u'推荐搜索关键词'
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

class PageSeoSet(models.Model):
    page_name_types = (
        ('1','首页'),
        ('2','移动app'),
        ('3','职业课程'),
    )
    page_name = models.CharField("单页名称", choices = page_name_types, max_length=3, null=True, blank=True)
    seo_title = models.CharField("SEO标题", max_length=200, null=True, blank=True)
    seo_keyword = models.CharField("SEO关键词", max_length=200, null=True, blank=True)
    seo_description = models.TextField("SEO描述", null=True, blank=True)
    class Meta:
        verbose_name = u'单页SEO设置'
        verbose_name_plural = verbose_name
        unique_together = (("page_name",),)
    def __unicode__(self):
        return self.page_name

class MobileVerifyRecord(models.Model):

    '''
    手机验证码记录表
    '''

    code            = models.CharField(max_length=6, verbose_name="验证码")
    mobile          = models.CharField(max_length=11, verbose_name="手机号码")
    type            = models.SmallIntegerField(default=0, choices=((0, "注册"),(1, "忘记密码"),), verbose_name="验证码类型")
    ip              = models.CharField(max_length=20, verbose_name="请求来源IP")
    created         = models.DateTimeField(auto_now_add = True, default=datetime.now(), verbose_name="创建时间")

    class Meta:
        verbose_name = "手机验证记录"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.code

class EmailVerifyRecord(models.Model):

    '''
    邮箱验证记录表（包括注册和忘记密码使用到的验证链接）
    '''

    code            = models.CharField(max_length=10, verbose_name="验证码")
    email           = models.CharField(max_length=50, verbose_name="邮箱")
    type            = models.SmallIntegerField(default=0, choices=((0, "注册"),(1, "忘记密码"),), verbose_name="验证码类型")
    ip              = models.CharField(max_length=20, verbose_name="请求来源IP")
    created         = models.DateTimeField(auto_now_add = True, default=datetime.now(), verbose_name="创建时间")

    class Meta:
        verbose_name = "邮箱验证记录"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.code


class Coupon(models.Model):
    endtime = datetime.now() + timedelta(days =90)
    surplus = models.IntegerField(verbose_name=u"剩余张数")
    coupon_price  = models.CharField(max_length=20,verbose_name=u"优惠金额")
    createtime = models.DateTimeField(default=datetime.now(), auto_now_add=True, verbose_name=u"创建时间")
    endtime = models.DateTimeField(default=endtime,verbose_name=u"结束时间")
    
    class Meta:
        verbose_name        = u"优惠码"
        verbose_name_plural = verbose_name

class Coupon_Details(models.Model):
    code_sno = models.CharField(max_length=20, unique=True, verbose_name=u"优惠码") 
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, verbose_name=u"用户")
    use_time = models.CharField(max_length=50,default=None,verbose_name=u"使用时间")
    is_use = models.BooleanField(default=False, verbose_name=u"是否使用")
    is_lock = models.BooleanField(default=False, verbose_name=u"是否锁定")
    coupon = models.ForeignKey(Coupon, verbose_name="id")
    careercourse_id = models.CharField(max_length=20,null=True,blank=True,verbose_name=u"职业课程id")
    
    class Meta:
        verbose_name        = u"优惠码详情"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.code_sno


class RecommendedReading(models.Model):
    ACTIVITY = 'AV'
    NEWS = 'NW'
    DISCUSS = 'DC'

    READING_TYPES = (
        (ACTIVITY, '官方活动'),
        (NEWS, '开发者资讯'),
        (DISCUSS, '技术交流'),
    )

    reading_type = models.CharField(max_length=2,
    choices=READING_TYPES,
    default=ACTIVITY
    )

    title = models.CharField(max_length=200)
    url = models.URLField(max_length=200)

    class Meta:
        verbose_name = "首页推荐文章"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.title

# 消息推送Model
class MsgBox(models.Model):
    sendtarget=models.SmallIntegerField(u"发送对象",default="-1", null=True, blank=True, choices=((-1,u"全部"),(0, u"学生"), (1,u"老师"),))
    content=models.TextField(u'消息内容')
    date_send = models.DateTimeField(u"发送时间", auto_now_add=True)
    is_sendmsg=models.BooleanField(u"是否发送站内信",default=False)
    is_sendemail=models.BooleanField(u"是否发送邮件",default=False)
    is_sendappmsg=models.BooleanField(u"是否推送App消息",default=False)

    class Meta:
        verbose_name = "消息推送记录"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# （app）留言反馈model
class Feedback(models.Model):
    content = models.TextField(u'反馈内容')
    date_publish = models.DateTimeField(u"发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "留言反馈"
        verbose_name_plural = verbose_name
        ordering = ['-date_publish']
    def __unicode__(self):
        return str(self.id)

# （app）版本管理
class AndroidVersion(models.Model):
    vno = models.CharField(max_length=10, verbose_name="版本号")
    size = models.CharField(max_length=10, verbose_name="文件大小", null=True, blank=True)
    desc = models.TextField(null=True, blank=True, verbose_name="功能简介")
    is_force = models.BooleanField(default=False, verbose_name="是否强制更新")
    down_url = models.CharField(max_length=100, verbose_name="下载地址")

    class Meta:
        verbose_name = "版本管理"
        verbose_name_plural = verbose_name
        ordering = ['-id']
    def __unicode__(self):
        return str(self.id)

# Add by Steven YU
# 组织结构基类
class Org(models.Model):
    name =  models.CharField("名称", unique=True, max_length=30)
    index = models.IntegerField("顺序(从小到大)",default=999)
    image = models.ImageField("小图标", upload_to="org/%Y/%m", null=True, blank=True)
    big_image = models.ImageField("大图标", upload_to="org/%Y/%m", null=True, blank=True)
    app_image = models.ImageField("app端小图标", upload_to="org/%Y/%m", null=True, blank=True)
    description = models.TextField("介绍", null=True, blank=True)
    parent=models.ForeignKey('self', null=True, blank=True, verbose_name="父级机构")
    level=models.IntegerField("级别", default=1)
    class Meta:
        verbose_name = "组织机构"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.name

# 手机活动页面咨询统计信息
class AppConsultInfo(models.Model):
    name = models.CharField("姓名", max_length=30, null=True, blank=True)
    phone = models.CharField("电话", max_length=30, null=True, blank=True)
    qq = models.CharField("QQ", max_length=30, null=True, blank=True)
    interest = models.CharField("兴趣方向", max_length=50, null=True, blank=True)
    date_publish = models.DateTimeField("发布时间", auto_now_add=True)

    class Meta:
        verbose_name = "手机活动页咨询统计"
        verbose_name_plural = verbose_name
        ordering = ['-id']

    def __unicode__(self):
        return self.name