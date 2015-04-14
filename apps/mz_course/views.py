# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse
from django.conf import settings
from django.db.models import Q
from django.core.cache import cache
from models import *
from mz_pay.models import *
from mz_user.models import *
from mz_lps.models import *
from mz_common.models import *
from mz_common.views import *
import logging
import json
import base64,urllib,urllib2,re

from aca_course.models import *

logger = logging.getLogger('mz_course.views')

#   职业课程（课程）列表视图
def course_list_view(request):
    try:
        current_page = request.GET.get('page', '1')
        template_vars = cache.get('course_list_view_'+current_page)
        if not template_vars:
            career_course_list = CareerCourse.objects.filter(course_scope=None).order_by("index", "-id")
            pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(career_course_list, int(current_page), settings.COURSE_LIST_PAGESIZE)
            # 首页SEO信息读取
            seo = PageSeoSet()
            try:
                seo = PageSeoSet.objects.get(page_name='3')
            except PageSeoSet.DoesNotExist:
                pass

            template_vars = {'seo':seo, 'pl':pl, 'pn':pn, 'pr':pr, 'ppn':ppn, 'npn':npn, 'cp':cp}

            cache.set('course_list_view', template_vars, settings.CACHE_TIME)
    except Exception as e:
        return render(request, 'mz_common/failure.html', {'reason': '该页没有数据'})
    return render(request, 'mz_course/course_list.html', template_vars)

def course_list_view_ajax(request):
    json_str = []
    try:
        career_course_list = CareerCourse.objects.all().order_by("index", "-id")
        current_page = int(request.GET.get('page', '1'))
        pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(career_course_list,current_page, settings.COURSE_LIST_PAGESIZE)
    except Exception, e:
        return HttpResponse(json.dumps({'result':'None'}),content_type="application/json")
    json_str = [{"course_color":p.course_color,"id":p.id,"image":str(p.image),"name":p.name.strip(),"student_count":p.student_count} for p in pl ]
    return HttpResponse(json.dumps(json_str),content_type="application/json")

