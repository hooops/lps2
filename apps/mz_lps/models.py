# -*- coding: utf-8 -*-
from django.db import models
from django.conf import settings
from django.forms.forms import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError
from mz_course.models import Lesson, Course, CareerCourse

# Create your models here.

# 班级
class Class(models.Model):
    coding = models.CharField(u"班级编号", unique=True, max_length=30)
    date_publish = models.DateTimeField(u"创建日期", auto_now_add=True)
    date_open = models.DateTimeField(u"开课日期")
    student_limit = models.IntegerField(u"学生上限", default=25)
    current_student_count = models.IntegerField(u"当前报名数",default=0)
    is_active = models.BooleanField(u"有效性", default=True)
    status = models.SmallIntegerField(u"班级状态", default=1, choices=((1, u"进行中"),(2, u"已结束"),))
    qq = models.CharField(u"班级QQ群", max_length=13)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name=u"teacher", verbose_name=u"班级老师",null=True, blank=True)
    students = models.ManyToManyField(settings.AUTH_USER_MODEL, null=True, blank=True, related_name=u"students", verbose_name=u"班级学生", through=u"ClassStudents")
    career_course = models.ForeignKey(CareerCourse, verbose_name=u"职业课程")

    class Meta:
        verbose_name = u"班级"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return u"班级"

# 班级和学生产生的关联对象
class ClassStudents(models.Model):
    user               = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u"学生")
    student_class      = models.ForeignKey(Class, verbose_name=u"班级")
    study_point        = models.IntegerField("学生在该班级下的学力", default=0)
    is_view_contract   = models.BooleanField(u"是否查看协议", default=False) # add for lps2.0

    class Meta:
        verbose_name = u"班级学生"
        verbose_name_plural = verbose_name
        unique_together = (("user", "student_class"),)
        ordering = ['-study_point']

# 课程学分对象
class CourseScore(models.Model):
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, related_name=u"cs_user", verbose_name=u"用户")
    course           = models.ForeignKey(Course, verbose_name=u"课程")
    lesson_score     = models.IntegerField("随堂测验得分", null=True, blank=True, default=None)
    course_score     = models.IntegerField("课堂总测验得分", null=True, blank=True, default=None)
    project_score    = models.IntegerField("项目制作得分", null=True, blank=True, default=None)
    is_complete      = models.BooleanField("是否完成课程", default=False)
    complete_date    = models.DateTimeField("课程完成时的时间", null=True, blank=True, default=None)
    rebuild_count    = models.SmallIntegerField("第几次重修",default=0)
    date_publish     = models.DateTimeField("建立时间", auto_now_add=True)

    class Meta:
        verbose_name = u"课程学分"
        verbose_name_plural = verbose_name
        ordering = ['-rebuild_count']
    def __unicode__(self):
        return str(self.id)

# 学习计划
class Planning(models.Model):
    date_publish = models.DateTimeField("建立时间", auto_now_add=True)
    is_active = models.BooleanField("有效性", default=True)
    version = models.IntegerField("版本号", default=1)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name="用户")
    career_course = models.ForeignKey(CareerCourse,verbose_name="职业课程")

    class Meta:
        verbose_name = "学习计划"
        verbose_name_plural = verbose_name
        ordering = ['-version', '-id']
        unique_together = (("user", "career_course", "version"),)
    def __unicode__(self):
        return str(self.id)

# 学习计划项
class PlanningItem(models.Model):
    need_days = models.IntegerField("所需天数")
    course = models.ForeignKey(Course, verbose_name="课程")
    rebuild_count = models.SmallIntegerField("重修版本号", default=0)
    planning = models.ForeignKey(Planning, verbose_name="学习计划")

    class Meta:
        verbose_name = "学习计划项"
        verbose_name_plural = verbose_name
        ordering = ['id']
        unique_together = (("planning", "course", "rebuild_count"),)
    def __unicode__(self):
        return str(self.id)

