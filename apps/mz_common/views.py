# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse,HttpResponsePermanentRedirect,HttpResponseRedirect
from django.db.models import Sum
from django.conf import settings
from django.core.paginator import Paginator
from django.core.paginator import PageNotAnInteger
from django.core.paginator import EmptyPage
from django.contrib.auth.models import Group
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.db.models import Q
from django.core.cache import cache
from mz_common.models import *
from mz_user.forms import *
from mz_course.models import *
from mz_lps.models import *
from utils.tool import upload_generation_dir
from utils import xinge
import json, logging, os, uuid,urllib2,urllib
from itertools import chain

logger = logging.getLogger('mz_common.views')


def get_recommended_readings():
    readings = RecommendedReading.objects.all()
    rearranged_readings = {RecommendedReading.ACTIVITY: [], RecommendedReading.NEWS: [], RecommendedReading.DISCUSS: []}
    for reading in readings:
        rearranged_readings[reading.reading_type].append(reading)

    return {'readings': rearranged_readings, 'reading_types': RecommendedReading.READING_TYPES}

def index_front(request):
    if request.user.is_authenticated() and (request.user.is_student() or request.user.is_teacher()):
        is_jump = request.COOKIES.get('is_jump',None)
        f_number = request.COOKIES.get('f_number',True)
        if is_jump is None and f_number == True:
            response = HttpResponseRedirect("/user/center")
            response.set_cookie("f_number",1)
            return HttpResponseRedirect("/user/center")

    template_vars = cache.get('index_front')
    if not template_vars:
        ad = Ad.objects.all()
        text_links = Links.objects.filter(is_pic = 0)
        pic_links = Links.objects.filter(is_pic = 1)
        teachers = teacher_list()
        most_courses = []
        new_courses = Course.objects.filter(Q(is_click=True), Q(is_homeshow=True)).order_by('-date_publish')
        n_pn,n_pt,n_pl,n_pp,n_np,n_ppn,n_npn,n_cp,n_pr = instance_pager(new_courses,int(1),settings.GLOBAL_PAGESIZE) #最新课程列表，默认第一页
        n_pn = range(1,int(n_pn)+1)
        lesson_group=Lesson.objects.values('course').annotate(s_amount = Sum('play_count')).order_by('-s_amount')
        for le in lesson_group:
            try:
                cours = Course.objects.get(id=le['course'], is_click=True, is_homeshow=True)
                most_courses.append(cours)
            except:
                pass

        m_pn,m_pt,m_pl,m_pp,m_np,m_ppn,m_npn,m_cp,m_pr = instance_pager(most_courses,int(1),settings.GLOBAL_PAGESIZE) #最多课程列表，默认第一页
        m_pn = range(1,int(m_pn)+1)
        hot_courses=Course.objects.filter(Q(is_click=True), Q(is_homeshow=True)).order_by('-favorite_count').all()
        h_pn,h_pt,h_pl,h_pp,h_np,h_ppn,h_npn,h_cp,h_pr = instance_pager(hot_courses,int(1),settings.GLOBAL_PAGESIZE) #热门课程列表，默认第一页
        h_pn = range(1,int(h_pn)+1)

        # 首页SEO信息读取
        seo = PageSeoSet()
        try:
            seo = PageSeoSet.objects.get(page_name='1')
        except Exception,e:
            logger.error(e)

        recommended_readings = get_recommended_readings()

        template_vars = {'ad': ad, 'n_pl': n_pl, 'n_pn': n_pn, 'n_cp': n_cp, 'm_pl': m_pl, 'm_pn': m_pn, 'm_cp': m_cp, 'h_pl': h_pl, 'h_pn': h_pn, 'h_cp': h_cp,
                         'teachers': teachers, 'text_links': text_links, 'pic_links': pic_links, 'seo':seo, 'recommended_readings':recommended_readings}

        cache.set('index_front', template_vars, settings.CACHE_TIME)

    return render(request, 'base_index.html', template_vars)

#首页ajax切换课程
def index_course_ajax_page(request):
    types = request.GET['type']
    page = request.GET['page']
    template_vars = cache.get('index_course_ajax_page_'+str(types)+'_'+str(page))
    if not template_vars:
        json_str = '['
        if types == "new":
            courses = Course.objects.filter(Q( is_click = True )).order_by('-date_publish')
        if types == "most":
            lesson_group=Lesson.objects.values('course').annotate(s_amount = Sum('play_count')).order_by('-s_amount')
            courses = []
            for le in lesson_group:
                try:
                    cours = Course.objects.get(id = le['course'] , is_click = True )
                    courses.append(cours)
                except:
                    pass
        if types=="hot":
            courses=Course.objects.filter(Q( is_click = True )).order_by('-favorite_count').all()

        pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(courses,int(page),settings.GLOBAL_PAGESIZE)
        # for li in pl:
        #   json_str+='{"name":"'+str(li.name)+'","image":"'+settings.MEDIA_URL+str(li.image)+'","student_count":"'+str(li.student_count)+'","course_id":'+str(li.id)+'},'
        # json_str=json_str[:-1]
        # json_str +=']'
        # return HttpResponse(json_str)
        p_json = [{"name": p.name,
                    "image": settings.MEDIA_URL+str(p.image),
                      "student_count":p.student_count,
                      "course_id": p.id} for p in pl]

        template_vars = p_json

        cache.set('index_course_ajax_page_'+str(types)+'_'+str(page), template_vars, settings.CACHE_TIME)

    return HttpResponse(json.dumps(template_vars), content_type="application/json")