#   职业课程详细视图
def course_view(request, course_id, university_id = 0):
    request.session['code_sno'] = None
    request.session['money'] = None
    #这段代码 以后要去掉和404页面函数的代码
    android = [4155 ,4121 ,3995 ,3875 ,3221 ,3391 ,3469 ,3300 ,3244 ,318 ,2703 ,1067 ,1056 ,297 ,1010 ,1009 ,1476 ,1417 ,258 ,919 ,876 ,471 ,220 ,833 ,756 ,450 ,175 ,1237 ,1216 ,421 ,1162 ,723 ,1132 ,2539 ,138 ,658 ,627 ,755 ,516 ,494 ,153 ,164 ,108 ,590 ,1097 ,1075 ,628 ,451 ,350]
    ios = [4005,3838,176]
    wp = [3978,3929,3887,3795,470,317,626,296,457,918,256,207,430,724,417,340,106]
    co2d = [2438,2429,2324,2334,722,2388,2406,2473,2450,548,257,2212,2175]
    other = [4009,2494,1293,1695,1629,1542,1541,1540,1868,1866,1830,1696,1364,2558,2607,4105,4089,4071,4009,3856,3617,3816,3491,3225,3420,2663]
    path_url =  request.path
    arr_path =  path_url.split('/')
    list_2 =[i for i in arr_path if i!='' ]
    arr_len =  len(list_2)
    if arr_len == 2:
        CourseType = list_2[0]
        CourseNum = list_2[1]
        if CourseType=="course":
            if int(CourseNum) in android:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/2/")
            elif int(CourseNum) in ios:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/3/")
            elif int(CourseNum) in wp:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/8/")
            elif int(CourseNum) in co2d:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/7/")
            elif int(CourseNum) in other:
                return HttpResponsePermanentRedirect("http://www.maiziedu.com/course/")

    cur_university = None
    course_scope = 0
    cur_careercourse = None
    template_vars = cache.get('course_view_'+str(course_id)+'_'+str(university_id)+'_'+str(request.user.is_authenticated()))
    if not template_vars:
        try:
            if university_id:
                cur_university=AcademicOrg.objects.get(pk=university_id)
                course_scope=1
        except Exception as e:
            logger.error(e)

        # 根据职业课程ID查询对应阶段和课程的详细列表
        try:
            cur_careercourse = CareerCourse.objects.get(pk=course_id)
            stages = cur_careercourse.stage_set.order_by("index")

            for stage in stages:
                setattr(stage, "course_list", [])
                stage.course_list = stage.course_set.filter(is_active=True).order_by("index", "id")
                if not request.user.is_authenticated():
                    for course in stage.course_list:
                        setattr(course, "url", "")
                        #如果没有播放章节的记录，直接获取该课程下第一个章节进行播放
                        lesson_list = Lesson.objects.filter(course=course.id).order_by("index")
                        if len(lesson_list) > 0:
                            course.url = "/lesson/"+str(lesson_list[0].id)
                        else:
                            course.url = "/course/"+str(course.id)+"/recent/play/"

            # 获取完成职业课程学习所需天数
            setattr(cur_careercourse, "need_days", 0)
            for stage in stages:
                sum_days = stage.course_set.extra(select={'sum': 'sum(need_days)'}).values('sum')[0]['sum']
                if sum_days is not None:
                    cur_careercourse.need_days += sum_days

            # 获取该职业课程下所有开放的班级
            cur_careercourse_class_list = cur_careercourse.class_set.filter(is_active=True, status=1)
        except Exception as e:
            logger.error(e)

        template_vars = {'course_scope':course_scope, 'cur_university':cur_university, 'cur_careercourse':cur_careercourse,
                         'stages':stages, 'cur_careercourse_class_list':cur_careercourse_class_list}
        cache.set('course_view_'+str(course_id)+'_'+str(university_id)+'_'+str(request.user.is_authenticated()), template_vars, settings.CACHE_TIME)

    try:
        if cur_careercourse is None:
            cur_careercourse = template_vars['cur_careercourse']

        # 更新职业课程的点击次数
        cur_careercourse.click_count += 1
        cur_careercourse.save()

        # 根据不同情况获取不同的支付金额
        cur_careercourse = get_real_amount(request.user, cur_careercourse)
    except Exception as e:
        logger.error(e)

    template_vars['cur_careercourse'] = cur_careercourse

    return render(request, 'mz_course/course_detail.html', template_vars)

# 根据课程ID查询当前应该播放的章节
def course_recent_play(request, course_id):
    # 更新课程的点击次数
    try:
        course = Course.objects.get(pk=course_id)
        course.click_count += 1
        course.save()
    except Exception, e:
        logger.error(e)

    #查询当前应该播放的章节(获取最近一次播放的章节)
    if request.user.is_authenticated():
        recent_learned_lesson = get_recent_learned_lesson(request.user, course_id)
        if recent_learned_lesson is not None:
            #跳转到最近播放的章节播放
            return HttpResponsePermanentRedirect(reverse('lesson:lesson_view', kwargs={"lesson_id": recent_learned_lesson.lesson.id}))
    #如果没有播放章节的记录，直接获取该课程下第一个章节进行播放
    lesson_list = Lesson.objects.filter(course=course_id).order_by("index")
    if len(lesson_list) == 0:
        return render(request, 'mz_common/failure.html',{'reason':'该课程下还没有章节'})
    return HttpResponsePermanentRedirect(reverse('lesson:lesson_view', kwargs={"lesson_id": lesson_list[0].id}))

