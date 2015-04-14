# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.db.models import Q
from django.conf import settings
from captcha.fields import CaptchaField, CaptchaTextInput
from datetime import datetime, timedelta
from models import UserProfile
from mz_common.models import MobileVerifyRecord
import re
from mz_user.models import *
class UserCreationForm(forms.ModelForm):
    """
    管理后台添加用户的Form
    """
    error_messages = {
        'duplicate_email': "Email已经存在.",
        'password_mismatch': "两次输入的密码不匹配.",
        }
    email = forms.EmailField(label="邮件地址", max_length=30,
                                error_messages={
                                    'invalid': "请输入正确的Email格式"})
    password1 = forms.CharField(label="密码", min_length=6, max_length=16,
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label="确认密码",
                                widget=forms.PasswordInput,
                                help_text="请输入和上面一致的密码以确认输入无误.")

    class Meta:
        model = UserProfile
        fields = ("email",)

    def clean_email(self):
        # Since User.username is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        email = self.cleaned_data["email"]
        try:
            UserProfile._default_manager.get(email=email)
        except UserProfile.DoesNotExist:
            return email
        raise forms.ValidationError(
            self.error_messages['duplicate_email'],
            code='duplicate_email',
            )

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
                )
        return password2

    def save(self, commit=True):
        user = super(UserCreationForm, self).save(commit=False)
        user.username = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    '''
    管理后台修改用户的Form
    '''
    error_messages = {"invaild": "手机号格式不正确",}
    email = forms.EmailField(label="邮件地址", max_length=30,required=False,
                             error_messages={
                                 'invalid': "请输入正确的Email格式"})
    password = ReadOnlyPasswordHashField(label="密码",
                                         help_text="原密码已加密处理，所以没有办法看到该用户的密码，但您可以更改密码，使用"
                                                     "<a href=\"password/\">这个链接</a>可以修改密码.")

    class Meta:
        model = UserProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UserChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')
        #email\mobile\username只能由前台修改
        self.fields.get("email").widget=forms.TextInput(attrs={"readonly": "true"})
        self.fields.get("mobile").widget=forms.TextInput(attrs={"readonly": "true"})
        self.fields.get("username").widget=forms.TextInput(attrs={"readonly": "true"})

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]

    def clean_mobile(self):
        '''
        验证Mobile格式是否正确
        :return:
        '''
        mobile = self.cleaned_data["mobile"]
        if mobile == "":
            mobile = None
        else:
            p=re.compile(settings.REGEX_MOBILE)
            if not p.match(mobile):
                raise forms.ValidationError(
                    self.error_messages['invaild'],
                    code='invaild',
                    )

        return mobile

class LoginForm(forms.Form):
    '''
    登录Form
    '''
    error_messages = {"invaild": "该账号格式不正确", "forbidden": "该账号已被禁用"}
    account_l = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入邮箱账号/手机号"}),
                              max_length=50,error_messages = {"required":"账号不能为空",})
    password_l = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入密码"}),
                                 error_messages = {"required":"密码不能为空",})

    def clean_account_l(self):
        '''
        验证账号输入格式是否为邮箱或手机
        :return:
        '''
        account_l = self.cleaned_data["account_l"]
        #邮箱或常用号码段的手机号格式
        p=re.compile(settings.REGEX_EMAIL+"|"+settings.REGEX_MOBILE)
        if not p.match(account_l):
            raise forms.ValidationError(
                self.error_messages['invaild'],
                code='invaild',
                )
        try:
            user = UserProfile.objects.get(Q(email=account_l)|Q(mobile=account_l))
            if user.is_active == 0:
                raise forms.ValidationError(
                    self.error_messages['forbidden'],
                    code='forbidden',
                    )
        except UserProfile.DoesNotExist:
            pass

        return account_l

class EmailRegisterForm(forms.Form):
    '''
    邮箱账号注册的Form
    '''
    error_messages = {"duplicate_email": "该账号已被注册",}
    email = forms.EmailField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入邮箱账号"}),
                             max_length=30,
                             error_messages = {
                                 "required":"账号密码不能为空",
                                 "invalid":"注册账号需为邮箱格式",})
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入密码"}),
                               min_length=8, max_length=50,
                               error_messages = {
                                   "required":"账号密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    captcha = CaptchaField(widget=CaptchaTextInput(
        attrs={"class": "form-control form-control-captcha fl","placeholder": "请输入验证码"}),
        error_messages = {"required":"请输入验证码","invalid":"验证码错误"})

    def clean_email(self):
            '''
            验证Email是否重复
            :return:
            '''
            email = self.cleaned_data["email"]
            try:
                UserProfile._default_manager.get(email=email)
            except UserProfile.DoesNotExist:
                return email
            raise forms.ValidationError(
                self.error_messages['duplicate_email'],
                code='duplicate_email',
            )