def teacher_list():
    try:
        group = Group.objects.get(name = '老师')   #所有老师
        te_list = Course.objects.distinct().values_list('teacher')
        teachers = group.user_set.filter(id__in = te_list).order_by("index", "id")

    except Exception, e:
        logger.error(e)
        return None
    return teachers

#404错误页面
def page_not_found(request):
    #这段代码以后要去掉
    path_url =  request.path
    arr_path =  path_url.split('/')
    list_2 = [i for i in arr_path if i != '']
    arr_len = len(list_2)
    if arr_len == 2:
        CourseType = list_2[0]
        CourseNum = list_2[1]
        if CourseType=="career":
            if int(CourseNum) == 10:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/7/")
            elif int(CourseNum) == 11:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/3/")
            elif int(CourseNum) == 2521:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/3/")
            elif int(CourseNum) == 2526:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/")
            elif int(CourseNum) == 2670:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/3/")
            elif int(CourseNum) == 2672:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/8/")
        if CourseType =='news':
            return HttpResponsePermanentRedirect("http://forum.maiziedu.com")
    if arr_len ==3 and list_2[1]=='node':
            if list_2[0] =='search':
                if list_2[2] == 'Java':
                    return HttpResponsePermanentRedirect("http://www.maiziedu.com/pages/ad01/java01.html?osc=java")
                if list_2[2] == 'PHP':
                    return HttpResponsePermanentRedirect("http://www.maiziedu.com/pages/ad01/php01.html?osc=php")
            return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/")

    return render(request, 'mz_common/404.html')

#500错误页面
def page_error(request):
    return render(request, 'mz_common/500.html')

# 维护模式页面
def page_maintenance(request):
    fileHandle = open('maintenance.txt')
    fileList = fileHandle.readlines()
    fileHandle.close()
    return render(request, 'mz_common/503.html', locals())

#定义共用的上下文处理器
def common_context(request):
    email_register_form = EmailRegisterForm()
    mobile_register_form = MobileRegisterForm()
    find_password_form = FindPasswordForm()
    update_password_form = UpdatePasswordForm()
    find_password_mobile_form = FindPasswordMobileForm()
    login_form = LoginForm()
    #最新消息条数
    new_message_count = MyMessage.objects.filter(Q(userB = request.user.id) | Q(userB = 0,action_type = 1), Q(is_new=True)).count()
    bbs_site_url = settings.BBS_SITE_URL

    locals = {
        "email_register_form": email_register_form,
        "mobile_register_form": mobile_register_form,
        "find_password_form": find_password_form,
        "update_password_form": update_password_form,
        "find_password_mobile_form": find_password_mobile_form,
        "login_form": login_form,
        "new_message_count": new_message_count,
        "bbs_site_url": bbs_site_url,
    }
    return locals

# 论坛消息条数调用接口
@csrf_exempt
def get_new_message_count(request):
    #最新消息条数
    new_message_count = 0
    if request.user.is_authenticated():
        new_message_count = MyMessage.objects.filter(Q(userB = request.user.id) | Q(userB = 0,action_type = 1), Q(is_new=True)).count()
    return HttpResponse(new_message_count)

# APP下载终端扫描地址
def terminal(request):
    ANDROID_DOWN_URL = settings.ANDROID_DOWN_URL
    IOS_DOWN_URL = settings.IOS_DOWN_URL
    WINPHONE_DOWN_URL = settings.WINPHONE_DOWN_URL
    IPAD_DOWN_URL = settings.IPAD_DOWN_URL
    return render(request, 'mz_common/terminal.html', locals())

# 热门搜索关键词推荐
def recommend_keyword(request):
    template_vars = cache.get('recommend_keyword')
    if not template_vars:
        try:
            keywords = RecommendKeywords.objects.all()[:10]
            keywords = [{"name": keyword.name} for keyword in keywords]
        except Exception as e:
            keywords = []

        template_vars = keywords

        cache.set('recommend_keyword', template_vars, settings.CACHE_TIME)

    return HttpResponse(json.dumps(template_vars),
                            content_type="application/json")

# 课程搜索
def course_search(request):
    keyword = request.GET['keyword'] or ""

    try:

        if keyword == "":
            courses = []
            careerCourses = []
            raise Exception()

        courses = Course.objects.filter(Q(name__icontains=keyword) |
                                        Q(search_keywords__name__icontains=keyword), Q(is_click=True), Q(is_homeshow=True)
        ).distinct()
        careerCourses = CareerCourse.objects.filter(Q(name__icontains=keyword) |
                                                    Q(search_keywords__name__icontains=keyword), Q(course_scope=None)
        ).distinct()
        courses = [{"id": course.id,
                    "name": course.name,
                    "course_color":course.stages.career_course.course_color if hasattr(course.stages,"career_course") else settings.DEFAULT_COLOR,
                    "image": str(course.image)} for course in courses]
        careerCourses = [{"id": course.id,
                          "name": course.name,
                          "course_color":course.course_color,
                          "image": str(course.image)} for course in careerCourses]

    except Exception as e:
        courses = []
        careerCourses = []
        logger.error(e)

    finally:
        coursesResult = {"courses": courses,"career_courses": careerCourses}
        return HttpResponse(json.dumps(coursesResult),content_type="application/json")