# 计划暂停记录
class PlanningPause(models.Model):
    pause_date = models.DateTimeField("暂停时间")
    restore_date = models.DateTimeField("恢复时间", null=True, blank=True)
    reason = models.CharField("暂停原因", max_length=200)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="pp_teacher", verbose_name="老师")
    planning = models.ForeignKey(Planning, verbose_name="学习计划")

    class Meta:
        verbose_name = "计划暂停记录"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 考核
class Examine(models.Model):
    EXAMINE_TYPE = (
        (1,"课后作业"),
        (2,"试卷"),
        (3,"在线练习"),
        (4,"人工任务"),
        (5,"项目制作"),
    )
    RELATION_TYPE = {
        (1,"章节"),
        (2,"课程"),
        (3,"阶段"),
    }
    description = models.TextField("考核描述")
    examine_type = models.IntegerField("考核类别",choices=EXAMINE_TYPE)
    relation_type = models.IntegerField("关联类型", choices=RELATION_TYPE)
    relation_id = models.IntegerField("关联ID", blank=True, null=True)
    is_active = models.BooleanField("有效性",default=True)
    date_publish = models.DateTimeField("建立时间", auto_now_add=True)
    score = models.IntegerField("分值",blank=True, null=True)
    study_point = models.IntegerField("学力",blank=True, null=True)

    class Meta:
        verbose_name = "考核管理"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return str(self.id)

    def validate_unique(self, exclude=None):
        # these next 5 lines are directly from the Model.validate_unique source code
        unique_checks, date_checks = self._get_unique_checks(exclude=exclude)
        errors = self._perform_unique_checks(unique_checks)
        date_errors = self._perform_date_checks(date_checks)
        for k, v in date_errors.items():
            errors.setdefault(k, []).extend(v)

        # here I get a list of all pairs of parent_org, alias from the database (returned
        # as a list of tuples) & check for a match, in which case you add a non-field
        # error to the error list
        # 如果不是Mission（人工考核任务），则需要在添加和修改时检查'examine_type', 'relation_type', 'relation_id'的唯一性
        if type(self) is not Mission:
            pairs = Examine.objects.exclude(pk=self.pk).values_list('examine_type', 'relation_type', 'relation_id')
            if (self.examine_type, self.relation_type, self.relation_id) in pairs:
                    errors.setdefault(NON_FIELD_ERRORS, []).append('examine_type and relation_type and relation_id'
                                                                   ' must be unique')

        # finally you raise the ValidationError that includes all validation errors,
        # including your new unique constraint
        if errors:
            raise ValidationError(errors)

# 项目制作考核
class Project(Examine):

    class Meta:
        verbose_name = "项目制作考核"
        verbose_name_plural = verbose_name

    def __unicode__(self):
        return str(self.id)

# 课后作业
class Homework(Examine):

    class Meta:
        verbose_name = "课后作业"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return u"课后作业"

# 试卷
class Paper(Examine):

    class Meta:
        verbose_name = "试卷"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 试卷题目单选题，与试卷多对一的关系
class Quiz(models.Model):
    question = models.TextField("题目描述")
    item_list = models.TextField("题目选项")
    result = models.CharField("答案", max_length=1)
    index = models.IntegerField("试题顺序(从小到大)",default=999)
    paper = models.ForeignKey(Paper, verbose_name="试卷")

    class Meta:
        verbose_name = "试卷题目"
        verbose_name_plural = verbose_name
        ordering = ['index', 'id']
    def __unicode__(self):
        return self.question

# 在线代码练习
class CodeExercise(Examine):
    LANG_TYPE = {
        (1,"python"),
        (2,"php"),
        (3,"c"),
    }

    lang_type = models.IntegerField("语言类型",choices=LANG_TYPE)
    result = models.TextField("参考答案")

    class Meta:
        verbose_name = "代码练习"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return u"代码练习"

# 人工考核
class Mission(Examine):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL,verbose_name="老师")
    name = models.CharField("任务名称", max_length=30)

    class Meta:
        verbose_name = "人工考核"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 考核记录