class MobileRegisterForm(forms.Form):
    '''
    手机账号注册的Form
    '''
    error_messages = {
        "duplicate_mobile": "该账号已被注册",
        "invaild": "注册账号需为手机格式",
        "nonmatch_mobile_code":"手机验证码输入错误，请重试",
        "overdue_mobile_code":"手机验证码已过期，请重试",
    }
    mobile = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control form-control-phone fl", "placeholder": "请输入手机号"}),
                             max_length=11, error_messages = {"required":"账号密码不能为空",})
    mobile_code = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入短信验证码"}),
                                  error_messages = {
                                      "required":"请输入手机验证码",})
    password_m = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入密码"}),
                               min_length=8, max_length=50,
                               error_messages = {
                                   "required":"账号密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    captcha_m = CaptchaField(widget=CaptchaTextInput(
        attrs={"class": "form-control form-control-captcha fl","placeholder": "请输入验证码"}),
                           error_messages = {"required":"请输入验证码","invalid":"验证码错误"})

    def clean_mobile(self):
        '''
        验证Mobile格式是否正确和是否重复
        :return:
        '''
        mobile = self.cleaned_data["mobile"]

        p=re.compile(settings.REGEX_MOBILE)
        if not p.match(mobile):
            raise forms.ValidationError(
                self.error_messages['invaild'],
                code='invaild',
                )

        try:
            UserProfile._default_manager.get(mobile=mobile)
        except UserProfile.DoesNotExist:
            return mobile
        raise forms.ValidationError(
             self.error_messages['duplicate_mobile'],
             code='duplicate_mobile',
        )

    def clean_mobile_code(self):
        '''
        验证手机验证码是否匹配和是否过期
        '''
        try:
            mobile = self.cleaned_data["mobile"]
            mobile_code = self.cleaned_data["mobile_code"]

            record = MobileVerifyRecord.objects.filter(Q(mobile=mobile), Q(code=mobile_code),Q(type=0)).order_by("-created")
            if record:
                if datetime.now()-timedelta(minutes=30) > record[0].created:
                    #手机验证码过期
                    raise forms.ValidationError(
                        self.error_messages['overdue_mobile_code'],
                        code='overdue_mobile_code',
                    )
            else:
                #手机验证码不匹配
                raise forms.ValidationError(
                    self.error_messages['nonmatch_mobile_code'],
                    code='nonmatch_mobile_code',
                )
        except Exception,e:
            #手机验证码不匹配
            raise forms.ValidationError(
                self.error_messages['nonmatch_mobile_code'],
                code='nonmatch_mobile_code',
                )

        return mobile_code

class FindPasswordForm(forms.Form):
    '''
    找回密码的Form
    '''
    error_messages = {"invaild": "该账号格式不正确","non_exist":"该账号尚未注册",}
    account = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入注册邮箱账号或手机号码"}),
                             max_length=50,error_messages = {"required":"账号不能为空",})
    captcha_f = CaptchaField(widget=CaptchaTextInput(
        attrs={"class": "form-control form-control-captcha fl","placeholder": "请输入验证码"}),
                             error_messages = {"required":"请输入验证码","invalid":"验证码错误"})

    def clean_account(self):
        '''
        验证账号输入格式是否为邮箱或手机
        :return:
        '''
        account = self.cleaned_data["account"]
        #邮箱或常用号码段的手机号格式
        p=re.compile(settings.REGEX_EMAIL+"|"+settings.REGEX_MOBILE)
        if not p.match(account):
            raise forms.ValidationError(
                self.error_messages['invaild'],
                code='invaild',
            )

        if UserProfile.objects.filter(Q(email=account) | Q(mobile=account)).count() == 0:
            raise forms.ValidationError(
                self.error_messages['non_exist'],
                code='non_exist',
            )

        return account