############### lps 开始##############################
# 获取该用户是第几次重修某个课程
def get_rebuild_count(user, course):
    '''
    获取该用户是第几次重修某个课程
    :param user: 用户对象
    :param course: 课程对象
    :return:
    '''
    try:
        course_score = CourseScore.objects.filter(user=user, course=course).order_by("-rebuild_count")
        if len(course_score)>0:
            return course_score[0].rebuild_count
    except Exception,e:
        logger.error(e)
    return 0

# 获取某个试卷下学生还未完成的试题列表
def get_uncomplete_quiz(user, paper, rebuild_count):
    '''
    获取某个试卷下学生还未完成的试题列表
    :param user: 用户对象
    :param paper: 试卷对象
    :param rebuild_count: 第几次重修
    :return:
    '''
    # 已经做过的试题ID列表
    quiz_record_list = []
    # 获取做题记录
    paper_record_list = PaperRecord.objects.filter(paper=paper,student=user,rebuild_count=rebuild_count)
    if len(paper_record_list) > 0:
        quiz_record_list = QuizRecord.objects.filter(paper_record=paper_record_list[0]).values_list("quiz")
        # 已经做过的题目则不再显示
    return Quiz.objects.filter(Q(paper=paper),~Q(id__in=quiz_record_list))

# 检查测验分所有考核项是否已经完成
def check_exam_is_complete(user, course):
    '''
    检查测验分所有考核项是否已经完成
    :param user: 用户对象
    :param course: 课程对象
    :return: 0 考核未完成，1 考核已完成，2 没有考核项
    '''
    course_score = CourseScore.objects.filter(user=user, course=course).order_by("-rebuild_count")
    exam_status = check_exam_item_status(course)

    if exam_status['has_count'] == 0:
        return 2
    if len(course_score) > 0:
        # 检查是否完成项目考核并评分
        # 检查是否完成项目测验
        if exam_status['course_has_project']:
            project_list = Project.objects.filter(examine_type=5, relation_type=2, relation_id=course.id)
            if len(project_list) > 0:
                if ProjectRecord.objects.filter(Q(project=project_list[0]),Q(student=user),Q(rebuild_count=course_score[0].rebuild_count),~Q(score=None)).count() == 0:
                    return 0
        # 检查是否完成课程总测验
        if exam_status['course_has_exam']:
            # 获取所有章节对应的paper
            # if paper_list is None:
            paper_list = Paper.objects.filter(examine_type=2, relation_type=2, relation_id=course.id)
            # 检查试卷是否完成
            if not check_iscomplete_paper_exam(paper_list,user,course_score[0].rebuild_count):
                return 0
        # 检查是否完成所有随堂测验
        if exam_status['lesson_has_exam']:
            # 获取该课程下所有lesson的测验是否已经完成并评分
            # 有随堂测验考核项的所有章节ID列表
            lesson_has_exam_list=[]
            # 获取该课程下所有章节ID列表
            lesson_list = course.lesson_set.all().values_list("id")
            for lesson in lesson_list:
                if lesson_has_exam(lesson[0]):
                    lesson_has_exam_list.append(lesson[0])
            # 获取所有章节对应的paper
            # if paper_list is None:
            paper_list = Paper.objects.filter(examine_type=2, relation_type=1, relation_id__in=lesson_has_exam_list)
            # 继续检查试卷试题是否有做完
            if not check_iscomplete_paper_exam(paper_list,user,course_score[0].rebuild_count):
                return 0
        return 1
    return 0

# 检查学生是否已经完成试卷
def check_iscomplete_paper_exam(paper_list,user,rebuild_count):
    for paper in paper_list:
        quiz_count = Quiz.objects.filter(paper=paper).count() #试卷拥有的题目数量
        paper_record = PaperRecord.objects.filter(Q(paper=paper),Q(student=user),Q(rebuild_count=rebuild_count),~Q(score=None)) #试卷对应考核记录
        if len(paper_record) > 0:
            quizrecord_count = QuizRecord.objects.filter(paper_record=paper_record).count() # 学生已做的试题数量
            if quiz_count > quizrecord_count:
                return False  # 还有题目未做完
        else:
            return False  #还有试卷未完成
    return True

