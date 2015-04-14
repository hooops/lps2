import xadmin
from models import *

class AcademicStageInline(object):
    model = AcademicStage
    extra = 1
    style = 'accordion'

class AcademicClassInline(object):
    model = AcademicClass
    extra = 1
    style = 'accordion'

class ProvinceCityAdmin(object):
    list_display = ('name', 'index', 'id')
    search_fields = ('name',)

class AcademicOrgAdmin(object):
    list_display = ('name', 'level', 'parent', 'province_city', 'id')
    search_fields = ('name', 'province_city')

class CourseTypeAdmin(object):
    list_display = ('name', 'index', 'id')
    search_fields = ('name',)

class AcademicCourseAdmin(object):
    list_display = ('name', 'description', 'description', 'course_type', 'id')
    search_fields = ('name',)
    inlines = [AcademicStageInline, AcademicClassInline]

class AcademicStageAdmin(object):
    list_display = ('name', 'description', 'id')
    search_fields = ('name',)

class AcademicClassAdmin(object):
    list_display = ('coding', 'date_publish', 'teacher', 'id')
    search_fields = ('coding',)

class NotificationAdmin(object):
    list_display = ('title', 'url', 'owner', 'id')
    search_fields = ('title',)

class AcademicUserAdmin(object):
    list_display = ('user_no', 'stu_name', 'verify_code', 'user', 'academic_course', 'owner_college', 'owner_university', 'is_binded', 'binded_date', 'id')
    search_fields = ('user_no', 'stu_name', 'academic_course', 'owner')


xadmin.site.register(ProvinceCity, ProvinceCityAdmin)
xadmin.site.register(AcademicOrg, AcademicOrgAdmin)
xadmin.site.register(CourseType, CourseTypeAdmin)
xadmin.site.register(AcademicCourse, AcademicCourseAdmin)
xadmin.site.register(AcademicStage, AcademicStageAdmin)
xadmin.site.register(AcademicClass, AcademicClassAdmin)
xadmin.site.register(Notification, NotificationAdmin)
xadmin.site.register(AcademicUser, AcademicUserAdmin)