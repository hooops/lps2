#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django import forms
from django.core import validators

from mz_course.models import CareerCourse, Lesson, LessonResource, Stage
from mz_user.models import UserProfile
from mz_lps.models import Quiz, Project, Examine


# bootstrap input 的默认样式
bs_input_class = {"class": "form-control"}


class StaticInfoWidget(forms.Widget):
    """ bs form 中的静态信息 """

    def __init__(self, attrs={}):
        super(forms.Widget, self).__init__()
        self.attrs = attrs

    # XXX 怎样可以不 escape
    def render(self, name, value, attrs={}):
        return u'<p class="form-control-static">%s</p>' % (value or "")


class LoginForm(forms.Form):
    """ 登录 """

    username = forms.CharField(label=u"用户名",
                               widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(label=u"密码",
                               widget=forms.TextInput(attrs={"class": "form-control", "type": "password"}))


class CareerCourseForm(forms.ModelForm):

    class Meta:
        model = CareerCourse
        fields = ["name", "short_name", "description", "market_page_url"]
        labels = {"short_name": u"英文缩写"}
        widgets = {"name": forms.TextInput(attrs=bs_input_class),
                   "short_name": forms.TextInput(attrs=bs_input_class),
                   "description": forms.Textarea(attrs={"class": "form-control autogrow", "rows": 3}),
                   "market_page_url": forms.TextInput(attrs=bs_input_class)}

    search_keywords = forms.CharField(label=u"关键词",
                                      widget=forms.TextInput(attrs=bs_input_class))


class StageEditForm(forms.ModelForm):

    class Meta:
        model = Stage
        fields = ["name", "price", "description"]
        #labels = {}
        widgets = {"name": forms.TextInput(attrs=bs_input_class),
                   "price": forms.TextInput(attrs=bs_input_class)}

    name = forms.CharField(label=u"阶段名称",
                           widget=forms.TextInput(attrs={"class": "form-control"}))
    description = forms.CharField(label=u"阶段介绍",
                                  widget=forms.Textarea(attrs={"class": "form-control autogrow", "rows": 3}))


class CourseForm(forms.Form):

    name = forms.CharField(label=u"课程标题",
                           widget=forms.TextInput(attrs=bs_input_class))
    search_keywords = forms.CharField(label=u"关键词",
                                      widget=forms.TextInput(attrs=bs_input_class))
    description = forms.CharField(label=u"课程描述",
                                  widget=forms.Textarea(attrs=bs_input_class))
    teacher = forms.CharField(label=u"选择讲师",
                              widget=forms.TextInput(attrs=bs_input_class))


class StudentForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ["username", "mobile", "nick_name", "city", "qq", "email"]
        labels = {"date_joined": u"注册时间"}
        widgets = {"email": forms.TextInput(attrs=bs_input_class),
                   "username": forms.TextInput(attrs=bs_input_class),
                   "mobile": forms.TextInput(attrs=bs_input_class),
                   "date_joined": StaticInfoWidget(),
                   "nick_name": forms.TextInput(attrs=bs_input_class),
                   "city": forms.TextInput(attrs=bs_input_class),
                   "qq": forms.TextInput(attrs=bs_input_class)}


class QuizForm(forms.ModelForm):

    class Meta:
        model = Quiz
        fields = ["index", "question", "result"]
        labels = {"index": u"题目序号",
                  "question": u"测试题目",
                  "result": u"正确答案"}
        widgets = {"index": forms.TextInput(attrs=bs_input_class),
                   "question": forms.Textarea(attrs=bs_input_class),
                   "result": forms.Select(attrs=bs_input_class,
                                          choices= (("a", "a"),
                                                    ("b", "b"),
                                                    ("c", "c"),
                                                    ("d", "d"),))}

    item_1 = forms.CharField(label=u"答案 a",
                             widget=forms.TextInput(attrs=bs_input_class))
    item_2 = forms.CharField(label=u"答案 b",
                              widget=forms.TextInput(attrs=bs_input_class))
    item_3 = forms.CharField(label=u"答案 c",
                              widget=forms.TextInput(attrs=bs_input_class))
    item_4 = forms.CharField(label=u"答案 d",
                              widget=forms.TextInput(attrs=bs_input_class))


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        fields = ["description", "is_active"]
        labels = {"description": u"任务描述"}
        widgets = {"description": forms.Textarea(attrs={"class": "form-control autogrow", "rows": 3}),
                   "is_active": forms.CheckboxInput(attrs={"data-toggle": "checkbox"})}


class LessonForm(forms.ModelForm):

    class Meta:
        model = Lesson
        fields = ["name", "video_url", "video_length", "index"]
        labels = {"name": u"章节标题",
                  "video_url": u"视频资源",
                  "video_length": u"视频时长",
                  "index": u"章节顺序"}

        widgets = {"name": forms.TextInput(attrs=bs_input_class),
                   "video_url": forms.TextInput(attrs=bs_input_class),
                   "video_length": forms.TextInput(attrs=bs_input_class),
                   "index": forms.TextInput(attrs=bs_input_class)}


class ExamineForm(forms.ModelForm):

    class Meta:
        model = Examine
        fields = ["description", "is_active"]
        labels = {"description": u"任务描述"}
        widgets = {"description": forms.Textarea(attrs={"class": "form-control autogrow", "rows": 3}),
                   "is_active": forms.CheckboxInput(attrs={"data-toggle": "checkbox"})}


class LessonResourceForm(forms.ModelForm):

    class Meta:
        model = LessonResource
        fields = ["name"]
        labels = {"name": u"资源名称"}
        widgets = {"name": forms.TextInput(attrs=bs_input_class)}

    download_url = forms.FileField(label=u"上传文件",
                                   required=False,
                                   widget=forms.FileInput(attrs=bs_input_class))


class TeacherForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ["email", "username", "mobile", "nick_name", "city", "qq"]
        labels = {}
        widgets = {"email": forms.TextInput(attrs=bs_input_class),
                   "username": forms.TextInput(attrs=bs_input_class),
                   "mobile": forms.TextInput(attrs=bs_input_class),
                   "nick_name": forms.TextInput(attrs=bs_input_class),
                   "city": forms.TextInput(attrs=bs_input_class),
                   "qq": forms.TextInput(attrs=bs_input_class)}