# 更新学力和测验分
def update_study_point_score(student, study_point=None, score=None, examine=None, examine_record=None, teacher=None, course=None, rebuild_count=None):
    '''
    更新学力和测验分
    :param student: 学生对象
    :param study_point: 学力加分（可选项）
    :param score: 测验分加分（可选项）
    :param examine: 考核对象（可选项）
    :param examine_record: 考核记录对象（可选项）
    :param teacher: 老师对象（可选项）
    :param course: 课程（可选项）,更新非考核产生的学力和学分时候需传入
    :param rebuild_count: 第几次重修（可选项）
    :return:
    '''
    if course is None:
        cur_course = Course()
    else:
        cur_course = course
    # 根据考核对象类型找到相应对象
    # 章节
    if examine is not None and examine_record is not None:
        if examine.relation_type == 1:
            cur_lesson = Lesson.objects.filter(pk=examine.relation_id)
            if len(cur_lesson) > 0:
                cur_course = cur_lesson[0].course
        #课程
        elif examine.relation_type == 2:
            cur_course = Course.objects.filter(pk=examine.relation_id)
            if len(cur_course)  > 0:
                cur_course = cur_course[0]

        if rebuild_count is None:
            rebuild_count = get_rebuild_count(student, cur_course)

        # 更新考核记录学力
        if score is not None:
            examine_record.score = score  # 计算该试卷测验得分
            if teacher is not None:
                examine_record.teacher = teacher
        if study_point is not None:
            examine_record.study_point = study_point   # 学力
        examine_record.save()

        # 在coursescore中更新测验分
        check_course_score(student, cur_course) # 检查是否有course_score记录,没有则创建
        if examine.examine_type in(2,5) and score is not None:
            course_score = CourseScore.objects.filter(user=student,course=cur_course,rebuild_count=rebuild_count)
            if len(course_score):
                # 考试测验
                # 试卷类型测验分
                if examine.examine_type == 2:
                    # 随堂测验
                    if examine.relation_type == 1:
                        # 获取所有章节id列表
                        lesson_list = cur_course.lesson_set.all().values_list("id")
                        lesson_total_score = 0
                        # 获取所有章节对应的paper
                        paper_list = Paper.objects.filter(examine_type=2, relation_type=1, relation_id__in=lesson_list).values_list("id")
                        # 获取所有章节对应的paperrecord
                        paper_record_list = PaperRecord.objects.filter(Q(student=student),Q(paper__in=paper_list),Q(rebuild_count=rebuild_count),~Q(score=None))
                        # 计算随堂测验总分
                        for paper_record in paper_record_list:
                            lesson_total_score += (100 / len(paper_list)) * paper_record.accuracy
                        course_score[0].lesson_score = int(round(lesson_total_score))
                    # 课程总测验
                    elif examine.relation_type == 2:
                        course_score[0].course_score = score
                # 项目类型测验分
                elif examine.examine_type == 5:
                    course_score[0].project_score = score
                # 检查测验分考核项是否已经完全考核
                if check_exam_is_complete(student, cur_course) == 1:
                    course_score[0].is_complete = True  # 所有测验完成状态
                    course_score[0].complete_date = datetime.now()  # 测验完成时间
                    career_course = cur_course.stages.career_course
                    # 如已完成所有考核项，则发送课程通过与否的站内消息
                    total_score = get_course_score(course_score[0], cur_course)
                    if total_score >= 60:
                        sys_send_message(0, student.id, 1, "恭喜您已通过<a href='/lps/learning/plan/"+str(career_course.id)+"/'>"+
                                                           str(cur_course.name)+"</a>课程，总获得测验分"+str(total_score)+
                                                           "分！<a href='/lps/learning/plan/"+str(career_course.id)+"/'>继续学习下一课</a>")
                    else:
                        sys_send_message(0, student.id, 1, "您的课程<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(cur_course.stages.id)+"'>"+str(cur_course.name)+
                                                           "</a>挂科啦。不要灰心，<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(cur_course.stages.id)+"'>去重修</a>")
                    # 继续检查是否完成该阶段的所有考核项
                    if check_stage_exam_is_complete(student, cur_course):
                        # 如果完成了所有考核项，则检查该课程对应职业课程的所有阶段和解锁信息
                        stage_list = Stage.objects.filter(career_course=cur_course.stages.career_course)
                        cur_stage_count = 0
                        for i,stage in enumerate(stage_list):
                            if stage == cur_course.stages:
                                cur_stage_count = i
                                break
                        if (cur_stage_count+1) < len(stage_list):
                            # 检查下一个阶段是否已经解锁
                            if UserUnlockStage.objects.filter(user=student, stage=stage_list[cur_stage_count+1]).count()>0:
                                # 已经解锁
                                msg = "恭喜您能努力坚持学完"+career_course.name+"的第"+str(cur_stage_count+1)+"阶段，赶快继续深造吧，你离梦想仅一步之遥了哦！<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_list[cur_stage_count+1].id)+"'>立即学习下一阶段</a>"
                            else:
                                # 还未解锁
                                msg = "恭喜您能努力坚持学完"+career_course.name+"的第"+str(cur_stage_count+1)+"阶段，赶快续费继续深造吧，你离梦想仅一步之遥了哦！<a href='/lps/learning/plan/"+str(career_course.id)+"/?stage_id="+str(stage_list[cur_stage_count+1].id)+"'>立即购买下一阶段</a>"
                        else:
                            msg = "恭喜您能努力坚持学完"+career_course.name+"所有课程，你还可以继续深造哦！<a href='/course/'>去选课程</a>"
                        sys_send_message(0, student.id, 1, msg)
                else:
                    # 如果是未完成所有考核项，但是测验分已经超过了60分，则可以判定课程通过，提前更新课程测验完成状态
                    if get_course_score(course_score[0], cur_course) >= 60:
                        course_score[0].is_complete = True  # 所有测验完成状态
                course_score[0].save()

    # 更新班级学力汇总信息
    if study_point > 0 and rebuild_count == 0:
        class_students = ClassStudents.objects.filter(user=student,student_class__career_course=cur_course.stages.career_course)
        if len(class_students)>0:
            class_students[0].study_point += study_point
            class_students[0].save()

# 检查某个阶段的所有考核项是否都已经完成
def check_stage_exam_is_complete(student, cur_course):
    # 根据当前课程找到对应阶段下所有课程
    course_list = Course.objects.filter(stages=cur_course.stages)
    for course in course_list:
        if course == cur_course:
            continue
        # 检查课程是否完成
        if check_exam_is_complete(student, course) == 0:
            return False
        if check_exam_is_complete(student, course) == 2:
            continue
    return True

# 检查课程各个考核项的状态
def check_exam_item_status(course):
    has_count = 0 # 测验分考核项计数
    lesson_has_exam = False
    course_has_exam = False
    course_has_project = False
    try:
        # 判断课程拥有几项评测分项（随堂测验？总测验？项目制作？）
        # 是否有随堂测验
        # 根据找到对应的paper
        paper_list = Paper.objects.filter(examine_type=2, relation_type=1,
                                          relation_id__in=course.lesson_set.all().values_list("id"))
        if Quiz.objects.filter(paper__in=paper_list).count() > 0:
            lesson_has_exam = True
            has_count += 1

        # 是否有总测验
        paper = Paper.objects.filter(examine_type=2, relation_type=2, relation_id=course.id)
        if Quiz.objects.filter(paper__in=paper).count() > 0:
            course_has_exam = True
            has_count += 1

        # 是否有项目制作
        if course.has_project and Project.objects.filter(examine_type=5, relation_type=2, relation_id=course.id).count() > 0:
            course_has_project = True
            has_count += 1
    except Exception,e:
        logger.error(e)
    return {'has_count':has_count,
            'lesson_has_exam':lesson_has_exam,
            'course_has_exam':course_has_exam,
            'course_has_project':course_has_project}


# 获取用户某门课程实际得分
def get_course_score(course_score, course=None):
    score = 0
    try:
        if course == None:
            course = Course.objects.get(pk=course_score.course.id)

        # 获取课程的各个考核项状态
        exam_status = check_exam_item_status(course)

        #Modify By Steven YU
        if course_score.lesson_score is None:
            ls=0
        else:
            ls=course_score.lesson_score

        if course_score.course_score is None:
            cs=0
        else:
            cs=course_score.course_score
        if course_score.project_score is None:
            ps=0
        else:
            ps = course_score.project_score
        #Modify end

        if exam_status['has_count'] == 3:
            score = int(ls * settings.LESSON_EXAM_RATE + cs * settings.COURSE_EXAM_RATE + ps * settings.PROJECT_EXAM_RATE)
        elif exam_status['has_count'] == 2:
            # 随堂测验+课堂总测验
            if exam_status['lesson_has_exam'] and exam_status['course_has_exam']:
                lesson_exam_rate = settings.LESSON_EXAM_RATE/(settings.LESSON_EXAM_RATE+settings.COURSE_EXAM_RATE)
                course_exam_rate = settings.COURSE_EXAM_RATE/(settings.LESSON_EXAM_RATE+settings.COURSE_EXAM_RATE)
                score = ls * lesson_exam_rate + cs * course_exam_rate
            # 课堂总测验+项目制作
            elif exam_status['course_has_exam'] and exam_status['course_has_project']:
                course_exam_rate = settings.COURSE_EXAM_RATE/(settings.COURSE_EXAM_RATE+settings.PROJECT_EXAM_RATE)
                project_exam_rate = settings.PROJECT_EXAM_RATE/(settings.COURSE_EXAM_RATE+settings.PROJECT_EXAM_RATE)
                score = cs * course_exam_rate + ps * project_exam_rate
            # 随堂测验+项目制作
            elif exam_status['lesson_has_exam'] and exam_status['course_has_project']:
                lesson_exam_rate = settings.LESSON_EXAM_RATE/(settings.LESSON_EXAM_RATE+settings.PROJECT_EXAM_RATE)
                project_exam_rate = settings.PROJECT_EXAM_RATE/(settings.LESSON_EXAM_RATE+settings.PROJECT_EXAM_RATE)
                score = ls * lesson_exam_rate + ps * project_exam_rate
        else:
            rate = 0
            if exam_status['has_count'] == 1:
                rate = settings.HAS_1_EXAM_RATE
            if exam_status['lesson_has_exam']:
                score += ls * rate
            elif exam_status['course_has_exam']:
                score += cs * rate
            elif exam_status['course_has_project']:
                score += ps * rate
    except Exception as e:
        logger.error(e)
    return int(score)

# 检查coursescore里面是否有对应记录,没有则增加一条rebuild_count为0的数据
def check_course_score(user, course):
    if CourseScore.objects.filter(user=user,course=course).count() == 0:
        course_score = CourseScore()
        course_score.user = user
        course_score.course = course
        course_score.save()

#获取当前用户学力
def current_study_point(careercourse,user):
    ret = {}
    try:
        classobj = ClassStudents.objects.get(user=user, student_class__career_course=careercourse)
        mypoint = classobj.study_point
        ret['classobj'] = classobj
        ret['mypoint'] = mypoint
        return ret
    except ClassStudents.DoesNotExist:
        message = 'NotSignUp' #没有报名
        return message
    except Exception,e:
        logger.error(e)

#当前班级用户的学力排行用户
def all_stu_ranking(careercourse,user):
    ret = current_study_point(careercourse, user)
    if ret =="NotSignUp":
        return "NotSignUp"
    else:
        current_user_class = ret['classobj'].student_class #当前用户所在的班级ID
        curren_all_stu = ClassStudents.objects.filter(student_class__career_course=careercourse,student_class=current_user_class).order_by('-study_point')
        return curren_all_stu

#获取用户当前排名
def current_user_ranking(careercourse,user):
    curren_all_stu = all_stu_ranking(careercourse,user)
    i = 0
    if curren_all_stu =="NotSignUp":
        return "NotSignUp"
    else:
        for stu in curren_all_stu:
            i += 1
            if stu.user.id ==user.id:
                break
    return i

#作业和项目文件上传函数
def file_upload(files, dirname):
    if files.size / 1024 > settings.JOB_SIZE_LIMIT :
        return (False,"文件大小超过"+str(settings.JOB_SIZE_LIMIT)+"KB限制")
    if settings.JOB_SUFFIX_LIMIT.find(files.name.split(".")[-1].lower()) == -1 :
        return (False,"文件必须为ZIP/RAR格式")
    path=os.path.join(settings.MEDIA_ROOT,upload_generation_dir(dirname))
    if not os.path.exists(path): #如果目录不存在创建目录
        os.makedirs(path)
    file_name=str(uuid.uuid1())+"."+str(files.name.split(".")[-1])
    path_file=os.path.join(path,file_name)
    db_file_url = path_file.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    status = open(path_file, 'wb').write(files.file.read())
    return (True,"文件上传成功",db_file_url)

# 判断章节是否有测验题
def lesson_has_exam(lesson_id):
    if Paper.objects.filter(examine_type=2, relation_type=1, relation_id=lesson_id).count() == 0:
        return False
    return True

# 是否有课后作业
def lesson_has_homework(lesson_id):
    if Homework.objects.filter(examine_type=1, relation_type=1, relation_id=lesson_id).count() == 0:
        return False
    return True
############### lps 结束##############################

class paging():
    '''
    此为文章分页功能，需要往里传递三个参数，分别如下：
    res:结果集
    page:页码号，即第几页,这个一般从URL的GET中得到
    pagenum:每页显示多少条记录
    '''
    def __init__(self,res,page,pagenum):
        self.res = res
        self.page = int(page)
        self.pagenum = int(pagenum)
        # tn = self.tablename.objects.all().order_by('-id') #查询tablename表中所有记录数，并以降序的方式对id进行排列
        self.p = Paginator(res,self.pagenum) #对表数据进行分页，每页显示pagenum条
    def pt(self):
        '''共有多少条数据'''
        return self.p.count
    def pn(self):
        '''总页数'''
        return self.p.num_pages
    def pr(self):
        '''获取页码列表'''
        return self.p.page_range
    def pl(self):
        '''第page页的数据列表'''
        return self.p.page(self.page).object_list
    def pp(self):
        '''是否有上一页'''
        return self.p.page(self.page).has_previous()
    def np(self):
        '''是否有下一页'''
        return self.p.page(self.page).has_next()
    def ppn(self):
        '''上一页的页码号'''
        if self.page <= 1: #假如当前页在第一页，那就直接返回1
            return '1'
        else:
            return self.p.page(self.page).previous_page_number()
    def npn(self):
        '''下一页的页码号'''
        if self.p.page(self.page).has_next() == False: #如果当前页不存在下一页，则返回最后一个页码值
            return self.page
        else:
            return self.p.page(self.page).next_page_number()

def instance_pager(obj,curren_page,page_size = 5):
    if not curren_page:
        curren_page = 1
    p = paging(obj,curren_page,page_size) #实例化分页类
    pn = p.pn()  #总页数
    pt = p.pt()  #共有多少条数据
    pl = p.pl()  #第x页的数据列表
    pp = p.pp()  #是否有前一页
    np = p.np()  #是否有后一页
    ppn= p.ppn() #前一页页码
    npn= p.npn() #后一页页码
    cp = int(curren_page) #获取当前页，并转为型形，方便下面进行计算和比较，并且模板文件中也要用到比较
    if cp < 5:   #这里进行判断，假如当前页小于5的时候，
        pr = p.pr()[0:5]    #pr为获取页码列表，即当前页小于5的时候，模板中将显示第1页至第5页，如 1 2 3 4 5
    elif int(pn) - cp < 5:   #假如最后页减当前页小于5时
        pr = p.pr()[int(pn)-5:int(pn)]  #页码列表显示最后5页，如共有30页的话，那显示：26 27 28 29 30
    else:   #其它情况
        pr = p.pr()[cp-3:cp+2]   #其它情况显示当前页的前4条至后4条，如当前在第10页的话，那显示：6 7 8 9 10
    return pn,pt,pl,pp,np,ppn,npn,cp,pr

def sys_send_message(A_id,B_id,action_type,content,action_id=None):
    """
    添加我的消息(站内信)
    @A_id:发送方，为0表示系统用户
    @B_id:接收方，为0就给所有用户发送消息
    @action_type: ('1','系统消息'),('2','课程讨论回复'),('3','论坛讨论回复'),
    @content：消息内容
    """
    if A_id != B_id:
        try:
            msg = MyMessage()
            msg.userA = A_id
            msg.userB = B_id
            msg.action_type = action_type
            if action_id is not None:
                msg.action_id = action_id
            msg.action_content = content
            msg.save()
        except Exception as e:
            logger.error(e)
            return False
    return True

# Add by Steven YU
def app_send_message_token(title,content,token_list,client = "all"):
    '''
    给app客户端推送消息
    :param title: 消息标题
    :param content: 消息内容
    :param account_list: 发送对象，为[]则给所有设备（所有用户）推送
    :param client: 发送客户端类型
    :return: True 成功，False 失败
    '''
    try:
        xg = xinge.XingeApp(settings.XG_ACCESS_ID, settings.XG_SECRET_KEY)

        # ios通知
        if client == "ios" or client == "all":
            msg = xinge.MessageIOS()
            # alert字段可以是字符串或json对象，参见APNS文档
            msg.alert = content
            # 消息为离线设备保存的时间，单位为秒。默认为0，表示只推在线设备
            msg.expireTime = 259200

            for token in token_list:
                xg.PushSingleDevice(token,msg,xinge.XingeApp.ENV_DEV)


        # android 通知
        if client == "android" or client == "all":
            msg = xinge.Message()
            msg.type = xinge.Message.TYPE_NOTIFICATION
            msg.title = title
            msg.content = content
            # 消息为离线设备保存的时间，单位为秒。默认为0，表示只推在线设备
            msg.expireTime = 259200
            msg.style = xinge.Style(2, 1, 0, 0, 0)
            action = xinge.ClickAction()
            action.actionType = xinge.ClickAction.TYPE_ACTIVITY
            action.activity="com.maiziedu.app.PushReceiveActivity"
            msg.action = action
            for token in token_list:
                xg.PushSingleDevice(token, msg,xinge.XingeApp.ENV_DEV)


    except Exception as e:
        print e
        logger.error(e)
        return False
    return True

def app_send_message(title,content,account_list,client = "all"):
    '''
    给app客户端推送消息
    :param title: 消息标题
    :param content: 消息内容
    :param account_list: 发送对象，为[]则给所有设备（所有用户）推送
    :param client: 发送客户端类型
    :return: True 成功，False 失败
    '''
    try:
        xg = xinge.XingeApp(settings.XG_ACCESS_ID, settings.XG_SECRET_KEY)

        # ios通知
        if client == "ios" or client == "all":
            msg = xinge.MessageIOS()
            # alert字段可以是字符串或json对象，参见APNS文档
            msg.alert = content
            # 消息为离线设备保存的时间，单位为秒。默认为0，表示只推在线设备
            msg.expireTime = 259200
            if len(account_list) > 0:
                xg.PushAccountList(0, account_list, msg, xinge.XingeApp.ENV_DEV)
            elif len(account_list) == 0:
                xg.PushAllDevices(0, msg, xinge.XingeApp.ENV_DEV)

        # android 通知
        if client == "android" or client == "all":
            msg = xinge.Message()
            msg.type = xinge.Message.TYPE_NOTIFICATION
            msg.title = title
            msg.content = content
            # 消息为离线设备保存的时间，单位为秒。默认为0，表示只推在线设备
            msg.expireTime = 259200
            msg.style = xinge.Style(2, 1, 0, 0, 0)
            action = xinge.ClickAction()
            action.actionType = 1
            msg.action = action
            if len(account_list) > 0:
                xg.PushAccountList(0, account_list, msg)
            elif len(account_list) == 0:
                xg.PushAllDevices(0, msg)

    except Exception as e:
        print e
        logger.error(e)
        return False
    return True


#app页面
def apppage(request):

    template_vars = cache.get('apppage')
    if not template_vars:
        text_links = Links.objects.filter(is_pic = 0)
        # 首页SEO信息读取
        seo = PageSeoSet()
        try:
            seo = PageSeoSet.objects.get(page_name='2')
        except Exception as e:
            logger.error(e)

        template_vars = {'text_links': text_links, 'seo': seo, 'ANDROID_DOWN_URL': '', 'IOS_DOWN_URL': '',
                         'WINPHONE_DOWN_URL': '', 'IPAD_DOWN_URL': ''}

        cache.set('apppage', template_vars, settings.CACHE_TIME)

    template_vars['ANDROID_DOWN_URL'] = settings.ANDROID_DOWN_URL
    template_vars['IOS_DOWN_URL'] = settings.IOS_DOWN_URL
    template_vars['WINPHONE_DOWN_URL'] = settings.WINPHONE_DOWN_URL
    template_vars['IPAD_DOWN_URL'] = settings.IPAD_DOWN_URL

    return render(request, 'mz_common/app.html', template_vars)

#手机搜索页面
def mobile_search(request):
    user = request.user
    return render(request, 'mz_common/mobile_search.html', locals())

# 重定向到老网站的手机接口
@csrf_exempt
def old_redirect(request):
    # 如果判断是post提交过来的接口，进行单独处理
    new_url = "http://old.maiziedu.com"+request.get_full_path()
    request_data = request.GET
    if request.POST:
        request_data = request.POST
    data = urllib.urlencode(request_data)
    req = urllib2.Request(new_url, data)
    response = urllib2.urlopen(req)
    return HttpResponse(response, content_type="application/json")

def faq(request):
    return render(request, 'mz_common/faq.html', locals())

def activitypage(request):
    return render(request, 'mz_common/activitypage.html', locals())

def def_1017(request):
    return render(request, 'mz_common/1017.html', locals())

def def_1018(request):
    return render(request, 'mz_common/1018.html', locals())

def ios(request):
    return render(request, 'mz_common/ios.html', locals())

def ios8(request):
    return render(request, 'mz_common/ios8.html', locals())

def osc(request):
    return render(request, 'mz_common/osc.html', locals())

def protocol(request):
    return render(request, 'mz_common/protocol.html', locals())

# 获取用户当前某个职业课程下的实际总学力数
def get_study_point(user, career_course):
    # 当前学力总数
    study_point_count = 0
    lesson_list = Lesson.objects.filter(course__stages__career_course=career_course).values_list("id")
    course_list = Course.objects.filter(stages__career_course=career_course).values_list("id")
    # 观看视频获得学力数
    study_point_count += UserLearningLesson.objects.filter(user=user, lesson__in=lesson_list, is_complete=True).count()
    # 课后作业获得学力数
    homework_list = Homework.objects.filter(examine_type=1, relation_type=1, relation_id__in=lesson_list).values_list("id")
    study_point_count += HomeworkRecord.objects.filter(student=user, homework__in=homework_list, rebuild_count=0).count()
    # 随堂测验获得学力数
    paper_list = Paper.objects.filter(examine_type=2,relation_type=1,relation_id__in=lesson_list).values_list("id")
    study_point_count += PaperRecord.objects.filter(student=user, paper__in=paper_list, rebuild_count=0).count()
    # 课程总测验获得学力数
    paper_list = Paper.objects.filter(examine_type=2,relation_type=2,relation_id__in=course_list).values_list("id")
    study_point_count += PaperRecord.objects.filter(student=user, paper__in=paper_list, rebuild_count=0).count() * 10
    # 项目制作获得学力数
    project_list = Project.objects.filter(examine_type=5,relation_type=2,relation_id__in=course_list).values_list("id")
    study_point_count += ProjectRecord.objects.filter(student=user, project__in=project_list, rebuild_count=0).count() * 10
    return study_point_count

# 优惠码验证
def coupon_vlidate(request):
    # careercourse
    careercourse = request.REQUEST.get('careercourse',None)
    result = ""
    request.session['code_sno'] = None
    request.session['money'] = None
    CouponCode = request.REQUEST.get("CouponCode","")
    p = re.compile('^[A-Za-z0-9]+$')
    c = p.match(CouponCode)
    if CouponCode == "":
        result= '{"status":"failure","message":"优惠码不能为空!"}'
    elif len(CouponCode) < 16 or len(CouponCode) > 16 or not(c):
        result='{"status":"failure","message":"优惠码格式不正确!"}'
    elif careercourse is None:
        result='{"status":"failure","message":"请选择职业课程!"}'

    if result!="":
        return HttpResponse(result, content_type="application/json")

    coupon_details = Coupon_Details.objects.filter(Q(code_sno=CouponCode))
    if len(coupon_details) > 0:
        coupon = coupon_details[0]
    else:
        return HttpResponse('{"status":"failure","message":"优惠码不存在!"}', content_type="application/json")

    if coupon.is_use:
        result = '{"status":"failure","message":"优惠码已经被使用!"}'
    elif coupon.is_lock and coupon.user != request.user:
        result = '{"status":"failure","message":"优惠码已被其他用户占用!"}'
    elif not(coupon.careercourse_id is None) and careercourse != coupon.careercourse_id :
        try:
            Course = CareerCourse.objects.get(pk=coupon.careercourse_id)
            result = '{"status":"failure","message":"你已经绑定了'+Course.name+'职业课程!"}'
        except Exception as e:
            result = '{"status":"failure","message":"未知错误!"}'
    else:
        if not(coupon.is_lock) and careercourse is not None:
            coupon.is_lock = True
            coupon.user = request.user
            coupon.use_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            coupon.careercourse_id = careercourse
            coupon.save()
            # print coupon.coupon_id
        money_obj = Coupon.objects.get(id=coupon.coupon_id)
        money = money_obj.coupon_price
        request.session['code_sno'] = coupon.code_sno
        request.session['money'] = money
        result = '{"status":"success","message":"优惠码可以使用！","money":"'+money+'"}'
    return HttpResponse(result, content_type="application/json")

# 首页企业直通班课程
def index_ajax_careercourse_list(request):
    current_page = request.GET.get('page', '1')
    template_vars = cache.get('index_ajax_careercourse_list_'+str(current_page))
    if not template_vars:
        career_course_list = CareerCourse.objects.filter(course_scope=None).order_by("index", "-id")
        lists = {}
        try:
            pagers = paging(career_course_list,int(current_page),13)
            page_data = pagers.pl()
            if len(page_data) < 13 and pagers.pn() != 1:
                num = 13 - len(page_data)
                pagers = paging(career_course_list,1,num)
                p_data = pagers.pl()
                page_data = chain(page_data,p_data) #返回的为一个迭代器
            lists = {
                'data':[{'id':p.id,'imgUrl':str(p.image),'text':p.name,'bgColor':p.course_color,'count':p.student_count} for p in page_data],
                'PageNum':pagers.pn() - 1 # 临时将总页数减去1，后面记得检查总页数计算错误的问题
            }
        except EmptyPage:
            pass

        template_vars = lists

        cache.set('index_ajax_careercourse_list_'+str(current_page), template_vars, settings.CACHE_TIME)

    return HttpResponse(json.dumps(template_vars), content_type="application/json")

# app下载
def app_download(request):
    try:
        file_object = open('/var/www/maiziedu.com/uploads/app/count.txt','r')
        the_count = file_object.read()
        the_count = the_count.split(':')
        file_object.close()
        file_object = open('/var/www/maiziedu.com/uploads/app/count.txt','w')
        file_object.write("The current Downloads:"+str(int(the_count[1])+1))
        file_object.close()
    except Exception as e:
        logger.error(e)

    return HttpResponseRedirect("http://www.maiziedu.com/uploads/app/"+str(settings.NEWEST_ANDROID_APP))

# 手机活动页面咨询统计
@csrf_exempt
def app_consult_info_add(request):
    try:
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        qq = request.POST.get("qq", "").strip()
        interest = request.POST.get("interest", "").strip()
        print request.POST
        app_consult_info = AppConsultInfo()
        app_consult_info.name = name
        app_consult_info.phone = phone
        app_consult_info.qq = qq
        app_consult_info.interest = interest
        app_consult_info.save()
    except Exception as e:
        logger.error(e)
        return HttpResponse('{"status":"failure"}', content_type="application/json")
    return HttpResponse('{"status":"success"}', content_type="application/json")