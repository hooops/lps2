# -*- coding: utf-8 -*-
import xadmin
from models import *
from xadmin.plugins.auth import UserAdmin
from forms import UserCreationForm, UserChangeForm
from xadmin.layout import Fieldset, Main, Side, Row

class CountryDictAdmin(object):
    pass

class ProvinceDictAdmin(object):
    pass

class CityDictAdmin(object):
    pass

class BadgeDictAdmin(object):
    pass

class CertificateAdmin(object):
    pass

class RegisterWayAdmin(object):
    pass

class MyCourseInline(object):
    model = MyCourse
    extra = 1
    style = 'accordion'

class UserLearningLessonInline(object):
    model = UserLearningLesson
    extra = 1
    style = 'accordion'

class MyFavoriteInline(object):
    model = MyFavorite
    extra = 1
    style = 'accordion'

class UserUnlockStageInline(object):
    model = UserUnlockStage
    extra = 1
    style = 'accordion'

#继承xadmin的UserAdmin以定制User的Admin界面
class UserProfileAdmin(UserAdmin):

    list_display = ('nick_name', 'email', 'mobile', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser')
    search_fields = ('first_name', 'last_name', 'email', 'mobile', 'nick_name')
    ordering = ('date_joined',)
    inlines = [MyCourseInline, MyFavoriteInline, UserUnlockStageInline, UserLearningLessonInline]

    def get_model_form(self, **kwargs):
        if self.org_obj is None:
            self.form = UserCreationForm
        else:
            self.form = UserChangeForm
        return super(UserAdmin, self).get_model_form(**kwargs)

    def get_form_layout(self):
        if self.org_obj:
            self.form_layout = (
                Main(
                    Fieldset('登录信息',
                             Row('email', 'mobile'),
                             'password',
                             #css_class='unsort no_title'
                    ),
                    Fieldset('个人信息',
                             Row('avatar_url', 'avatar_middle_thumbnall', 'avatar_small_thumbnall'),
                             Row('first_name', 'last_name'),
                             Row('nick_name', 'qq'),
                             Row('valid_email', 'valid_mobile'),
                    ),
                    Fieldset('VIP信息',
                             'is_vip', 'date_limit'
                    ),
                    Fieldset('权限信息',
                             'groups', 'user_permissions'
                    ),
                    Fieldset('日期信息',
                             'last_login', 'date_joined'
                    ),
                    ),
                Side(
                    Fieldset('Status',
                             'is_active', 'is_staff', 'is_superuser',
                             ),
                    )
            )
        return super(UserAdmin, self).get_form_layout()

xadmin.site.register(CountryDict, CountryDictAdmin)
xadmin.site.register(ProvinceDict, ProvinceDictAdmin)
xadmin.site.register(CityDict, CityDictAdmin)
xadmin.site.register(BadgeDict, BadgeDictAdmin)
xadmin.site.register(Certificate, CertificateAdmin)
xadmin.site.register(RegisterWay, RegisterWayAdmin)
#注册UserProfile需先取消UserProfile的注册，因为系统自动已按get_user_model注册了User对象
xadmin.site.unregister(UserProfile)
xadmin.site.register(UserProfile, UserProfileAdmin)
