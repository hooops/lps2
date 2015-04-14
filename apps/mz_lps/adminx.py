import xadmin
from models import *

# Register your models here.
class ClassStudentsInline(object):
    model = ClassStudents
    extra = 1
    style = 'accordion'

class ClassAdmin(object):
    list_display = ('coding', 'date_open','teacher','id')
    search_fields = ['coding','teacher']
    inlines = [ClassStudentsInline,]

class PlanningAdmin(object):
    list_display = ('user', 'career_course','date_publish','id')
    search_fields = ['relation_id','description']

class PlanningItemAdmin(object):
    list_display = ('planning', 'course','need_days','id')
    search_fields = ['course','planning']

class PlanningPauseAdmin(object):
    list_display = ('planning', 'pause_date','restore_date','reason','id')

class ExamineAdmin(object):
    list_display = ('examine_type', 'relation_type','relation_id','id')
    search_fields = ['relation_id','description']

class HomeworkAdmin(object):
    list_display = ('examine_type', 'relation_type','relation_id','id')
    search_fields = ['relation_id','description']

class ProjectAdmin(object):
    list_display = ('examine_type', 'relation_type','relation_id','id')
    search_fields = ['relation_id','description']

class PaperAdmin(object):
    list_display = ('examine_type', 'relation_type','relation_id','id')
    search_fields = ['relation_id','description']

class QuizAdmin(object):
    list_display = ('question', 'paper','index','id')
    search_fields = ['question','item_list']

class CodeExerciseAdmin(object):
    pass

class MissionAdmin(object):
    pass

class ExamineRecordAdmin(object):
    pass

class HomeworkRecordAdmin(object):
    pass

class ProjectRecordAdmin(object):
    pass

class PaperRecordAdmin(object):
    pass

class QuizRecordAdmin(object):
    pass

class CodeExerciseRecordAdmin(object):
    pass

class MissionRecordAdmin(object):
    pass

class CourseScoreAdmin(object):
    pass

xadmin.site.register(Class, ClassAdmin)
xadmin.site.register(Planning, PlanningAdmin)
xadmin.site.register(PlanningItem, PlanningItemAdmin)
xadmin.site.register(PlanningPause, PlanningPauseAdmin)
xadmin.site.register(Examine, ExamineAdmin)
xadmin.site.register(Homework, HomeworkAdmin)
xadmin.site.register(Project, ProjectAdmin)
xadmin.site.register(Paper, PaperAdmin)
xadmin.site.register(Quiz, QuizAdmin)
xadmin.site.register(CodeExercise, CodeExerciseAdmin)
xadmin.site.register(Mission, MissionAdmin)
xadmin.site.register(ExamineRecord, ExamineRecordAdmin)
xadmin.site.register(HomeworkRecord, HomeworkRecordAdmin)
xadmin.site.register(ProjectRecord, ProjectRecordAdmin)
xadmin.site.register(PaperRecord, PaperRecordAdmin)
xadmin.site.register(QuizRecord, QuizRecordAdmin)
xadmin.site.register(CodeExerciseRecord, CodeExerciseRecordAdmin)
xadmin.site.register(MissionRecord, MissionRecordAdmin)
xadmin.site.register(CourseScore, CourseScoreAdmin)