#   章节视图
def lesson_view(request, lesson_id):
    cur_lesson = None
    cur_course = None
    cur_careercourse = None
    uncomplete_quiz_list = []  # 获取测验题列表
    cur_careercourse_class_list = [] #该职业课程的班级列表

    try:
        cur_lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'没有该章节'})

    # 更新播放次数
    cur_lesson.play_count += 1
    cur_lesson.save()

    cur_course = cur_lesson.course
    if cur_lesson.course.stages is not None:
        cur_careercourse = cur_lesson.course.stages.career_course

    template_vars = cache.get('lesson_view_'+str(lesson_id))
    if not template_vars:
        lesson_list = cur_course.lesson_set.order_by("index", "id")

        # 去掉当前章节视频URL地址的空格
        cur_lesson.video_url = cur_lesson.video_url.strip()

        # 课件下载
        lesson_resourse_list = cur_lesson.lessonresource_set.all()

        # 视频完成多少提示考试
        VIDEO_EXAM_COMPLETE = settings.VIDEO_EXAM_COMPLETE

        if cur_careercourse is not None:
            # 获取该职业课程下所有开放的班级
            cur_careercourse_class_list = cur_careercourse.class_set.filter(is_active=True, status=1)

        # 获取章节作业描述需求
        setattr(cur_lesson, "homework", {"description": "", "upload_file": ""})
        try:
            homework = Homework.objects.get(relation_id=lesson_id,relation_type = 1,examine_type = 1)
            cur_lesson.homework["description"] =  homework.description
            if request.user.is_authenticated():
                homework_record = HomeworkRecord.objects.filter(examine = homework,student= request.user)
                if len(homework_record) > 0:
                    cur_lesson.homework["upload_file"] = homework_record[0].upload_file
                else:
                    cur_lesson.homework["upload_file"] = ""
        except Homework.DoesNotExist:
            homework = Homework()
            homework.examine_type = 1
            homework.relation_type = 1
            homework.relation_id = lesson_id
            homework.description = settings.DEFAULT_HOMEWORK
            homework.save()
            cur_lesson.homework["description"] =  settings.DEFAULT_HOMEWORK

        search_keywords = cur_course.search_keywords.all()
        search_keywords_plain = []
        for keyword in search_keywords:
            search_keywords_plain.append(keyword.name)
        search_keywords_string = ','.join(search_keywords_plain)
        bbs_url = settings.BBS_SITE_URL

        #拉勾网接口(相关招聘信息读取)
        lagou = []
        web_url = ""
        try:
            # 职业课程是否包含相关关键词
            if cur_careercourse.name.upper().find("产品".upper()) > -1:
                web_url = settings.LAGOU_PRODUCT_MANAGER_API
            elif cur_careercourse.name.upper().find("ios".upper()) > -1:
                web_url = settings.LAGOU_IOS_API
            elif cur_careercourse.name.upper().find("android".upper()) > -1:
                web_url = settings.LAGOU_ANDROID_API
            elif cur_careercourse.name.upper().find("物联".upper()) > -1:
                web_url = settings.LAGOU_JOINT_PAI
            elif cur_careercourse.name.upper().find("嵌入式".upper()) > -1:
                web_url = settings.LAGOU_EMBEDDED_PAI
            elif cur_careercourse.name.upper().find("windowsphone".upper()) > -1:
                web_url = settings.LAGOU_WINPHONE_API
            elif cur_careercourse.name.upper().find("cocos2d".upper()) > -1:
                web_url = settings.LAGOU_COCOS2D_API
            elif cur_careercourse.name.upper().find("web".upper()) > -1:
                web_url = settings.LAGOU_WEB_API
            response = urllib2.urlopen(web_url, timeout=3)
            json_read = response.read()
            matchObj = re.match('success_jsonpCallback\(([\s\S]+)\)$',json_read)
            if matchObj:
                lagou_json = matchObj.group(1)
                lagou = json.loads(lagou_json)
        except Exception as e:
            pass

        template_vars = {'cur_lesson':cur_lesson, 'cur_course':cur_course, 'cur_careercourse':cur_careercourse, 'lesson_list':lesson_list,
                         'search_keywords_string':search_keywords_string, 'lagou':lagou, 'lesson_resourse_list':lesson_resourse_list, 'VIDEO_EXAM_COMPLETE':VIDEO_EXAM_COMPLETE,
                         'cur_careercourse_class_list':cur_careercourse_class_list, 'uncomplete_quiz_list':[]}

        cache.set('lesson_view_'+str(lesson_id), template_vars, settings.CACHE_TIME)

    if cur_careercourse is not None:
        # 根据不同情况获取不同的支付金额
        cur_careercourse = get_real_amount(request.user, cur_careercourse)

    #给course增加收藏信息
    setattr(cur_course, "is_favorite", False)
    #检查该用户是否购买了该课程对应的职业课程所属的阶段
    if request.user.is_authenticated():
        user = request.user

        # 播放时课程是否加入到用户的课程列表
        add_into_mycourse(user, cur_course, cur_careercourse)
        # 播放时检查coursescore是否有用户和课程对应的记录
        check_course_score(user, cur_course)
        # 根据lessonid找到对应的paper
        paper = Paper.objects.filter(examine_type=2, relation_type=1, relation_id=lesson_id)
        if len(paper) > 0:
            # 获取重修次数
            rebuild_count = get_rebuild_count(user, cur_course)
            uncomplete_quiz_list = get_uncomplete_quiz(user, paper[0], rebuild_count)
        #判断用户是否已经解锁过该章节对应的阶段，已经解锁则不需要弹出支付提示框
        unlock_count = 0
        if cur_careercourse is not None:
            unlock_count = UserUnlockStage.objects.filter(Q(user=user), Q(stage=cur_course.stages)).count()
        if unlock_count > 0:
            cur_lesson.is_popup = False

        #查询是否收藏该课程
        if user.myfavorite.filter(id=cur_course.id).count() > 0:
            cur_course.is_favorite = True

        # 更新当前观看章节（如果已经有记录只更新观看时间）
        user_learning_lesson = UserLearningLesson()
        try:
            user_learning_lesson = UserLearningLesson.objects.get(user=user, lesson=lesson_id)
        except UserLearningLesson.DoesNotExist :
            user_learning_lesson.lesson = cur_lesson
            user_learning_lesson.user = user
        user_learning_lesson.save()

    # 将一些更新后的参数存入到template_vars
    template_vars['cur_careercourse'] = cur_careercourse
    template_vars['cur_course'] = cur_course
    template_vars['cur_lesson'] = cur_lesson
    template_vars['uncomplete_quiz_list'] = uncomplete_quiz_list

    return render(request,'mz_course/lesson_view.html', template_vars)