class FindPasswordMobileForm(forms.Form):
    '''
    找回密码的手机验证码验证界面
    '''

    error_messages = {
        "nonmatch_mobile_code":"手机验证码输入错误，请重试",
        "overdue_mobile_code":"手机验证码已过期，请重试",
    }
    mobile_f = forms.CharField(widget=forms.HiddenInput(),)
    mobile_code_f = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入短信验证码"}),
                                  error_messages = {
                                      "required":"请输入手机验证码",})

    def clean_mobile_code_f(self):
        '''
        验证手机验证码是否匹配和是否过期
        '''
        mobile_f = self.cleaned_data["mobile_f"]
        mobile_code_f = self.cleaned_data["mobile_code_f"]

        record = MobileVerifyRecord.objects.filter(Q(mobile=mobile_f), Q(code=mobile_code_f),Q(type=1)).order_by("-created")
        if record:
            if datetime.now()-timedelta(minutes=30) > record[0].created:
                #手机验证码过期
                raise forms.ValidationError(
                    self.error_messages['overdue_mobile_code'],
                    code='overdue_mobile_code',
                    )
        else:
            #手机验证码不匹配
            raise forms.ValidationError(
                self.error_messages['nonmatch_mobile_code'],
                code='nonmatch_mobile_code',
                )

        return mobile_code_f


class UpdatePasswordForm(forms.Form):
    '''
    找回密码-修改密码界面的Form
    '''
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入密码"}),
                               min_length=8, max_length=50,error_messages = {
                                   "required":"密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入确认密码"}),
                                min_length=8, max_length=50,error_messages = {
                                    "required":"确认密码不能为空",
                                    "min_length":"请输入至少8位密码",
                                    "max_length":"密码不能超过50位"})

    def clean(self):
        cleaned_data = super(UpdatePasswordForm, self).clean()
        password = cleaned_data.get('password', '')
        password2 = cleaned_data.get('password2', '')

        if password != password2:
            raise forms.ValidationError("两次输入密码不一致")

        return cleaned_data

# 用户保存信息表单

class UserInfoSave(forms.Form):
    error_messages = {"invaild": "手机号格式不正确","error_invald": "邮箱格式不正确","error_qq":"QQ格式不正确",'duplicate_email': "该Email被其他账户绑定.","duplicate_mobile":"该手机被其他账户绑定"}

    provinces_choices = []
    provinces = ProvinceDict.objects.all()
    for province in provinces:
        provinces_choices.append([province.id, province.name])
    citys_choices = []
    citys = CityDict.objects.all()
    for city in citys:
        citys_choices.append([city.id, city.name])
    uid= forms.CharField(widget=forms.HiddenInput())
    nick_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),
                             max_length=10, error_messages = {"required":"名字不能为空","max_length":"昵称（姓名）不能超过10位"})
    position = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),
                             max_length=50, required = False)
    prov = forms.ChoiceField(choices = (provinces_choices), required = True,widget=forms.Select(attrs={"class": "city form-control"}))
    city = forms.ChoiceField(choices = (citys_choices), required = True,widget=forms.Select(attrs={"class": "city form-control"}))
    description = forms.CharField(widget=forms.Textarea(attrs={"class": "form-control",'cols':60,'rows':8}),
                             max_length=500,required = False)
    qq = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),
                             max_length=20, required=False)
    mobile = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),
                             max_length=11,required=False)
    email = mobile = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),
                             max_length=50, required=False)
    def clean_mobile(self):
        '''
        验证Mobile格式是否正确
        :return:
        '''
        mobile = self.cleaned_data["mobile"]
        if mobile == "":
           mobile = None
        else:
            p=re.compile(settings.REGEX_MOBILE)
            if not p.match(mobile):
                raise forms.ValidationError(
                    self.error_messages['invaild'],
                    code='invaild',
                    )

        uid=self.cleaned_data.get('uid')
        obj= UserProfile.objects.filter(Q(mobile=mobile) & ~Q(id=uid) & ~Q(mobile=None))
        if obj:
            raise forms.ValidationError(
            self.error_messages['duplicate_mobile'],
            code='duplicate_mobile',
            )
        return mobile

    def clean_email(self):
        '''
        验证账号输入格式是否为邮箱
        :return:
        '''
        email = self.cleaned_data["email"]
        #邮箱或常用号码段的手机号格式
        if email=="":
            return ""
        p=re.compile(settings.REGEX_EMAIL)
        if not p.match(email):
            raise forms.ValidationError(
                self.error_messages['error_invald'],
                code='invaild',
                )
        uid=self.cleaned_data.get('uid')

        obj= UserProfile.objects.filter(Q(email=email) & ~Q(id=uid))
        if obj:
            raise forms.ValidationError(
            self.error_messages['duplicate_email'],
            code='duplicate_email',
            )
        else:
            return email

    def clean_qq(self):
        '''
        验证账号输入格式是否为QQ
        :return:
        '''
        qq = self.cleaned_data["qq"]
        #邮箱或常用号码段的手机号格式
        if qq!="":
            p=re.compile(settings.REGEX_QQ)
            if not p.match(qq):
                raise forms.ValidationError(
                    self.error_messages['error_qq'],
                    code='invaild',
                    )

        return qq

