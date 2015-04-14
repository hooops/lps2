# -*- coding: utf-8 -*-

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from datetime import datetime
from django.core.mail import send_mail
from mz_course.models import CareerCourse,Course,Lesson,Stage
from uuidfield import UUIDField

class CountryDict(models.Model):

    """
    国家字典
    """

    name        = models.CharField(max_length=50, verbose_name=u"国家")
    index       = models.IntegerField("国家顺序(从小到大)",default=999)

    class Meta:
        verbose_name        = u"国家字典"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

class ProvinceDict(models.Model):

    """
    省份字典
    """

    name        = models.CharField(max_length=50, verbose_name=u"省份")
    index       = models.IntegerField("省份顺序(从小到大)",default=999)
    country     = models.ForeignKey(CountryDict, verbose_name=u"国家")

    class Meta:
        verbose_name        = u"省份字典"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return self.name

class CityDict(models.Model):

    """
    城市字典
    """

    name        = models.CharField(max_length=50, verbose_name=u"城市")
    index       = models.IntegerField("城市顺序(从小到大)",default=999)
    province    = models.ForeignKey(ProvinceDict, verbose_name=u"省份")

    class Meta:
        verbose_name        = u"城市字典"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return self.name

class BadgeDict(models.Model):

    """
    徽章字典
    """

    name            = models.CharField(max_length=50, verbose_name=u"徽章名称")
    badge_type      = models.SmallIntegerField(choices=((0, u"VIP徽章"),(1, u"职业课程徽章"),), verbose_name=u"徽章类型")
    badge_url       = models.ImageField(upload_to='badge/%Y/%m', max_length=200, null=True, blank=True, verbose_name=u"徽章路径")
    career_course   = models.OneToOneField(CareerCourse, null=True, blank=True, verbose_name=u"职业课程")

    class Meta:
        verbose_name        = u"徽章字典"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

class Certificate(models.Model):

    """
    证书
    """

    name            = models.CharField(max_length=50, verbose_name=u"证书名称")
    image_url       = models.ImageField(upload_to='certificate/%Y/%m', max_length=200, null=True, blank=True, verbose_name=u"证书地址")
    career_course   = models.OneToOneField(CareerCourse, verbose_name=u"职业课程")

    class Meta:
        verbose_name        = u"证书字典"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name

class RegisterWay(models.Model):

    '''
    注册途径
    '''

    name            = models.CharField(max_length=30, verbose_name=u"途径名称")

    class Meta:
        verbose_name        = u"注册途径"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return self.name