def update_favorite(request, course_id):
    if request.user.is_authenticated() :
        favorite = MyFavorite()
        course = Course()
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            result = '{"status":"failure","message":"不存在该课程"}'
        try:
            favorite = MyFavorite.objects.get(user=request.user, course=course_id)
            favorite.delete()
            # 收藏数减1
            course.favorite_count -= 1
            course.save()
            result = '{"status":"success","message":"取消收藏成功"}'
        except MyFavorite.DoesNotExist :
            favorite.user = request.user
            favorite.course_id = course_id
            favorite.save()
            # 收藏数加1
            course.favorite_count += 1
            course.save()
            result = '{"status":"success","message":"收藏成功"}'
        except Exception as e:
            logger.error(e)
    else:
        result = '{"status":"failure","message":"请登录之后再收藏"}'
    return HttpResponse(result, content_type="application/json")

#评论函数
@csrf_exempt
def add_comment(request):
    if request.POST['comment']=="":
        message = '{"message":"评论不能为空"}'
        return HttpResponse(message,content_type="application/json")
    comment = request.POST['comment']
    parent_id = request.POST['parent_id'] or None
    lesson_id = request.POST['lesson_id']
    child_uid = request.POST['child_uid'] or None
    user = request.user
    dis = Discuss()
    dis.content = comment
    dis.parent_id = parent_id
    dis.lesson_id = lesson_id
    dis.user_id = user.id
    pid = dis.save()
    new_id = Discuss.objects.order_by('-id')[0]
    if child_uid is not None and int(user.id) != int(child_uid):
        sys_send_message(user.id,child_uid,2,comment,lesson_id) #添加消息函数

        # app推送
        try:
            child_user = UserProfile.objects.get(pk=child_uid)
            lesson = Lesson.objects.get(pk=lesson_id)
            #app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [child_user.username])

            app_send_message_token("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [child_user.token])
        except Exception as e:
            logger.error(e)

    # 如果子回复为None则表示给录课老师的留言
    if child_uid is None:
        try:
            lesson = Lesson.objects.get(pk=lesson_id)
            # 录课老师对象
            teacher = lesson.course.teacher
            sys_send_message(user.id,teacher.id,2,comment,lesson_id) #添加消息函数
            app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [teacher.token])
            # 带课老师对象
            teachers = UserProfile.objects.filter(
                id__in=Class.objects.filter(career_course=lesson.course.stages.career_course).values("teacher").distinct())
            for class_teacher in teachers:
                if teacher.id != class_teacher.id:
                    sys_send_message(user.id,class_teacher.id,2,comment,lesson_id) #添加消息函数
                    app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [class_teacher.token])
        except Exception as e:
            logger.error(e)
    message = '{"message":"success","parent_id":"'+str(new_id.id)+'"}'
    return HttpResponse(message,content_type="application/json")