class ChangePassword(forms.Form):
    '''
    找回密码-修改密码界面的Form
    '''
    original_pass = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入原密码"}),
                               min_length=8, max_length=50,error_messages = {
                                   "required":"密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    newpass = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请输入新密码"}),
                               min_length=8, max_length=50,error_messages = {
                                   "required":"新密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    newpass1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "请确认新密码"}),
                               min_length=8, max_length=50,error_messages = {
                                   "required":"新密码不能为空",
                                   "min_length":"请输入至少8位密码",
                                   "max_length":"密码不能超过50位"})
    def clean(self):
        cleaned_data = super(ChangePassword, self).clean()
        newpass = cleaned_data.get('newpass', '')
        newpass1 = cleaned_data.get('newpass1', '')

        if newpass != newpass1:
            raise forms.ValidationError("两次输入密码不一致")

        return cleaned_data

class UpdateMobileForm(forms.Form):
    '''
    修改手机账号的Form
    '''
    error_messages = {"invaild": "手机号格式不正确","exist":"该手机号已被其他用户绑定",}
    uid_um = forms.CharField(widget=forms.HiddenInput())
    mobile_um = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入手机号码"}),
                              max_length=50,error_messages = {"required":"请输入手机号",})
    captcha_um = CaptchaField(widget=CaptchaTextInput(
        attrs={"class": "form-control form-control-captcha fl","placeholder": "请输入验证码"}),
                             error_messages = {"required":"请输入验证码","invalid":"验证码错误"})

    def clean_mobile_um(self):
        '''
        验证账号输入格式是否为手机
        :return:
        '''
        uid_um = self.cleaned_data['uid_um']
        mobile_um = self.cleaned_data["mobile_um"]
        #手机号格式
        p=re.compile(settings.REGEX_MOBILE)
        if not p.match(mobile_um):
            raise forms.ValidationError(
                self.error_messages['invaild'],
                code='invaild',
                )

        if UserProfile.objects.filter(Q(mobile=mobile_um) & ~Q(id=uid_um) & ~Q(mobile=None)).count() > 0:
            raise forms.ValidationError(
                self.error_messages['exist'],
                code='exist',
                )

        return mobile_um

class UpdateEmailForm(forms.Form):
    '''
    修改邮箱的Form
    '''
    error_messages = {"invaild": "邮箱格式不正确","exist":"该邮箱已被其他用户绑定",}
    uid_ue = forms.CharField(widget=forms.HiddenInput())
    email_ue = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入邮箱"}),
                                max_length=50,error_messages = {"required":"请输入邮箱",})
    captcha_ue = CaptchaField(widget=CaptchaTextInput(
        attrs={"class": "form-control form-control-captcha fl","placeholder": "请输入验证码"}),
                              error_messages = {"required":"请输入验证码","invalid":"验证码错误"})

    def clean_email_ue(self):
        '''
        验证账号输入格式是否为邮箱
        :return:
        '''
        uid_ue = self.cleaned_data['uid_ue']
        email_ue = self.cleaned_data["email_ue"]
        #手机号格式
        p=re.compile(settings.REGEX_EMAIL)
        if not p.match(email_ue):
            raise forms.ValidationError(
                self.error_messages['invaild'],
                code='invaild',
                )

        if UserProfile.objects.filter(Q(email=email_ue) & ~Q(id=uid_ue) & ~Q(email=None)).count() > 0:
            raise forms.ValidationError(
                self.error_messages['exist'],
                code='exist',
                )

        return email_ue