class ExamineRecord(models.Model):
    is_active = models.BooleanField("有效性",default=True)
    score = models.IntegerField("获得分数",default=None,blank=True, null=True)
    study_point = models.IntegerField("获得学力",default=None,blank=True, null=True)
    date_publish = models.DateTimeField("建立时间", auto_now_add=True)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="er_student", verbose_name="学生")
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="er_teacher", verbose_name="评分老师", blank=True, null=True)
    rebuild_count = models.SmallIntegerField("第几次重修",default=0)
    examine = models.ForeignKey(Examine,verbose_name="对应考核")

    class Meta:
        verbose_name = "考核记录"
        verbose_name_plural = verbose_name
        unique_together = (("student", "examine", "rebuild_count"),)
    def __unicode__(self):
        return str(self.id)

# 项目制作考核记录
class ProjectRecord(ExamineRecord):
    project = models.ForeignKey(Project, verbose_name="对应项目制作考核")
    remark = models.TextField("项目考核评语",null=True,blank=True)
    upload_file = models.FileField("上传项目作品", upload_to="project/%Y/%m")

    class Meta:
        verbose_name = "考核记录_项目制作"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 课后作业记录
class HomeworkRecord(ExamineRecord):
    homework = models.ForeignKey(Homework, verbose_name="对应课后作业")
    upload_file = models.FileField("上传作品",upload_to="homework/%Y/%m")

    class Meta:
        verbose_name = "考核记录_课后作业"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 试卷记录
class PaperRecord(ExamineRecord):
    paper    = models.ForeignKey(Paper, verbose_name="对应试卷")
    accuracy = models.DecimalField("正确率", null=True, blank=True, default=None, max_digits=3, decimal_places=2)

    class Meta:
        verbose_name = "考核记录_试卷考核"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 做题记录
class QuizRecord(models.Model):
    quiz = models.ForeignKey(Quiz,verbose_name="对应试题")
    result = models.CharField("试题项结果",max_length=200)
    paper_record = models.ForeignKey(PaperRecord)

    class Meta:
        verbose_name = "考核记录_做题记录"
        verbose_name_plural = verbose_name
        unique_together = (("quiz", "paper_record"),)
    def __unicode__(self):
        return str(self.id)

# 在线练习结果
class CodeExerciseRecord(ExamineRecord):
    result = models.TextField("编码结果")
    code_exercise = models.ForeignKey(CodeExercise,verbose_name="对应代码练习")

    class Meta:
        verbose_name = "考核记录_代码练习"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return u"考核记录_代码练习"

class MissionRecord(ExamineRecord):
    mission = models.ForeignKey(Mission,verbose_name="对应人工考核")

    class Meta:
        verbose_name = "考核记录_人工考核"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)

# 直播室Model
class LiveRoom(models.Model):
    live_id = models.CharField(u"直播室ID", null=True, blank=True, max_length=15)
    live_code = models.CharField(u"课堂编号", null=True, blank=True, max_length=15)
    live_is_open = models.SmallIntegerField(u"是否开启直播", default=0, null=True, blank=True, choices=((0, u"未开启"),(1, u"开启"),))
    assistant_token = models.CharField(u"助教口令", null=True, blank=True, max_length=10)
    student_token = models.CharField(u"Web端学生口令", null=True, blank=True, max_length=10)
    teacher_token = models.CharField(u"老师口令", null=True, blank=True, max_length=10)
    student_client_token = models.CharField(u"学生客户端口令", null=True, blank=True, max_length=10)
    student_join_url = models.CharField(u"学生加入直播室地址", null=True, blank=True, max_length=100)
    teacher_join_url = models.CharField(u"老师加入直播室地址", null=True, blank=True, max_length=100)
    date_publish = models.DateTimeField(u"建立时间", auto_now_add=True)
    live_class = models.OneToOneField(Class, verbose_name=u"直播室关联班级", unique=True)

    class Meta:
        verbose_name = "直播室"
        verbose_name_plural = verbose_name
    def __unicode__(self):
        return str(self.id)