class UserProfileManager(BaseUserManager):

    def _create_user(self, username, email, password,
                     is_staff, is_superuser, **extra_fields):
        """
        根据用户名和密码创建一个用户
        """
        now = datetime.now()
        if not email:
            raise ValueError(u'Email必须填写')
        user = self.model(username=username,email=email,
                          is_staff=is_staff, is_active=True,
                          is_superuser=is_superuser, last_login=now,
                          date_joined=now, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        return self._create_user(email, email, password, False, False,
                                 **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email, email, password, True, True,
                                 **extra_fields)

class UserProfile(AbstractBaseUser,PermissionsMixin):

    """
    继承AbstractUser，扩展用户信息
    """
    uuid                    = UUIDField(auto=True)
    username                = models.CharField("用户名", max_length=30, unique=True)
    first_name              = models.CharField("名字", max_length=30, blank=True)
    last_name               = models.CharField("姓氏", max_length=30, blank=True)
    email                   = models.EmailField("邮件地址", unique=True, null=True, blank=True)
    is_staff                = models.BooleanField("职员状态", default=False, help_text="是否能够登录管理后台")
    is_active               = models.BooleanField("是否激活", default=True, help_text="用户是否被激活，未激活则不能使用")
    date_joined             = models.DateTimeField("创建日期", default=datetime.now())
    nick_name               = models.CharField(max_length=50, verbose_name=u"昵称", unique=True, null=True, blank=True)
    avatar_url              = models.ImageField(upload_to="avatar/%Y/%m", default="avatar/default_big.png", max_length=200, blank=True, null=True, verbose_name=u"头像220x220")
    avatar_middle_thumbnall = models.ImageField(upload_to="avatar/%Y/%m", default="avatar/default_middle.png", max_length=200, blank=True, null=True, verbose_name=u"头像104x104")
    avatar_small_thumbnall  = models.ImageField(upload_to="avatar/%Y/%m", default="avatar/default_small.png", max_length=200, blank=True, null=True, verbose_name=u"头像70x70")
    qq                      = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"QQ号码")
    mobile                  = models.CharField(max_length=11, blank=True, null=True, unique=True, verbose_name=u"手机号码")
    valid_email             = models.SmallIntegerField(default=0, choices=((0, u"否"),(1, u"是"),), verbose_name=u"是否验证邮箱")
    valid_mobile            = models.SmallIntegerField(default=0, choices=((0, u"否"),(1, u"是"),), verbose_name=u"是否验证手机")
    company_name            = models.CharField(max_length=150, blank=True, null=True, verbose_name=u"公司名")
    position                = models.CharField(max_length=150, blank=True, null=True, verbose_name=u"职位名")
    description             = models.TextField(blank=True, null=True, verbose_name=u"个人介绍")
    uid                     = models.IntegerField(blank=True, null=True, unique=True, verbose_name=u"对应ucenter用户ID")
    register_way            = models.ForeignKey(RegisterWay, null=True, blank=True, verbose_name=u"注册途径")
    city                    = models.ForeignKey(CityDict, null=True, blank=True, verbose_name=u"城市")
    index                   = models.IntegerField("排列顺序(从小到大)",default=999)
    badge                   = models.ManyToManyField(BadgeDict, null=True, blank=True, verbose_name=u"徽章")
    certificate             = models.ManyToManyField(Certificate, null=True, blank=True, verbose_name=u"证书")
    mylesson                = models.ManyToManyField(Lesson, null=True, blank=True, verbose_name=u"我的学习章节", through=u"UserLearningLesson")
    mystage                 = models.ManyToManyField(Stage, null=True, blank=True, verbose_name=u"我的解锁阶段", through=u"UserUnlockStage")
    myfavorite              = models.ManyToManyField(Course, null=True, blank=True, verbose_name=u"我的收藏", through=u"MyFavorite")
    token                   = models.CharField(max_length=100, blank=True, null=True, verbose_name=u"设备Token")

    objects = UserProfileManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name        = u"用户"
        verbose_name_plural = verbose_name

    def get_full_name(self):
        """
        Returns the first_name plus the last_name, with a space in between.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        "Returns the short name for the user."
        return self.first_name

    def email_user(self, subject, message, from_email=None, **kwargs):
        """
        Sends an email to this User.
        """
        send_mail(subject, message, from_email, [self.email], **kwargs)

    # 是否是老师
    def is_teacher(self):
        if self.groups.filter(name="老师").count() > 0 :
            return True
        return False

    # 是否是学生
    def is_student(self):
        if self.groups.filter(name="学生").count() > 0 :
            return True
        return False

    # 是否是高校老师
    def is_academic_teacher(self):
        if self.is_teacher() and self.academicuser_set.all().count() > 0:
            return True
        return False

    # 是否是高校学生
    def is_academic_student(self):
        if self.is_student() and self.academicuser_set.all().count() > 0:
            return True
        return False

    # 验证学生是否是企业直通班的学生
    def is_unlockstage(self):
        if self.userunlockstage_set.all().count() > 0:
            return True
        return False

class MyCourse(models.Model):
    user             = models.ForeignKey(UserProfile, related_name=u"mc_user", verbose_name=u"用户")
    course           = models.CharField(max_length=10, verbose_name=u"课程ID")
    course_type      = models.SmallIntegerField(choices=((1, u"课程"),(2, u"职业课程"),), verbose_name=u"课程类型")
    index            = models.IntegerField(default=999, verbose_name=u"课程显示顺序(从小到大)")
    date_add         = models.DateTimeField(auto_now_add=True, verbose_name=u"添加时间")

    class Meta:
        verbose_name = u"我的课程"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)


class MyFavorite(models.Model):
    user             = models.ForeignKey(UserProfile, related_name=u"mf_user", verbose_name=u"用户")
    course           = models.ForeignKey(Course, verbose_name=u"课程")
    date_favorite    = models.DateTimeField(auto_now_add=True, verbose_name=u"收藏时间")

    class Meta:
        verbose_name = u"我的收藏"
        verbose_name_plural = verbose_name
        unique_together = (("user", "course"),)
    def __unicode__(self):
        return str(self.id)

# 用户学习章节记录(我的章节)
class UserLearningLesson(models.Model):
    date_learning = models.DateTimeField("最近学习时间", auto_now=True)
    is_complete = models.BooleanField("是否完成观看",default=False)
    lesson = models.ForeignKey(Lesson, verbose_name="章节")
    user = models.ForeignKey(UserProfile, verbose_name="用户")

    class Meta:
        verbose_name="我的章节"
        verbose_name_plural = verbose_name
        unique_together = (("user", "lesson"),)
    def __unicode__(self):
        return str(self.id)

# 用户解锁的具体阶段
class UserUnlockStage(models.Model):
    user                    = models.ForeignKey(UserProfile, verbose_name=u"用户")
    stage                   = models.ForeignKey(Stage, null=True, blank=True, verbose_name=u"解锁的阶段")
    date_unlock             = models.DateTimeField(default=datetime.now(), auto_now_add=True, verbose_name=u"解锁时间")

    class Meta:
        verbose_name="我的解锁阶段"
        verbose_name_plural = verbose_name
        unique_together = (("user", "stage"),)
    def __unicode__(self):
        return str(self.id)