#作业提交
@csrf_exempt
def job_upload(request):
    ret="0"
    files = request.FILES.get("Filedata",None)
    lesson_id = request.POST['lesson_id']
    if files:
        result =file_upload(files, 'homework')
        if result[0] == True:
            ret='{"status":"success","message":"'+str(result[1])+'"}'
            try:
                examine = Homework.objects.get(Q(relation_type=1), Q(relation_id=lesson_id),Q(examine_type = 1))
                workobj = HomeworkRecord.objects.filter(examine_id = examine.id,student_id= request.user.id)
                if workobj:
                    project_record_path = os.path.join(settings.MEDIA_ROOT)+"/"+str(workobj[0].upload_file)
                    if os.path.exists(project_record_path) : #如果存在就移除
                        os.remove(project_record_path)
                    # 如果已经上传，就执行更新操作
                    HomeworkRecord.objects.filter(examine_id=examine.id).update(upload_file=result[2])
                else:
                    work = HomeworkRecord()
                    work.upload_file = result[2]
                    work.student = request.user
                    work.examine_id = examine.id
                    work.homework = examine
                    work.save()
                    # 首次上传时加上1学力
                    update_study_point_score(request.user, 1, examine=examine, examine_record=work)
            except Homework.DoesNotExist:
                ret='{"status":"failure","message":"保存失败"}'
                return HttpResponse(ret, content_type="text/plain")
        else:
            ret='{"status":"failure","message":"'+str(result[1])+'"}'
    return HttpResponse(ret, content_type="text/plain")

# #判断是否上传
# def is_up(exaid,user_id):
#     workobj = HomeworkRecord.objects.filter(examine_id = exaid,student_id= user_id)
#     if workobj.exists():
#         return True
#     else:
#         return False

# #模板判断是否上传,传值到模板
# def template_is_up(request,lesson_id):
#     bools = 0
#     try:
#         examine = Homework.objects.get(Q(relation_type=1), Q(relation_id=lesson_id))
#         if is_up(examine.id):
#             bools = 1
#         else:
#             bools = 0
#     except:
#         return HttpResponse(bools)
#     return HttpResponse(bools)

# 课程（隐藏）额外购买渠道
def course_pay_other(request, careercourse_id):

    if not request.user.is_authenticated():
        return render(request, 'mz_common/failure.html',{'reason': '请先回首页登录后再访问该页面'})

    cur_careercourse = None    # 职业课程
    cur_careercourse_stage_list = []    # 职业课程下所属阶段
    user_careercourse_unlockstage_list = []    # 用户职业课程中已经解锁的阶段

    # 获取职业课程下所有的阶段
    try:
        cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
    except CareerCourse.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'没有该职业课程'})
    cur_careercourse_stage_list_temp = cur_careercourse.stage_set.all().order_by("index", "id")
    user_careercourse_unlockstage_list = UserUnlockStage.objects.filter(user=request.user, stage__career_course=careercourse_id)
    for stage in cur_careercourse_stage_list_temp:
        # 给stage增加一个标记，标记该阶段是否已经解锁
        setattr(stage, "is_unlock", False)
        for unlockstage in user_careercourse_unlockstage_list:
            if stage.id == unlockstage.stage.id:
                stage.is_unlock = True
                break
        cur_careercourse_stage_list.append(stage)

    # 如果已经购买过该职业课程的阶段，则获取之前购买选择的班级
    cur_careercourse_class_list=[]
    setattr(cur_careercourse, "careercourse_class", None)
    if len(user_careercourse_unlockstage_list) != 0:
        cur_careercourse.careercourse_class = get_careercourse_class(request.user, cur_careercourse)
    else:
        # 获取该职业课程下所有开放的班级
        cur_careercourse_class_list = cur_careercourse.class_set.filter(is_active=True, status=1)

    return render(request, 'mz_course/careercourse_pay_other.html', locals())

# 更新章节完成状态
def update_learning_lesson(request, lesson_id):
    try:
        if request.user.is_authenticated():
            learning_lesson = UserLearningLesson.objects.get(user=request.user, lesson=lesson_id)
            if not learning_lesson.is_complete:
                learning_lesson.is_complete = True
                learning_lesson.save()
                # 更新学力
                update_study_point_score(student=request.user, study_point=1, course=learning_lesson.lesson.course, rebuild_count=0)
    except Exception, e:
        logger.error(e)
        return HttpResponse({"status": "failure"}, content_type="application/json")
    return HttpResponse({"status": "success"}, content_type="application/json")


# 获取职业课程价格
def get_careercourse_total_price(careercourse):
    price = 0
    if careercourse.stage_set.all().count() > 0:
        price = careercourse.stage_set.extra(select={'sum': 'sum(price)'}).values('sum')[0]['sum'] * careercourse.discount
        if price is None:price = 0
    return int(price)

# 获取职业课程列表所有阶段ID列表
def get_careercourse_allstage_list(careercourse):
    return careercourse.stage_set.all().order_by("index", "id").values_list("id")

# 获取职业课程首付金额
def get_careercourse_first_payment(careercourse):
    price = careercourse.stage_set.filter(is_try=True).extra(select={'sum': 'sum(price)'}).values('sum')[0]['sum']
    if price == None:price =0
    return int(price)

# 获取试学阶段ID列表
def get_careercourse_trystage_list(careercourse):
    return careercourse.stage_set.filter(is_try=True).order_by("index","id").values_list("id")

# 获取还未支付阶段的余款
def get_careercourse_balance_payment(user, careercourse):
    user_careercourse_unlockstage_list = UserUnlockStage.objects.filter(user=user, stage__career_course=careercourse).values_list("stage")
    price = careercourse.stage_set.filter(~Q(id__in=user_careercourse_unlockstage_list)).extra(select={'sum': 'sum(price)'}).values('sum')[0]['sum']
    if price == None:price =0
    return int(price)

# 获取还未支付加锁的阶段ID列表
def get_careercourse_lockstage_list(user, careercourse):
    user_careercourse_unlockstage_list = UserUnlockStage.objects.filter(user=user, stage__career_course=careercourse).values_list("stage")
    return careercourse.stage_set.filter(~Q(id__in=user_careercourse_unlockstage_list)).values_list("id")

# 根据阶段解锁状态来判断课程购买按钮的状态(0显示全款支付和试学首付,1显示尾款支付按钮，2显示已经购买)
def get_careercourse_buybtn_status(user, careercourse):
    careercourse_stage_count = careercourse.stage_set.extra(select={'count': 'count(name)'}).values('count')[0]['count']
    user_careercourse_unlockstage_count = UserUnlockStage.objects.filter(user=user, stage__career_course=careercourse).count()
    if user_careercourse_unlockstage_count == 0:
        return 0
    elif careercourse_stage_count > user_careercourse_unlockstage_count :
        return 1
    else :
        return 2

# 根据用户和职业课程找到用户在职业课程中所属班级编号，
def get_careercourse_class(user, careercourse):
    try:
        userclass = Class.objects.get(students=user, career_course=careercourse)
        return userclass.coding
    except Exception, e:
        logger.error(e)
        return None

# 根据用户、职业课程来判断目标支付阶段列表中是否有已经解锁的阶段
def is_unlock_in_stagelist(user, target_stage_list) :
    if UserUnlockStage.objects.filter(user=user, stage__in=target_stage_list).count() > 0 :
        return True
    return False

# 判断不同情况下支付的实际金额
def get_real_amount(user, careercourse):
    # 根据课程阶段价格计算课程总价
    setattr(careercourse, "total_price", get_careercourse_total_price(careercourse))
    # 获取首付款价格
    setattr(careercourse, "first_payment", get_careercourse_first_payment(careercourse))
    # 获取首付试学的阶段列表
    setattr(careercourse, "trystage_list", get_careercourse_trystage_list(careercourse))
    if user.is_authenticated():
        # 课程购买按钮的状态
        setattr(careercourse, "buybtn_status", get_careercourse_buybtn_status(user, careercourse))
        if careercourse.buybtn_status == 1:
            #计算尾款应支付金额
            setattr(careercourse, "balance_payment", get_careercourse_balance_payment(user, careercourse))
            #用户当前所属该职业课程下的某个班级
            setattr(careercourse, "careercourse_class", get_careercourse_class(user, careercourse))
    return careercourse

# 播放时课程是否加入到用户的课程列表
def add_into_mycourse(user, cur_course, cur_careercourse):
    # 判断该课程是否属于某个职业课程
    if user.is_student():
        if cur_course.stages == None:  #不属于某个职业课程
            # 判断该课程是否已经在该用户的课程列表
            if MyCourse.objects.filter(user=user, course=cur_course.id, course_type=1).count() == 0 :
                my_course = MyCourse()
                my_course.user = user
                my_course.course = cur_course.id
                my_course.course_type = 1
                my_course.save()
                #更新相应小课程的学习人数
                cur_course.student_count += 1
                cur_course.save()
        else:  #属于某个职业课程
            if MyCourse.objects.filter(user=user, course=cur_careercourse.id, course_type=2).count() == 0 :
                my_course = MyCourse()
                my_course.user = user
                my_course.course = cur_careercourse.id
                my_course.course_type = 2
                my_course.save()
                #更新职业课程的学习人数
                cur_careercourse.student_count += 1
                cur_careercourse.save()
                #更新相应小课程的学习人数
                cur_course.student_count += 1
                cur_course.save()


# 得到用户最近观看的章节
def get_recent_learned_lesson(user, course):
    recent_learned_lesson = UserLearningLesson.objects.filter(user=user,lesson__course=course).order_by("-date_learning")
    if recent_learned_lesson:
        return recent_learned_lesson[0]
    return None

# ajax分页评论函数
def lesson_comment(request):
    lesson_id = request.GET.get('lessonid')
    page = request.GET.get('page','1')
    child_comment=[]
    cur_lesson = None
    try:
        cur_lesson = Lesson.objects.get(pk=lesson_id)
    except Lesson.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'没有该章节'})
    # if cur_lesson.course.stages != None:
    discuss_list = cur_lesson.discuss_set.filter(parent_id__isnull=True).order_by("-date_publish") #获取到所有父级评论
    try:
        com_pn,com_pt,discuss_list,com_pp,com_np,com_ppn,com_npn,com_cp,pr = instance_pager(discuss_list,int(page),settings.COMMENT_PAGESIZE)
        for c in discuss_list:
            child = cur_lesson.discuss_set.filter(parent_id = c.id)
            child_comment.append(child)
        return render(request,'mz_course/lesson_view_comm_foreach.html', locals())
    except Exception,e:
        ret = ""
        return HttpResponse(ret)


#老师（他的课程）
def has_course(request,has_id):
    page = request.GET.get('page', '1')
    template_vars = cache.get('has_course_'+str(has_id)+'_'+str(page))
    if not template_vars:
        hascourese = Course.objects.filter(teacher_id = has_id)
        pn,pt,courses,pp,np,ppn,npn,cp,pr = instance_pager(hascourese,int(page),settings.GLOBAL_PAGESIZE)
        try:
            has = UserProfile.objects.get(pk =has_id )
        except Exception as e:
            pass

        template_vars = {'has': has, 'courses': courses, 'pn': pn, 'pr': pr, 'ppn': ppn, 'npn': npn, 'cp': cp}

        cache.set('has_course_'+str(has_id)+'_'+str(page), template_vars, settings.CACHE_TIME)

    return render(request, 'mz_course/user_has_course.html', template_vars)
