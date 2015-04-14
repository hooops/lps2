# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from mz_user.models import *
from mz_lps.models import *
from mz_course.models import *
from mz_course.views import *
from mz_common.models import *
from mz_common.views import *
from mz_pay.models import *
from utils.alipay import params_filter
from mz_pay.views import order_handle
import django.contrib.auth as auth
from django.core.validators import validate_email
from mz_user.views import common_register, do_send_mail, sync_avatar
from django.core.exceptions import ValidationError
from utils.tool import generate_random, upload_generation_dir, generation_order_no
import re, hashlib, requests
import logging, json
from utils.yunpian import tpl_send_sms
import base64
from django.contrib.auth.hashers import make_password
from PIL import Image, ImageFile
from django.db.models import Count

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA

logger = logging.getLogger('mz_service.views')

# common

# 消息异常类
class APIException(Exception):
    pass

# 消息类
class Response:
    message = "数据加载失败"
    success = False
    data = {}

    @staticmethod
    def dumps():
        return json.dumps({
            "message": Response.message,
            "success": Response.success,
            "data": Response.data
        })

# 定义Service的初始化消息的装饰器
def response_init(func):
    def _init(request):
        Response.message = "加载数据时出了一点错哦，请稍后重试吧"
        Response.success = False
        Response.data = {}

        #版本屏蔽
        client = request.REQUEST.get('client','')
        vno = request.REQUEST.get('vno','')
        full_path =  request.get_full_path()
        keyword = request.REQUEST.get('keyword','')
        path_arr = full_path.split('/')
        interface = path_arr[2]

        if (client == 'ios' and vno.find(settings.IOSVERSION) > -1 ) or (client == 'ipad' and vno.find(settings.IPADVERSION) > -1) :

            if interface == 'getExcellentCourse':
                json_obj = {"list": [{"course_id": "341","img_url": "http://www.maiziedu.com/uploads/course/2015/02/001.jpg","student_count": "37","course_name": "架构师的成长的十个步骤"},{"course_id": "331","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Mysql基础.jpg","student_count": "3","course_name": "Mysql基础"},{"course_id": "328","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Web前端开发之Ajax初步.jpg","student_count": "17","course_name": "ajax入门"},{"course_id": "327","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Web前端开发之jQuery入门课程.jpg","student_count": "13","course_name": "Jquery入门"},{"course_id": "326","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Web前端开发之Javascript初步.jpg","student_count": "13","course_name": "Javascript初步"},{"course_id": "325","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Web前端开发之HTML5CSS3快速入门.jpg","student_count": "61","course_name": "Html5+css3"},{"course_id": "317","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Yii框架入门.jpg","student_count": "43","course_name": "yii框架入门"},{"course_id": "316","img_url": "http://www.maiziedu.com/uploads/course/2015/02/Php语言编程基础_uE1hiOz.jpg","student_count": "31","course_name": "Php语言编程基础"},{"course_id": "307","img_url": "http://www.maiziedu.com/uploads/course/2015/01/django基础.jpg","student_count": "63","course_name": "django基础"},{"course_id": "306","img_url": "http://www.maiziedu.com/uploads/course/2015/01/Mysql基础.jpg","student_count": "1","course_name": "Mysql基础"},{"course_id": "305","img_url": "http://www.maiziedu.com/uploads/course/2015/01/Web前端开发之Ajax初步.jpg","student_count": "37","course_name": "ajax入门"},{"course_id": "303","img_url": "http://www.maiziedu.com/uploads/course/2015/01/Web前端开发之jQuery入门课程.jpg","student_count": "20","course_name": "jquery入门"},{"course_id": "302","img_url": "http://www.maiziedu.com/uploads/course/2015/01/Web前端开发之Javascript初步.jpg","student_count": "36","course_name": "javascript初步"},{"course_id": "301","img_url": "http://www.maiziedu.com/uploads/course/2015/01/Web前端开发之HTML5CSS3快速入门.jpg","student_count": "187","course_name": "html5+css3"},{"course_id": "296","img_url": "http://www.maiziedu.com/uploads/course/2015/01/建筑原画绘制-拷贝-3.jpg","student_count": "27","course_name": "建筑原画绘制"}],"ad": [{"url": "http://www.maiziedu.com/uploads/ad/2015/02/APPbanner1.jpg","target_id": "6","ad_type": "1","name": "产品经理"},{"url": "http://www.maiziedu.com/uploads/ad/2015/02/APPbanner3.jpg","target_id": "13","ad_type": "1","name": "Python Web开发"},{"url": "http://www.maiziedu.com/uploads/ad/2015/02/APPbanner2.jpg","target_id": "12","ad_type": "1","name": "游戏原画设计"}]}
                Response.data = json_obj
            elif interface == 'getCareerCourse':
                json_obj = {"list": [{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/IOS.jpg","name": "iOS应用开发","career_id": "3"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/cocos2d-x.jpg","name": "Cocos2d-x手游开发","career_id": "7"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/游戏原画.jpg","name": "游戏原画设计","career_id": "12"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/python.jpg","name": "Python Web开发","career_id": "13"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/html.jpg","name": "Web前端开发","career_id": "9"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/嵌入式应用.jpg","name": "嵌入式应用开发","career_id": "5"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/产品经理.jpg","name": "产品经理","career_id": "6"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/cocos2d.jpg","name": "Cocos2d手游开发","career_id": "10"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/嵌入式驱动.jpg","name": "嵌入式驱动开发","career_id": "1"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/物联网.jpg","name": "物联网开发","career_id": "4"},{"img_url": "http://www.maiziedu.com/uploads/course/2015/02/php.jpg","name": "PHP Web开发","career_id": "14"}]}
                Response.data = json_obj
            elif interface == 'getHotSearch':
                json_obj = {"list": [{"name": "物联网"},{"name": "cocos2d"},{"name": "嵌入式"}]}
                Response.data = json_obj
            elif interface == 'getTeacherList':
                json_obj = {"list": [{
                                         "teacher_id": "4",
                                         "job": "嵌入式专业负责人",
                                         "desc": "7年嵌入式开发工程经验，专注于嵌入式linux应用及内核，驱动的开发和研究工作，曾支持开发多个大型嵌入式及物联网项目。\r\n",
                                         "avatar": "http://www.maiziedu.com/uploads/avatar/2014/12/王老师_HjugzF9.jpg",
                                         "name": "Rocky"
                                     },{
                                    "teacher_id": "46",
                                    "job": "",
                                    "desc": "去哪儿网用户体验总监，前百度产品经理。",
                                    "avatar": "http://www.maiziedu.com/uploads/avatar/2015/02/big_itMVzFd.jpg",
                                    "name": "黄喆"
                                },{
                                    "teacher_id": "81",
                                    "job": "",
                                    "desc": "成都梦拓科技有限公司CEO，国内手机领域的先驱者和布道者，资深开发工程师，在手机应用开发方面有丰富的实战经验。",
                                    "avatar": "http://www.maiziedu.com/uploads/avatar/2014/12/杨丰盛.jpg",
                                    "name": "杨丰盛"
                                }]}
                Response.data = json_obj
            elif interface == 'search':
                android = 'androidANDROIDAndroid安卓'
                wp = 'windowsphoneWINDOWPHONEWinphonewinphone'
                if android.find(keyword) > -1 or wp.find(keyword) > -1:
                    Response.message = "搜索成功"
                    Response.data = {}
                else:
                    return func(request)
            elif interface == 'getTeacherDetail':
                teacherId = request.REQUEST.get('teacherId', None)
                if teacherId == '5':
                    json_obj = {
                        "course_list": [
                            {
                                "course_id": "39",
                                "img_url": "http://www.maiziedu.com/uploads/course/2014/11/10iOS-App打包及发布到Appstore.jpg",
                                "student_count": "0",
                                "course_name": "iOS App打包及发布到Appstore",
                                "updating": 1
                            },
                            {
                                "course_id": "47",
                                "img_url": "http://www.maiziedu.com/uploads/course/2014/11/141iOS8开发新特性-AppExtensions.jpg",
                                "student_count": "0",
                                "course_name": "iOS8开发新特性-AppExtensions",
                                "updating": 1
                            },
                            {
                                "course_id": "346",
                                "img_url": "http://www.maiziedu.com/uploads/course/2015/03/QQ图片20150305103954_zMFi7Lw.jpg",
                                "student_count": "37",
                                "course_name": "IOS多点触控与手势识别",
                                "updating": 0
                            }
                        ]
                    }
                    Response.data = json_obj
                else:
                    return func(request)
            else:
                return func(request)
            Response.message = "数据加载成功"
            Response.success = True
            return HttpResponse(Response.dumps(), content_type="application/json")
        return func(request)
    return _init

# 根据UUID和userId验证请求合法性
def checkUser(request, role):
    '''
    检验权限并获取对应的用户
    :param request:
    :param role: student 是否是学生，teacher 是否是老师, all 只要登录就返回
    :return:权限验证失败则返回错误的具体信息，验证成功则返回对应的用户对象
    '''
    try:
        UUID = request.REQUEST.get("UUID", None)
        userId = request.REQUEST.get("userId", None)
        user = UserProfile.objects.get(uuid=UUID, id=userId)
        if role == "all" or (role == "student" and user.is_student()) or (role == "teacher" and user.is_teacher()):
            return user

    except Exception as e:
        logger.error(e)
    raise APIException('权限验证失败')

# app service api

# 精彩课程
@csrf_exempt
@response_init
def getExcellentCourse(request):
    orderBy = request.REQUEST.get('orderBy','1')
    page = request.REQUEST.get('page','1')
    pageSize = request.REQUEST.get('pageSize','10')
    loadAd = request.REQUEST.get('loadAd', '0')
    template_vars = cache.get('getExcellentCourse_'+str(orderBy)+'_'+str(page)+'_'+str(pageSize)+'_'+str(loadAd))
    if not template_vars:
        ad = []
        courses = []
        if loadAd == '1':
            ad = AppAd.objects.all()
        if orderBy == '1':
            courses = Course.objects.filter(Q(is_click=True), Q(is_homeshow=True)).order_by('-date_publish')
        elif orderBy == '2':
            lesson_group=Lesson.objects.values('course').annotate(s_amount=Sum('play_count')).order_by('-s_amount')
            courses = []
            for le in lesson_group:
                try:
                    cours = Course.objects.get(id=le['course'], is_click=True, is_homeshow=True)
                    courses.append(cours)
                except:
                    pass
        elif orderBy == '3':
            courses=Course.objects.filter(Q(is_click=True), Q(is_homeshow=True)).order_by('-favorite_count').all()
        obj = paging(courses,page,pageSize) #实例化分页类
        try:
            if obj.pl():
                Response.data = {
                    "ad": [{"target_id": str(a.target_id),
                              "url": settings.SITE_URL+settings.MEDIA_URL+str(a.image_url),
                              "ad_type": str(a.ad_type),
                              "name": str(a.title)} for a in ad],
                    "list":[{
                        "course_id":str(o.id),
                        "course_name":str(o.name),
                        "img_url":settings.SITE_URL+settings.MEDIA_URL+str(o.image),
                        "student_count":str(o.student_count)} for o in obj.pl()]
                }
                Response.message = "数据加载成功"
                Response.success = True
        except Exception as e:
            logger.error(e)

        template_vars = Response.dumps()
        cache.set('getExcellentCourse_'+str(orderBy)+'_'+str(page)+'_'+str(pageSize)+'_'+str(loadAd), template_vars, settings.CACHE_TIME)

    return HttpResponse(template_vars, content_type="application/json")

# 职业课程
@csrf_exempt
@response_init
def getCareerCourse(request):
    template_vars = cache.get('getCareerCourse')
    if not template_vars:
        try:
            career_course_list = CareerCourse.objects.filter(course_scope=None).order_by("index", "id")
            Response.data = {
                "list": [{"career_id": str(course.id),
                          "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.app_image),
                          "name": str(course.name)} for course in career_course_list]
            }
            Response.message = "数据加载成功"
            Response.success = True
        except Exception as e:
            logger.error(e)

        template_vars = Response.dumps()
        cache.set('getCareerCourse', template_vars, settings.CACHE_TIME)

    return HttpResponse(template_vars, content_type="application/json")

# 职业课程详情
@csrf_exempt
@response_init
def getCareerDetail(request):
    try:
        try:
            UUID = request.REQUEST.get("UUID", None)
            userId = request.REQUEST.get("userId", None)
            user = UserProfile.objects.get(uuid=UUID, id=userId)
        except UserProfile.DoesNotExist:
            user = None

        careerId = request.REQUEST.get('careerId', None)
        career_course = CareerCourse.objects.get(pk=careerId)
        last_course_id = 1
        template_vars = cache.get('getCareerDetail_'+str(careerId))
        if not template_vars:
            if careerId is not None:

                # 如果最近没有观看记录，则返回第一课(默认的最近观看记录)
                stages = career_course.stage_set.all().order_by("index", "id")
                if len(stages) > 0:
                    courses = Course.objects.filter(stages=stages[0]).order_by("index", "id")
                    if len(courses) > 0:
                        last_course_id = courses[0].id

                Response.data = {
                    "desc": career_course.description,
                    "last_course_id": str(last_course_id),
                    "stage": [{
                            "stage_name": str(stage.name),
                            "stage_desc": str(stage.description),
                            "list":[{
                                        "course_id": str(course.id),
                                        "name": str(course.name),
                                        "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.image),
                                        "updating": 0 if course.is_click else 1
                            } for course in Course.objects.filter(stages=stage).order_by("index", "id")]
                        } for stage in career_course.stage_set.all().order_by("index", "id")]
                }

                template_vars = Response.data
                cache.set('getCareerDetail_'+str(careerId), template_vars, settings.CACHE_TIME)

        if careerId is not None:
            # 获取最近看的视频对应的课程
            recent_learned_lesson = UserLearningLesson.objects.filter(user=user, lesson__course__stages__career_course=career_course).order_by("-date_learning")
            if len(recent_learned_lesson) > 0:
                last_course_id = recent_learned_lesson[0].lesson.course.id

        template_vars['last_course_id'] = str(last_course_id)
        Response.data = template_vars
        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        print e
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")

# 职业课程价格
@csrf_exempt
@response_init
def getCareerPrice(request):
    try:
        careerId = request.REQUEST.get("careerId", None)
        if careerId is None:
            raise APIException("careerId不能为空")

        # 检验权限并得到对应的用户
        user = checkUser(request, "all")

        career_course = CareerCourse.objects.get(pk=careerId)
        # 实际应支付价格
        cur_careercourse = get_real_amount(user, career_course)
        if cur_careercourse.buybtn_status == 0:
            # 全款支付和试学首付
            pay = {
                "price": str(cur_careercourse.total_price),
                "first_pay": str(cur_careercourse.first_payment),
                "balance": "-1"
            }
            # 获取该职业课程下所有开放的班级
            class_list = [
                {
                    "class_id": str(_class.id),
                    "class_no": str(_class.coding),
                    "teacher": str(_class.teacher.nick_name),
                    "max_student": str(_class.student_limit),
                    "curr_student": str(_class.current_student_count)
                } for _class in cur_careercourse.class_set.filter(is_active=True, status=1)]
        elif cur_careercourse.buybtn_status == 1:
            # 尾款支付
            pay = {
                "price": "-1",
                "first_pay": "-1",
                "balance": str(cur_careercourse.balance_payment)
            }
            userclass = Class.objects.get(students=user, career_course=cur_careercourse)
            class_list = [
                {
                    "class_id": str(userclass.id),
                    "class_no": str(userclass.coding),
                    "teacher": str(userclass.teacher.nick_name),
                    "max_student": str(userclass.student_limit),
                    "curr_student": str(userclass.current_student_count)
                }]
        else:
            # 已经购买
            pay = {
                "price": "-1",
                "first_pay": "-1",
                "balance": "-1"
            }
            class_list = [{}]
        Response.data = {
            "vno": settings.IOSVERSION,
            "pay": pay,
            "class_list": class_list
        }
        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message
    except CareerCourse.DoesNotExist:
        Response.message = "无此职业课程"
    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")


# 名师风采
@csrf_exempt
@response_init
def getTeacherList(request):
    template_vars = cache.get('getTeacherList')
    if not template_vars:
        try:
            group = Group.objects.get(name='老师')   #所有老师
            te_list = Course.objects.distinct().values_list('teacher')
            teachers = group.user_set.filter(id__in=te_list).order_by("index", "id")
            Response.data = {
                "list": [
                    {
                        "teacher_id": str(teacher.id),
                        "avatar": settings.SITE_URL+settings.MEDIA_URL+str(teacher.avatar_url),
                        "name": str(teacher.nick_name),
                        "job": str(teacher.position),
                        "desc": str(teacher.description)
                    } for teacher in teachers]
            }
            Response.message = "数据加载成功"
            Response.success = True
        except Exception, e:
            logger.error(e)

        template_vars = Response.dumps()
        cache.set('getTeacherList', template_vars, settings.CACHE_TIME)

    return HttpResponse(template_vars, content_type="application/json")

# 名师详情
@csrf_exempt
@response_init
def getTeacherDetail(request):
    teacherId = request.REQUEST.get('teacherId', None)
    template_vars = cache.get('getTeacherDetail_'+str(teacherId))
    if not template_vars:
        try:
            if teacherId is not None:
                teacher = UserProfile.objects.get(pk=teacherId)
                Response.data={
                    "course_list":[{
                                       "course_id": str(course.id),
                                       "course_name": str(course.name),
                                       "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.image),
                                       "student_count": str(course.student_count),
                                       "updating": 0 if course.is_click else 1
                                   } for course in Course.objects.filter(teacher=teacher)]
                }
                Response.message = "数据加载成功"
                Response.success = True
        except Exception as e:
            logger.error(e)

        template_vars = Response.dumps()
        cache.set('getTeacherDetail_'+str(teacherId), template_vars, settings.CACHE_TIME)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 登录
@csrf_exempt
@response_init
def login(request):
    username = request.REQUEST.get('userName')
    password = request.REQUEST.get('password')

    try:
        if username is None or password is None:
            raise APIException('账号或者密码为空')

        user = auth.authenticate(username=username, password=password)
        if user is None:
            raise APIException('账号或者密码错误')

        auth.login(request, user)

        Response.data = get_user_info(user)
        Response.message = '登录成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


def absolute_media_path(url):
        return settings.SITE_URL+settings.MEDIA_URL + str(url)


def get_user_info(user):
    maps = {
        'user_id': 'id',
        'UUID': 'uuid',
        'user_name': 'username',
        'avatar': 'avatar_url',
        'nickname': 'nick_name',
        'city': 'city',
        'city_id': 'city_id',
        'province': 'city',
        'province_id': 'city',
        'QQ': 'qq',
        'phone': 'mobile',
        'email': 'email',
    }

    def format_id(num):
        if num is None:
            return -1
        return int(num)

    def format_province(city):
        return city.province.name if city else ''

    def format_province_id(city):
        return city.province.id if city else -1

    transforms = {
        'avatar': absolute_media_path,
        'user_id': format_id,
        'city_id': format_id,
        'province': format_province,
        'province_id': format_province_id
    }

    data = {}

    for item in maps:
        value = getattr(user, maps[item])
        if item in transforms:
            value = transforms[item](value)
        else:
            value = str(value) if value is not None else ''

        data[item] = value

    data['is_student'] = 1 if user.is_student() else 0

    return data


def send_sms_code(mobile, ip, code_type):

    start = datetime.now() - timedelta(hours=23, minutes=59, seconds=59)
    send_count = MobileVerifyRecord.objects.filter(Q(ip=ip), Q(created__gt=start)).count()
    if send_count > settings.SMS_COUNT:
        raise APIException('你今天验证太多了哦，请明天再试吧')

    #生成验证码并保存
    code = generate_random(6, 0)
    mobile_record = MobileVerifyRecord()
    mobile_record.code = code
    mobile_record.mobile = mobile
    mobile_record.type = code_type
    mobile_record.ip = ip
    mobile_record.save()

    #发送短信
    apikey = settings.SMS_APIKEY
    tpl_id = settings.SMS_TPL_ID  #短信模板ID
    tpl_value = '#code#=%(code)s&#company#=%(company)s' % {'code': code, 'company': settings.SMS_COMPANY}
    try:
        result=json.loads(tpl_send_sms(apikey, tpl_id, tpl_value, mobile))
        if result['code'] != 0:
            raise APIException('验证码发送失败')
    except Exception as e:
        logger.error(e)
        raise APIException('验证码发送失败')

    return code

def send_email_code(email, ip, code_type):
    #查询同IP是否超出最大发送邮件限制
    start = datetime.now() - timedelta(hours=23, minutes=59, seconds=59)
    send_count=EmailVerifyRecord.objects.filter(Q(ip=ip),Q(created__gt = start)).count()
    if send_count > settings.EMAIL_COUNT:
        return
        #生成激活码
    random_str = generate_random(10, 1)
    #邮件发送记录写入数据库
    email_record = EmailVerifyRecord()
    email_record.code = random_str
    email_record.email = email
    email_record.type = code_type
    email_record.ip = ip
    email_record.save()

    email_title = email_body = ""

    if code_type == 0:
        email_title = settings.EMAIL_SUBJECT_PREFIX + "注册账号激活邮件"
        email_body = """欢迎使用麦子学院账号激活功能 \r\n
请点击链接激活账号：\r
%(site_url)s/user/active/%(email)s/%(random_str)s \r\n
(该链接在24小时内有效)  \r
如果上面不是链接形式，请将地址复制到您的浏览器(例如IE)的地址栏再访问。 \r
        """ % {'site_url': settings.SITE_URL, 'email': base64.b64encode(email), 'random_str': random_str}
    elif code_type == 1:
        email_title = settings.EMAIL_SUBJECT_PREFIX + "找回密码邮件"
        email_body = """欢迎使用麦子学院找回密码功能 \r\n
请点击链接重置密码：\r
%(site_url)s/user/password/reset/%(email)s/%(random_str)s \r\n
(该链接在24小时内有效)  \r
如果上面不是链接形式，请将地址复制到您的浏览器(例如IE)的地址栏再访问。 \r
        """ % {'site_url': settings.SITE_URL, 'email': base64.b64encode(email), 'random_str': random_str}

    try:
        return send_mail(email_title, email_body, settings.EMAIL_FROM, [email])
    except Exception as e:
        logger.error(e)
        #raise APIException('邮件发送失败')

# 邮箱注册
@csrf_exempt
@response_init
def regEmail(request):
    username = request.REQUEST.get('userName')
    password = request.REQUEST.get('password')

    try:

        try:
            validate_email(username)
        except ValidationError:
            raise APIException('邮箱格式错误，请重试')

        if len(password) < 8:
            raise APIException('密码长度至少为8位')

        if len(password) > 50:
            raise APIException('密码长度不能大于50位')

        try:
            UserProfile.objects.get(email=username)
            raise APIException('该帐号已被注册')
        except UserProfile.DoesNotExist:
            pass

        user = common_register(request, username, password, "新网站")
        if user.id is None:
            raise APIException('注册失败')

        #发送注册激活邮件
        send_email_code(username, request.META['REMOTE_ADDR'], 0)

        Response.message = '注册成功'
        Response.success = True
        Response.data = get_user_info(user)

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 手机注册
@csrf_exempt
@response_init
def regPhone(request):
    mobile = request.REQUEST.get('phoneNum')
    step = request.REQUEST.get('step')

    try:
        #手机注册分为三次请求即验证该手机号是否能注册、检查验证码、使用手机号和密码注册
        step = int(step)

        if 1 == step:
            p = re.compile(settings.REGEX_MOBILE)
            if not p.match(mobile):
                raise APIException('手机号码格式不合法')

            try:
                UserProfile.objects.get(mobile=mobile)
                raise APIException('该号码已注册')
            except UserProfile.DoesNotExist:
                pass

            #发送验证码到手机
            send_sms_code(mobile, request.META['REMOTE_ADDR'], 0)

            Response.message = '验证码已发送'
            Response.success = True

        elif 2 == step:
            code = request.REQUEST.get('vcode')
            if code is None:
                raise APIException('验证码不能为空')

            record = MobileVerifyRecord.objects.filter(Q(mobile=mobile), Q(code=code),Q(type=0)).order_by("-created")
            if record:
                if datetime.now()-timedelta(minutes=30) > record[0].created:
                    raise APIException('验证码已过期，请重新获取')
            else:
                raise APIException('验证码不匹配')

            Response.message = '验证码正确'
            Response.success = True

        elif 3 == step:
            password = request.REQUEST.get('password')
            if password is None:
                raise APIException('密码不能为空')

            if len(password) < 8:
                raise APIException('密码长度至少八位')

            if len(password) > 50:
                raise APIException('密码长度不能大于50位')

            user = common_register(request, mobile, password, '新网站')
            if user.id is None:
                raise APIException('注册失败')

            Response.message = '注册成功'
            Response.success = True
            Response.data = get_user_info(user)

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


RESET_PASSWORD_BY_MOBILE = 1
RESET_PASSWORD_BY_EMAIL = 2

# 忘记密码
@csrf_exempt
@response_init
def forgetPwd(request):
    identifier = request.REQUEST.get('userName')

    try:
        if identifier is None:
            raise APIException('请输入邮箱或手机号码')

        p=re.compile(settings.REGEX_EMAIL+"|"+settings.REGEX_MOBILE)
        if not p.match(identifier):
            raise APIException('邮箱或者手机号格式错误')

        if UserProfile.objects.filter(Q(email=identifier) | Q(mobile=identifier)).count() == 0:
            raise APIException('该账号不存在')

        if re.compile(settings.REGEX_MOBILE).match(identifier):
            send_sms_code(identifier, request.META['REMOTE_ADDR'], 1)
            Response.message = '请查收验证码'
            Response.data['type'] = RESET_PASSWORD_BY_MOBILE

        elif re.compile(settings.REGEX_EMAIL).match(identifier):
            send_email_code(identifier, request.META['REMOTE_ADDR'], 1)
            Response.message = '请在邮箱中点击密码重置链接'
            Response.data['type'] = RESET_PASSWORD_BY_EMAIL

        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 重置密码
@csrf_exempt
@response_init
def resetPwd(request):
    identifier = request.REQUEST.get('userName')
    code = request.REQUEST.get('vcode')
    password = request.REQUEST.get('newPwd')

    try:
        if identifier is None or code is None:
            raise APIException('账号或者验证码不能为空')

        if password is None:
            raise APIException('新密码不能为空')

        if len(password) < 8:
            raise APIException('密码长度至少为8位')

        if len(password) > 50:
            raise APIException('密码长度需小于50位')

        if re.compile(settings.REGEX_MOBILE).match(identifier):
            record = MobileVerifyRecord.objects.filter(Q(mobile=identifier), Q(code=code), Q(type=1)).order_by("-created")

            if not record:
                raise APIException('找回密码信息错误，无法找回')

            if datetime.now()-timedelta(minutes=30) > record[0].created:
                raise APIException('手机验证码已经过期，请重试')

        else:
            if re.compile(settings.REGEX_EMAIL).match(identifier):
                record = EmailVerifyRecord.objects.filter(Q(email=identifier), Q(code=code), Q(type=1)).order_by("-created")
                if not record:
                    raise APIException('找回密码信息错误，无法找回')
                if datetime.now()-timedelta(days=1) > record[0].created:
                    raise APIException('找回密码链接已经过期，请到重新发送找回密码邮件')
            else:
                raise APIException('找回密码信息错误，无法找回')

        try:
            user = UserProfile.objects.get(Q(email=identifier) | Q(mobile=identifier))
        except UserProfile.DoesNotExist:
            raise APIException('该账号不存在，请重试')

        user.password = make_password(password)
        user.save()

        Response.message = '密码重置成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 个人中心-学生-我的课程'
@csrf_exempt
@response_init
def getMyCourse(request):
    try:
        user = checkUser(request, "student")
        # 获取职业课程列表
        mycourses = MyCourse.objects.filter(user=user).order_by("index", "-id")
        career_course_list=[]
        course_list=[]
        for course in mycourses:
            if course.course_type == 2:
                try:
                    career_course = CareerCourse.objects.get(pk=course.course, course_scope=None)
                except CareerCourse.DoesNotExist:
                    continue
                #根据职业课程找到对应的班级,计算班级排名未完成
                curren_stu_ranking = current_user_ranking(career_course,user)
                if curren_stu_ranking !="NotSignUp":
                    setattr(career_course, "cur_ranking", int(curren_stu_ranking))
                else:
                    setattr(career_course, "cur_ranking","-1")
                career_course_list.append(career_course)
            elif course.course_type == 1:
                try:
                    course = Course.objects.get(pk=course.course)
                except Course.DoesNotExist:
                    continue
                course_list.append(course)

        Response.data = {
            "career_course": [
                {
                    "course_id": str(career_course.id),
                    "name": str(career_course.name),
                    "img_url": settings.SITE_URL+settings.MEDIA_URL+str(career_course.app_image),
                    "rank": str(career_course.cur_ranking)
                } for career_course in career_course_list],
            "other_course": [
                {
                    "course_id": str(course.id),
                    "name": str(course.name),
                    "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.image)
                }for course in course_list]
        }

        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message
    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")

# 个人中心-学生-我的收藏
@csrf_exempt
@response_init
def getMyCollection(request):
    try:
        user = checkUser(request, "student")
        Response.data = {
            "list": [
                {
                    "course_id": str(favorite.course.id),
                    "name": str(favorite.course.name),
                    "img_url": settings.SITE_URL+settings.MEDIA_URL+str(favorite.course.image)
                }for favorite in MyFavorite.objects.filter(user=user).order_by("-date_favorite")]
        }
        Response.message = "数据加载成功"
        Response.success = True
    except APIException as e:
        Response.message = e.message
    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 修改个人资料
@csrf_exempt
@response_init
def updateUserInfo(request):
    uuid_ = request.REQUEST.get('UUID')
    id_ = request.REQUEST.get('userId')
    nick_name = request.REQUEST.get('nickName')
    city_id = request.REQUEST.get('city')
    qq = request.REQUEST.get('qq')

    try:
        try:
            user = UserProfile.objects.get(id=id_, uuid=uuid_)
        except UserProfile.DoesNotExist:
            raise APIException('请登录后再修改')

        user.nick_name = nick_name

        if city_id:
            try:
                city = CityDict.objects.get(pk=city_id)
                user.city = city
            except CityDict.DoesNotExist:
                raise APIException('城市超出范围')

        if qq and len(qq) > 20:
            raise APIException('QQ号格式错误，请重试')
        user.qq = qq

        try:
            user.save()
        except Exception as e:
            logger.error(e)
            raise APIException('修改失败')

        Response.message = '修改成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 修改头像
@csrf_exempt
@response_init
def updateAvatar(request):
    try:
        file = request.FILES.get("avatar")

        user = checkUser(request, 'all')
        request.user = user

        if file is None:
            raise APIException('必须上传头像图片')

        if file.size / 1024 > settings.AVATAR_SIZE_LIMIT:
            raise APIException("头像大小超过"+str(settings.AVATAR_SIZE_LIMIT)+"KB限制")

        if settings.AVATAR_SUFFIX_LIMIT.find(file.name.split(".")[-1]) == -1:
            raise APIException('头像必须为GIF/JPG/PNG/BMP格式')

        path=os.path.join(settings.MEDIA_ROOT,"temp")
        if not os.path.exists(path): #如果目录不存在创建目录
            os.makedirs(path)

        file_name=str(uuid.uuid1())+".jpg"
        path_file=os.path.join(path,file_name)
        parser = ImageFile.Parser()
        for chunk in file.chunks():
            parser.feed(chunk)
        img = parser.close()

        try:
            if img.mode != "RGB":
                img = img.convert("RGB")
            width, height = img.size
            img.save(path_file, 'jpeg', quality=100)
        except Exception,e:
            logger.error(e)
            raise APIException("头像上传失败")

        picwidth, picheight = (width, height)
        marginTop, marginLeft, marginTo, marginLeft = (0, 0, 0, 0)
        avatar_tmp = file_name
        source_path = os.path.join(settings.MEDIA_ROOT,'temp',avatar_tmp)
        avatar_up_small = upload_generation_dir("avatar")+"/"+avatar_tmp.split(".")[0]+"_thumbnail.jpg"
        avatar_target_path = upload_generation_dir("avatar")+"/"+avatar_tmp.split(".")[0]+"_big.jpg"
        avatar_middle_target_path = upload_generation_dir("avatar")+"/"+avatar_tmp.split(".")[0]+"_middle.jpg"
        avatar_small_target_path = upload_generation_dir("avatar")+"/"+avatar_tmp.split(".")[0]+"_small.jpg"

        f = Image.open(source_path)
        f.resize((picwidth,picheight),Image.ANTIALIAS).save(avatar_up_small, 'jpeg', quality=100)
        ft = Image.open(avatar_up_small)
        box=(marginTop,marginLeft,marginTop+width,marginLeft+height)
        # box(0,0,100,100)
        ft.crop(box).resize((220,220), Image.ANTIALIAS).save(avatar_target_path, 'jpeg', quality=100)
        ft.crop(box).resize((104,104), Image.ANTIALIAS).save(avatar_middle_target_path, 'jpeg', quality=100)
        ft.crop(box).resize((70,70), Image.ANTIALIAS).save(avatar_small_target_path, 'jpeg', quality=100)


        # 读取原来的头像信息并删除
        if request.user.avatar_url!="avatar/default_big.png" and avatar_tmp != str(request.user.avatar_url).split("/")[-1] :
            avatar_url_path = os.path.join(settings.MEDIA_ROOT)+"/"+str(request.user.avatar_url)
            avatar_middle_thumbnall_path = os.path.join(settings.MEDIA_ROOT)+"/"+str(request.user.avatar_middle_thumbnall)
            avatar_small_thumbnall_path = os.path.join(settings.MEDIA_ROOT)+"/"+str(request.user.avatar_small_thumbnall)
            if os.path.exists(avatar_url_path) :
                os.remove(avatar_url_path)
            if os.path.exists(avatar_middle_thumbnall_path) :
                os.remove(avatar_middle_thumbnall_path)
            if os.path.exists(avatar_small_thumbnall_path) :
                os.remove(avatar_small_thumbnall_path)

        # 将裁切后的图片路径信息更新图片字段
        request.user.avatar_url = avatar_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
        request.user.avatar_middle_thumbnall = avatar_middle_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
        request.user.avatar_small_thumbnall = avatar_small_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
        request.user.save()

        if request.user.uid:
            sync_avatar(request.user.uid, avatar_target_path)

        Response.message = '修改成功'
        Response.success = True
        Response.data['avatar'] = settings.SITE_URL + settings.MEDIA_URL + str(request.user.avatar_url)

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 新增/修改邮箱
@csrf_exempt
@response_init
def updateEmail(request):
    uuid_ = request.REQUEST.get('UUID')
    id_ = request.REQUEST.get('userId')
    new_email = request.REQUEST.get('newEmail')

    try:
        if new_email is None:
            raise APIException('请输入邮箱')

        try:
            user = UserProfile.objects.get(id=id_, uuid=uuid_)
        except UserProfile.DoesNotExist:
            raise APIException('请登录后再修改')

        try:
            validate_email(new_email)
        except ValidationError:
            raise APIException('邮箱格式不合法')

        try:
            UserProfile.objects.get(email=new_email)
            raise APIException('邮箱已占用，请换一个邮箱')
        except UserProfile.DoesNotExist:
            pass

        user.email = new_email
        user.save()

        Response.message = '修改成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 新增手机号
@csrf_exempt
@response_init
def addPhone(request):
    uuid_ = request.REQUEST.get('UUID')
    id_ = request.REQUEST.get('userId')
    mobile = request.REQUEST.get('phoneNum')
    step = request.REQUEST.get('step')

    try:
        if step not in ('1', '2'):
            raise APIException('步骤超出范围')

        try:
            user = UserProfile.objects.get(id=id_, uuid=uuid_)
        except UserProfile.DoesNotExist:
            raise APIException('请登录后再修改')

        if user.mobile is not None:
            raise APIException('该用户已经注册了手机号')

        if mobile is None:
            raise APIException('必须输入手机号')

        p = re.compile(settings.REGEX_MOBILE)
        if not p.match(mobile):
            raise APIException('手机号码格式不合法')

        try:
            UserProfile.objects.get(mobile=mobile)
            raise APIException('该号码已注册')
        except UserProfile.DoesNotExist:
            pass

        step = int(step)

        if 1 == step:
            #发送验证码到手机
            send_sms_code(mobile, request.META['REMOTE_ADDR'], 0)

            Response.message = '验证码已发送'
            Response.success = True

        elif 2 == step:
            code = request.REQUEST.get('vcode')
            if code is None:
                raise APIException('验证码不能为空')

            record = MobileVerifyRecord.objects.filter(Q(mobile=mobile), Q(code=code),Q(type=0)).order_by("-created")
            if record:
                if datetime.now()-timedelta(minutes=30) > record[0].created:
                    raise APIException('验证码过期')
            else:
                raise APIException('验证码不匹配')

            user.mobile = mobile
            user.valid_mobile = 1
            user.save()

            Response.message = '添加成功'
            Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 修改手机号
@csrf_exempt
@response_init
def updatePhone(request):
    uuid_ = request.REQUEST.get('UUID')
    id_ = request.REQUEST.get('userId')
    mobile = request.REQUEST.get('phoneNum')
    step = request.REQUEST.get('step')

    try:
        if step not in ('1', '2', '3', '4'):
            raise APIException('步骤超出范围')

        try:
            user = UserProfile.objects.get(id=id_, uuid=uuid_)
        except UserProfile.DoesNotExist:
            raise APIException('请登录后再修改')

        if user.mobile is None:
            raise APIException('该用户还没有添加手机号')

        if mobile is None:
            raise APIException('必须输入手机号')

        p = re.compile(settings.REGEX_MOBILE)
        if not p.match(mobile):
            raise APIException('手机号码格式不合法')

        step = int(step)

        if 1 == step:
            if user.mobile != mobile:
                raise APIException('手机号不符')

            #发送验证码到手机
            send_sms_code(mobile, request.META['REMOTE_ADDR'], 0)

            Response.message = '验证码已发送'
            Response.success = True

        elif 2 == step:
            code = request.REQUEST.get('vcode')
            if code is None:
                raise APIException('验证码不能为空')

            record = MobileVerifyRecord.objects.filter(Q(mobile=mobile), Q(code=code),Q(type=0)).order_by("-created")
            if record:
                if datetime.now()-timedelta(minutes=30) > record[0].created:
                    raise APIException('验证码过期')
            else:
                raise APIException('验证码不匹配')

            Response.message = '验证成功'
            Response.success = True

        elif 3 == step:
            try:
                UserProfile.objects.get(mobile=mobile)
                raise APIException('该号码已注册')
            except UserProfile.DoesNotExist:
                pass
            #发送验证码到手机
            send_sms_code(mobile, request.META['REMOTE_ADDR'], 0)

            Response.message = '验证码已发送'
            Response.success = True

        elif 4 == step:
            code = request.REQUEST.get('vcode')
            if code is None:
                raise APIException('验证码不能为空')

            record = MobileVerifyRecord.objects.filter(Q(mobile=mobile), Q(code=code),Q(type=0)).order_by("-created")
            if record:
                if datetime.now()-timedelta(minutes=30) > record[0].created:
                    raise APIException('验证码过期')
            else:
                raise APIException('验证码不匹配')

            user.mobile = mobile
            user.save()

            Response.message = '修改成功'
            Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 个人中心-教师-我的班级
@csrf_exempt
@response_init
def getMyClass(request):
    try:
        user = checkUser(request, "teacher")
        classing = Class.objects.filter(teacher = user,status = 1,is_active = True).annotate(num_students=Count('students'))
        Response.data = {
            "list": [
                {
                    "class_id": str(c.id),
                    "class_name": str(c.coding),
                    "student_count": str(c.num_students),
                    "img_url": settings.SITE_URL+settings.MEDIA_URL+str(c.career_course.app_image)
                }for c in classing]
        }
        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 个人中心-教师-班级详情
@csrf_exempt
@response_init
def getClassDetail(request):
    try:

        user = checkUser(request, 'teacher')

        class_id = request.REQUEST.get('classId', None)
        class_ = Class.objects.get(pk = class_id)

        class_student_list=class_.classstudents_set.all()

        Response.data = {
            "list": [
                {
                    "student_id": str(class_student.user.id),
                    "student_name": str(class_student.user.nick_name),
                    "student_city": str(class_student.user.city),
                    "avatar": absolute_media_path(class_student.user.avatar_url),
                }for class_student in class_student_list]
        }

        Response.message = "数据加载成功"
        Response.success = True

    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")

# 个人中心-教师-学员详情
@csrf_exempt
@response_init
def getStudentDetail(request):
    try:

        user = checkUser(request, 'teacher')

        class_id = int(request.REQUEST.get('classId', None))
        student_id = int(request.REQUEST.get('studentId', None))

        student=UserProfile.objects.get(pk=student_id)

        try:
            class_ = Class.objects.get(pk=class_id)
            #class_student = ClassStudents.objects.get(student_class=class_id, user=user)
        except Class.DoesNotExist:
            raise APIException('班级不存在')

        if class_.teacher != user:
            raise APIException('你不属于该班级，不能进入该班级')

        # 获取最新学习计划
        planning_list = Planning.objects.filter(
            user_id=student_id,
            career_course=class_.career_course
        ).order_by(
            "-version",
            "-id"
        )

        is_pause = False
        planning = None
        planning_pause_reason = ""
        if len(planning_list) > 0:
            planning = planning_list[0]

            # 是否暂停状态 最近一次的 restore_date 是不是为空
            planning_pauses = PlanningPause.objects.filter(planning=planning.id).order_by("-id")
            if len(planning_pauses) > 0:

                is_pause = True
                planning_pause = planning_pauses[0]

                # 不合法的时间，返回 None
                if planning_pause.restore_date:
                    is_pause = False

        state=""
        if not planning:
            state = "尚未设置学习计划"
        elif is_pause:
            state = "暂停中"
            planning_pause_reason = planning_pause.reason
        else:
            state="正在进行"

        stagelist=[]
        for stage in Stage.objects.filter(career_course=class_.career_course).order_by("index", "id"):
            list=[]
            rebuild_count=0
            for course in Course.objects.filter(stages=stage).order_by("index", "id"):

                course_scores = CourseScore.objects.filter(user_id = student_id, course = course).order_by("-rebuild_count")
                score=-1

                if len(course_scores):
                    rebuild_count=course_scores[0].rebuild_count
                    ret=check_exam_is_complete(student, course)
                    if ret == 1:
                        score=get_course_score(course_scores[0])
                # score=0
                # if len(course_scores):
                #     score=get_course_score(course_scores[0])
                #     rebuild_count=course_scores[0].rebuild_count
                list.append(
                    {
                        "course_id": str(course.id),
                        "name": str(course.name),
                        "course_count":course.lesson_set.count(),
                        "score":score,
                        "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.image)
                    }
                )
            stage_missions = Mission.objects.filter(teacher=user, examine_type=4, relation_type=3, relation_id=stage.id)
            for stage_mission in stage_missions:
                stage_mission_records = MissionRecord.objects.filter( mission=stage_mission.id , student_id=student_id, teacher=user, rebuild_count=rebuild_count)
                score=0;
                if len(stage_mission_records):
                    score=stage_mission_records[0]
                list.append(
                    {
                        "course_id": str(stage_mission.id),
                        "name": str(stage_mission.name),
                        "course_count":-1,
                        "score": score,
                        "img_url": ""
                    }
                )
            stagelist.append(
                {
                    "stage_name": str(stage.name),
                    "stage_desc": str(stage.description),
                    "list": list
                }
            )

        Response.data = {
            "state": state ,
            "pause_cause": planning_pause_reason,
            "stage": stagelist
        }

        # # 职业课程的相应阶段
        # stages = Stage.objects.filter(career_course=class_.career_course)
        #
        # for stage in stages:
        #
        #     # 获取阶段中的课程
        #     courses = Course.objects.filter(stages=stage).order_by("index", "id")
        #
        #     for course in courses:
        #         course = _get_course_info(course, user_id)
        #
        #     stage.courses = enumerate(courses, start=1)
        #
        #     # 阶段任务
        #     stage_missons = Mission.objects.filter(teacher=class_.teacher,
        #                                            examine_type=4,
        #                                            relation_type=3,
        #                                            relation_id=stage.id)
        #     for stage_misson in stage_missons:
        #         stage_mission_records = MissionRecord.objects.filter(
        #             mission=stage_misson.id
        #         )
        #
        #         if len(stage_mission_records) > 0:
        #             stage_misson.score = stage_mission_records[0].score
        #
        #         else:
        #             stage_misson.score = None
        #
        #     stage.stage_missons = enumerate(stage_missons, start=1)


        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message
    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")


# 个人中心-教师-暂停/恢复
@csrf_exempt
@response_init
def setPause(request):
    try:
        user = checkUser(request, "teacher")
        classId = request.REQUEST.get('classId', None)
        studentId = request.REQUEST.get('studentId', None)
        type = request.REQUEST.get('type', None)
        pauseCause = request.REQUEST.get('pauseCause', None)

        if classId is None:
            raise APIException('班级编号不能为空')

        if studentId is None:
            raise APIException('学生ID不能为空')

        if type is None:
            raise APIException('暂停类别不能为空')

        try:
            class_ = Class.objects.get(pk=classId)
        except Class.DoesNotExist:
            raise APIException('无此班级')

        planning = Planning.objects.filter(user_id=studentId, career_course=class_.career_course, is_active=True)
        if len(planning) > 0:
            if type == "0":
                if pauseCause is None:
                    raise APIException('暂停原因不能为空')

                # 暂停则插入一条新的请假记录
                planning_pause = PlanningPause()
                planning_pause.planning = planning[0]
                planning_pause.teacher = user
                planning_pause.pause_date = datetime.now()
                planning_pause.reason = pauseCause
                planning_pause.save()
            elif type == "1":
                planning_pause = PlanningPause.objects.filter(planning=planning[0], teacher=user).order_by("-pause_date")
                if len(planning_pause) > 0:
                    planning_pause[0].restore_date = datetime.now()
                    planning_pause[0].save()
                else:
                    raise APIException('还没有请假记录')
        else:
            raise APIException('还没有生成计划')

        Response.message = "数据更新成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

def _getCourseProgress(student_id, course_id, Response):
    try:
        course=Course.objects.get(pk=course_id)
        course_scores = CourseScore.objects.filter(user_id = student_id, course=course).order_by("-rebuild_count")
        score=-1
        pass_state='0'
        rebuild_count=0

        user=UserProfile.objects.get(pk=student_id)

        ret=check_exam_is_complete(user, course)
        if len(course_scores):
            rebuild_count=course_scores[0].rebuild_count
            if ret == 1:
                score=get_course_score(course_scores[0])
                if score >= 60:
                    pass_state = '1'
                else:
                    pass_state = '2'

        list=[]

        #计算课程学习
        lesson_list = course.lesson_set.all()

        if  len(lesson_list) > 0:
            learning_lesson_list = UserLearningLesson.objects.filter(user_id= student_id, lesson__in=lesson_list, is_complete = True)

            list.append(
                {
                    "name": "课程学习",
                    "count": len(lesson_list),
                    "done": len(learning_lesson_list),
                    "score": -1
                }
            )

        #计算随堂测验
        paper_list = Paper.objects.filter(examine_type=2, relation_type=1,
                                          relation_id__in=course.lesson_set.all().values_list("id"))
        paper_count=len(paper_list)
        #quiz_count=Quiz.objects.filter(paper__in=paper_list).count()
        if  paper_count > 0:
            # paper_record_list= PaperRecord.objects.filter(student_id=student_id, rebuild_count=rebuild_count, paper__in=paper_list)
            paper_iscomplete_count = 0
            for paper in paper_list:
                temp_paper_list = []
                temp_paper_list.append(paper)
                if check_iscomplete_paper_exam(temp_paper_list, student_id, rebuild_count):
                    paper_iscomplete_count += 1
            #quiz_done=QuizRecord.objects.filter(paper_record__in=paper_list).count()

            list.append(
                {
                    "name": "随堂测验",
                    "count": paper_count,
                    "done": paper_iscomplete_count,
                    "score": -1
                }
            )

        # 计算随堂作业
        homework_list = Homework.objects.filter(examine_type=1, relation_type=1,
                                                relation_id__in=course.lesson_set.all().values_list("id"))
        homework_count = len(homework_list)
        if  homework_count > 0:
            homework_done= HomeworkRecord.objects.filter(student_id=student_id, homework__in=homework_list).count() #rebuild_count=rebuild_count,


            list.append(
                {
                    "name": "随堂作业",
                    "count": homework_count,
                    "done": homework_done,
                    "score": -1
                }
            )

        # 计算总测验
        paper = Paper.objects.filter(examine_type=2, relation_type=2, relation_id=course.id)
        paper_count=0
        paper_count_done=0
        #if Quiz.objects.filter(paper__in=paper).count() > 0:
        if len(paper)>0:
            paper_count = 1
            paper_record=PaperRecord.objects.filter(student_id=student_id, rebuild_count=rebuild_count, paper__in=paper)
            paper_record_score=0
            if len(paper_record):
                paper_count_done=1
                paper_record_score = paper_record[0].score
            list.append(
                {
                    "name": "课程总测验",
                    "count": paper_count,
                    "done": paper_count_done,
                    "score": paper_record_score
                }
            )

        # 是否有项目制作
        project=Project.objects.filter(examine_type=5, relation_type=2, relation_id=course.id)
        project_count=0
        project_count_done=0

        if course.has_project and len(project) > 0:
            project_count = 1
            project_record = ProjectRecord.objects.filter(student_id=student_id, rebuild_count=rebuild_count, project__in=project)
            project_state="未上传"
            project_record_score = 0
            if len(project_record):
                project_count_done=1

                if project_record[0].upload_file:
                    if project_record[0].score:
                        project_record_score = project_record[0].score
                        project_state="已打分:" + str(project_record[0].score)
                    else:
                        project_state="已上传"
                else:
                    project_state="未上传"


            list.append(
                {
                    "name": "项目制作",
                    "count": project_count,
                    "done": project_count_done,
                    "score": project_record_score,
                    "project_state":project_state
                }
            )

        Response.data={
            "score": score ,
            "pass_state": pass_state,
            "list":list
        }

        Response.message = "数据加载成功"
        Response.success = True

    except APIException as e:
        Response.message = e.message
    return
# 个人中心-教师-课程进度
@csrf_exempt
@response_init
def getCourseProgress(request):
    try:

        user = checkUser(request, 'teacher')

        course_id = request.REQUEST.get('courseId', None)
        student_id = request.REQUEST.get('studentId', None)

        _getCourseProgress(student_id, course_id, Response)

    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")


# 热门关键字
@csrf_exempt
@response_init
def getHotSearch(request):
    try:
        keywords = RecommendKeywords.objects.all()[:10]
        keywords = [{"name": keyword.name} for keyword in keywords]
    except Exception as e:
        keywords = []
    finally:
        Response.message = '获取成功'
        Response.success = True
        Response.data = {
            "list": keywords
        }
        return HttpResponse(Response.dumps(), content_type="application/json")


# 搜索
@csrf_exempt
@response_init
def search(request):
    keyword = request.REQUEST.get('keyword',None)
    courses = []
    careerCourses = []
    if keyword is not None and keyword !="" :
        courses = Course.objects.filter(Q(name__icontains=keyword) | Q(search_keywords__name__icontains=keyword), Q(is_click = True)).distinct()
        careerCourses = CareerCourse.objects.filter(Q(name__icontains=keyword) | Q(search_keywords__name__icontains=keyword), Q(course_scope=None)).distinct()
        courses = [{"id": course.id,
                    "name": course.name} for course in courses]
        careerCourses = [{"id": course.id,
                          "name": course.name} for course in careerCourses]
        Response.message = '搜索成功'
        Response.success = True
        Response.data = {
            "careercourse":careerCourses,
            "courses":courses
        }
    else:
        Response.message = '关键词不能为空'
        Response.success = False
    return HttpResponse(Response.dumps(), content_type="application/json")



    

# 获取播放列表
@csrf_exempt
@response_init
def getCoursePlayInfo(request):
    course_id = request.REQUEST.get('courseId')
    uuid_ = request.REQUEST.get('UUID')
    uid = request.REQUEST.get('userId')
    try:
        try:
            user = UserProfile.objects.get(id=uid, uuid=uuid_)
        except UserProfile.DoesNotExist:
            user = UserProfile()

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        teacher = course.teacher
        teacher_info = {
            'teacher_id': teacher.id,
            'name': teacher.nick_name,
            'avatar': absolute_media_path(teacher.avatar_url),
            'desc': teacher.description,
        }

        data = {
            'course_name': course.name,
            'teacher_info': teacher_info,
            "img_url": settings.SITE_URL+settings.MEDIA_URL+str(course.image),
            'video_list': []
        }

        lessons = course.lesson_set.all()
        learnings = UserLearningLesson.objects.filter(lesson__in=lessons, is_complete=True, user_id=user.id)
        learning_ids = [learning.lesson_id for learning in learnings]
        for lesson in lessons:
            is_watch = False
            if lesson.id in learning_ids:
                is_watch = True

            data['video_list'].append({
                'video_id': lesson.id,
                'video_name': lesson.name,
                'video_url': lesson.video_url,
                'is_watch': is_watch
            })

        Response.message = '获取成功'
        Response.success = True
        Response.data = data

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 获取播放进度
@csrf_exempt
@response_init
def getCoursePlayProgress(request):
    course_id = request.REQUEST.get('courseId')

    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        lessons = course.lesson_set.all()
        learnings = UserLearningLesson.objects.order_by('-date_learning')\
            .filter(lesson__in=lessons, is_complete=True, user__pk=user.id)
        watched = [{'lesson_id': learning.lesson_id, 'is_complete': learning.is_complete} for learning in learnings]

        data = {
            'progress': 0,
            'lesson_id': -1,
            'last_url': '',
            'collection_state': 0
        }

        if len(watched) > 0:
            data['progress'] = int((float(len(watched)) / lessons.count()) * 100)
            data['lesson_id'] = learnings.first().lesson_id
            data['last_url'] = learnings.first().lesson.video_url

        # 是否收藏该课程
        if MyFavorite.objects.filter(user=user, course=course).count() > 0:
            data['collection_state'] = 1

        Response.message = '获取成功'
        Response.success = True
        Response.data = data

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 设置播放进度
@csrf_exempt
@response_init
def setCoursePlayProgress(request):
    course_id = request.REQUEST.get('courseId')
    lesson_id = request.REQUEST.get('lesson_id')

    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        try:
            lesson = course.lesson_set.get(pk=lesson_id)
        except Lesson.DoesNotExist:
            raise APIException('没有对应的章节')

        try:
            learning = UserLearningLesson.objects.get(user=user, lesson=lesson)
        except UserLearningLesson.DoesNotExist:
            learning = UserLearningLesson.objects.create(user=user, lesson=lesson)

        learning.is_complete=True
        learning.save()

        lessons = course.lesson_set.all()
        learnings = UserLearningLesson.objects.order_by('-date_learning')\
            .filter(lesson__in=lessons, is_complete=True, user__pk=user.id)
        watched = [{'lesson_id': learning.lesson_id, 'is_complete': learning.is_complete} for learning in learnings]

        progress = 0

        if len(watched) > 0:
            progress = int((float(len(watched)) / lessons.count()) * 100)

        course = lesson.course
        if course.stages is not None:
            career_course = course.stages.career_course
            add_into_mycourse(user, course, career_course)

        Response.message = '设置成功'
        Response.success = True
        Response.data['progress'] = progress

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 获取评论列表
@csrf_exempt
@response_init
def getCommentList(request):
    lessonId = request.REQUEST.get('lessonId')
    page = request.REQUEST.get('page','1')
    pageSize = request.REQUEST.get('pageSize')
    child_comment=[]
    cur_lesson = None
    try:
        cur_lesson = Lesson.objects.get(pk=lessonId)
    except Lesson.DoesNotExist:
        Response.message = '没有该章节'
        Response.success = False
        return HttpResponse(Response.dumps(), content_type="application/json")
    parent_list = cur_lesson.discuss_set.filter(parent_id__isnull=True).order_by("-date_publish") #获取到所有父级评论
    parent = paging(parent_list,page,pageSize)

    Response.message = '获取成功'
    Response.success = True
    Response.data = {
        "list":[{
            "comment_id":p.id,
            "user_id":p.user.id,
            "user_name":p.user.nick_name,
            "avatar":settings.SITE_URL+settings.MEDIA_URL+str(p.user.avatar_url),
            "desc":p.content,
            "date":str(p.date_publish),
            "child_list":[{
                "comment_id":c.id,
                "user_id":c.user.id,
                "user_name":c.user.nick_name,
                "avatar":settings.SITE_URL+settings.MEDIA_URL+str(c.user.avatar_url),
                "desc":c.content,
                "date":str(c.date_publish)
            } for c in cur_lesson.discuss_set.filter(parent_id = p.id) ]
        } for p in parent.pl()]
    }
    return HttpResponse(Response.dumps(), content_type="application/json")


# 发布评论
@csrf_exempt
@response_init
def sendComment(request):
    user = checkUser(request, 'all')
    lessonId = request.REQUEST.get('lessonId')
    parentId = request.REQUEST.get('commentId',None)
    desc = request.REQUEST.get('desc',None)
    if desc is None:
        Response.message = "评论内容为空"
        Response.success = False
        return HttpResponse(Response.dumps(), content_type="application/json")
    dis = Discuss()
    dis.content = desc
    dis.parent_id = parentId
    dis.lesson_id = lessonId
    dis.user_id = user.id
    pid = dis.save()
    Response.message = "评论成功"
    Response.success = True
    if parentId is not None:
        try:
            parentObj = Discuss.objects.get(pk=parentId)
            puser = parentObj.user
            sys_send_message(user.id,puser.id,2,desc,lessonId) #添加消息函数
            # app推送
            lesson = Lesson.objects.get(pk=lessonId)
            app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [puser.token])
        except Exception as e:
            logger.error(e)
    else:
        try:
            lesson = Lesson.objects.get(pk=lessonId)
            # 录课老师对象
            teacher = lesson.course.teacher
            sys_send_message(user.id,teacher.id,2,desc,lessonId) #添加消息函数
            app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [teacher.token])
            # 带课老师对象
            teachers = UserProfile.objects.filter(
                id__in=Class.objects.filter(career_course=lesson.course.stages.career_course).values("teacher").distinct())
            for class_teacher in teachers:
                if teacher.id != class_teacher.id:
                    sys_send_message(user.id,class_teacher.id,2,desc,lessonId) #添加消息函数
                    app_send_message("系统消息", str(user.nick_name) + "在课程" + str(lesson.name) + "中回复了你", [class_teacher.token])
        except Exception as e:
            logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")
    
# 添加收藏
@csrf_exempt
@response_init
def addCollection(request):
    course_id = request.REQUEST.get('courseId')
    user = checkUser(request, 'all')
    favorite = MyFavorite()
    course = Course()
    try:
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('不存在该课程')
        try:
            favorite = MyFavorite.objects.get(user=user, course=course_id)
            Response.message = "该课程已经收藏"
            Response.success = False
        except MyFavorite.DoesNotExist :
            favorite.user = user
            favorite.course_id = course_id
            favorite.save()
            # 收藏数加1
            course.favorite_count += 1
            course.save()
            Response.message = "收藏成功"
            Response.success = True
        except Exception as e:
            logger.error(e)
    except APIException as e:
        Response.message = e.message
    return HttpResponse(Response.dumps(), content_type="application/json")

# （批量）删除收藏
@csrf_exempt
@response_init
def delCollection(request):
    course_id_str = request.REQUEST.get('courseId')
    try:
        user = checkUser(request, 'all')
        course_list_id = course_id_str.split(',')
        for course_id in course_list_id:
            try:
                favorite = MyFavorite.objects.get(user=user, course=course_id)
                favorite.delete()
                course = Course.objects.get(pk=course_id)
                course.favorite_count -= 1
                course.save()
            except MyFavorite.DoesNotExist:
                pass
        Response.message = "批量删除收藏成功"
        Response.success = True
    except Exception as e :
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")




# 学生-我的课程
@csrf_exempt
@response_init
def getMyCourseStage(request):
    #注意这个course id实际上是职业课程id
    course_id = request.REQUEST.get('courseId')

    try:
        user = checkUser(request, 'all')

        try:
            course = CareerCourse.objects.get(pk=course_id)
        except CareerCourse.DoesNotExist:
            raise APIException('没有对应的课程')

        stage_set = course.stage_set.all()
        stages = []
        for s in stage_set:
            stage_state = UserUnlockStage.objects.filter(user=user, stage=s.id).count() > 0
            stage = {'stage_name': s.name, 'stage_desc': s.description,'stage_state':1 if stage_state else 0 }
            course_set = s.course_set.all()
            scores = {}
            for c in course_set:
                try:
                    course_score = CourseScore.objects.get(user=user, course=c, rebuild_count=get_rebuild_count(user, c))
                    score=-1
                    if check_exam_is_complete(user, c)== 1:
                        score = get_course_score(course_score, c)
                except CourseScore.DoesNotExist:
                    score = -1
                scores[c.id] = score
            stage['list'] = [{'course_id': c.id, 'name': c.name, 'score': scores[c.id], 'img_url': settings.SITE_URL + settings.MEDIA_URL + str(c.image),
                              'course_count': c.lesson_set.count()} for c in course_set]
            stages.append(stage)

        study_power = current_study_point(course, user)
        if study_power != 'NotSignUp':
            rank = {'study_power': study_power['mypoint'], 'my_rank': current_user_ranking(course, user)}
            classmate_rank = all_stu_ranking(course, user)
            all_rank = [{'user_id': cr.user.id, 'user_name': cr.user.nick_name, 'study_power': cr.study_point,
                         'avatar': settings.SITE_URL + settings.MEDIA_URL + str(cr.user.avatar_url)} for cr in classmate_rank]
            all_rank = sorted(all_rank, key=lambda item: -item['study_power'])
            rank['all_rank'] = all_rank
        else:
            rank = {'study_power': -1, 'my_rank': -1, 'all_rank': []}

        Response.message = '数据获取成功'
        Response.success = True
        Response.data['vno'] = settings.IOSVERSION
        Response.data['stage'] = stages
        Response.data['rank'] = rank

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-课程详情
@csrf_exempt
@response_init
def getMyCourseDetail(request):
    try:

        user = checkUser(request, 'all')

        course_id = request.REQUEST.get('courseId', None)
        student_id = request.REQUEST.get('userId', None)

        _getCourseProgress(student_id, course_id, Response)

    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-视频列表
@csrf_exempt
@response_init
def getMyCourseVideoList(request):
    try:
        user = checkUser(request, 'all')
        course_id = request.REQUEST.get('courseId')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        lessons = course.lesson_set.all()
        learnings = UserLearningLesson.objects.filter(lesson__in=lessons, is_complete=True, user_id=user.id)
        learning_ids = [learning.lesson_id for learning in learnings]
        video_list = []
        for lesson in lessons:
            is_watch = False
            if lesson.id in learning_ids:
                is_watch = True

            video_list.append({
                'video_id': lesson.id,
                'video_name': lesson.name,
                'is_watch': is_watch
            })

        Response.message = '数据获取成功'
        Response.success = True
        Response.data['list'] = video_list

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-作业列表
@csrf_exempt
@response_init
def getMyHomeworkList(request):
    course_id = request.REQUEST.get('courseId')

    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        lessons = course.lesson_set.order_by("index", "id")

        # lesson_ids = [lesson.id for lesson in lessons]

        works=[]
        for lesson in lessons:
            homework = Homework.objects.filter(examine_type=1, relation_type=1, relation_id=lesson.id)
            if len(homework) > 0:
                works.append(homework[0])

        # works = Homework.objects.filter(relation_id__in=lesson_ids, examine_type=1, relation_type=1)

        #rebuild_count = get_rebuild_count(user, course)

        completed = HomeworkRecord.objects.filter(homework__in=works, student=user)  # rebuild_count=rebuild_count,

        completed = [item.homework_id for item in completed]
        lessons = {lesson.id: lesson for lesson in lessons}

        meta = []

        for w in works:
            lesson = lessons[w.relation_id]
            meta.append({
                'homework_id': lesson.id,
                'homework_name': lesson.name,
                'is_update': True if w.id in completed else False
            })

        if len(meta) == 0:
            raise APIException('没有对应的随堂作业')

        Response.message = '获取成功'
        Response.success = True
        Response.data['list'] = meta

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 学生-随堂测试章节列表
@csrf_exempt
@response_init
def getTestChapterList(request):
    course_id = request.REQUEST.get('courseId')

    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        lessons = course.lesson_set.all()

        lesson_ids = [lesson.id for lesson in lessons]

        papers = Paper.objects.filter(relation_id__in=lesson_ids, examine_type=2, relation_type=1)

        rebuild_count = get_rebuild_count(user, course)

        completed = PaperRecord.objects.filter(rebuild_count=rebuild_count, student=user)

        completed = [item.paper_id for item in completed]
        lessons = {lesson.id: lesson for lesson in lessons}

        list_ = []
        for paper in papers:
            # 检查试卷是否已经完成
            paper_list = []
            paper_list.append(paper)
            paper_iscomplete = check_iscomplete_paper_exam(paper_list, user, rebuild_count)

            lesson = lessons[paper.relation_id]
            list_.append({
                'chapter_id': lesson.id,
                'chapter_name': lesson.name,
                'is_done': paper_iscomplete
            })

        Response.data = {'list': list_}

        if len(list_) == 0:
            raise APIException('没有对应的随堂测验')

        Response.message = '获取成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        print e
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-随堂测试题目列表
@csrf_exempt
@response_init
def getQuestionList(request):
    chapter_id = request.REQUEST.get('chapterId')

    try:
        user = checkUser(request, 'all')

        try:
            lesson = Lesson.objects.get(pk=chapter_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的章节')

        course = lesson.course

        try:
            paper = Paper.objects.get(relation_id=chapter_id, examine_type=2, relation_type=1)
        except Paper.DoesNotExist:
            raise APIException('没有对应的随堂测验')

        rebuild_count = get_rebuild_count(user, course)

        try:
            paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, paper=paper, student=user)
            records = QuizRecord.objects.filter(paper_record=paper_record)
            completed_quiz = [record.quiz_id for record in records]
        except PaperRecord.DoesNotExist:
            completed_quiz = []

        questions = Quiz.objects.filter(paper=paper).all()

        uncompleted_quiz = []

        for question in questions:
            if question.id in completed_quiz:
                continue
            item_list = question.item_list
            results = re.findall(r'<button.*value="(.*)">(.*)<\/button>', item_list)
            options = []
            for item in results:
                options.append({
                    'option': item[0] + '-' + item[1]
                })
            uncompleted_quiz.append({
                'question_id': question.id,
                'question_name': question.question,
                'answer': question.result,
                'option_list': options
            })

        if len(uncompleted_quiz) == 0:
            raise APIException('没有未完成的试题')

        Response.message = '获取成功'
        Response.success = True
        Response.data['list'] = uncompleted_quiz

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-提交随堂测试结果
@csrf_exempt
@response_init
def sendTestResult(request):
    chapter_id = request.REQUEST.get('chapterId')

    try:
        user = checkUser(request, 'all')

        try:
            lesson = Lesson.objects.get(pk=chapter_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的章节')

        course = lesson.course

        try:
            paper = Paper.objects.get(relation_id=chapter_id, examine_type=2, relation_type=1)
        except Paper.DoesNotExist:
            raise APIException('没有对应的随堂测验')

        _answer_quiz(request,user,course,paper)

        # rebuild_count = get_rebuild_count(user, course)
        #
        # try:
        #     paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, paper=paper, student=user)
        #     quiz_records = QuizRecord.objects.filter(paper_record=paper_record)
        #     quiz_completed = [r.quiz_id for r in quiz_records]
        # except PaperRecord.DoesNotExist:
        #     quiz_completed = []
        #     paper_record = PaperRecord(paper=paper, student=user, rebuild_count=rebuild_count, score=0,
        #                                examine_id=paper.examine_ptr_id, study_point=0)
        #     paper_record.save()
        #
        # answers = request.REQUEST.get('answers')
        # if not answers:
        #     raise APIException('答案不能为空')
        #
        # try:
        #     answers = json.loads(answers)
        #     answers = {a['id']: a['answer'] for a in answers}
        # except ValueError:
        #     raise APIException('答案json解析错误')
        #
        # quizs = Quiz.objects.filter(paper=paper).all()
        #
        # quizs = {q.id: q for q in quizs}
        #
        # for qid in answers:
        #     if int(qid) not in quizs or int(qid) in quiz_completed:
        #         continue
        #     quiz_record = QuizRecord(quiz=quizs[int(qid)], result=answers[qid], paper_record=paper_record)
        #     quiz_record.save()
        #
        # #计算正确率
        # quiz_records = QuizRecord.objects.filter(paper_record=paper_record)
        # quiz_records = {r.quiz_id: r for r in quiz_records}
        # total = 0
        # right = 0
        # for qid in quiz_records:
        #     total += 1
        #     if quiz_records[qid].result == quizs[qid].result:
        #         right += 1
        # if total != 0:
        #     accuracy = round(float(right)/total, 2)
        # else:
        #     accuracy = 0
        # paper_record.accuracy = accuracy
        # paper_record.save()

        Response.message = '保存成功'
        Response.success = True
        Response.data = {'accuracy': accuracy}

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 学生-课程总测验
@csrf_exempt
@response_init
def getTotalTest(request):
    course_id = request.REQUEST.get('courseId')

    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        try:
            paper = Paper.objects.get(relation_id=course_id, examine_type=2, relation_type=2)
        except Paper.DoesNotExist:
            raise APIException('没有对应的课程测验')

        rebuild_count = get_rebuild_count(user, course)

        try:
            paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, examine__relation_id=course_id, student=user)
            records = QuizRecord.objects.filter(paper_record=paper_record)
            completed_quiz = [record.quiz_id for record in records]
        except PaperRecord.DoesNotExist:
            completed_quiz = []

        questions = Quiz.objects.filter(paper=paper).all()

        uncompleted_quiz = []

        for question in questions:
            if question.id in completed_quiz:
                continue
            item_list = question.item_list
            results = re.findall(r'<button.*value="(.*)">(.*)<\/button>', item_list)
            options = []
            for item in results:
                options.append({
                    'option': item[0] + '-' + item[1]
                })
            uncompleted_quiz.append({
                'question_id': question.id,
                'question_name': question.question,
                'answer': question.result,
                'option_list': options
            })

        if len(uncompleted_quiz) == 0:
            raise APIException('没有未完成的试题')

        Response.message = '获取成功'
        Response.success = True
        Response.data['list'] = uncompleted_quiz

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

def _answer_quiz(request, user, course, paper):

    rebuild_count = get_rebuild_count(user, course)
    try:
        paper_record = PaperRecord.objects.get(rebuild_count=rebuild_count, paper=paper, student=user)
        quiz_records = QuizRecord.objects.filter(paper_record=paper_record)
        quiz_completed = [r.quiz_id for r in quiz_records]
    except PaperRecord.DoesNotExist:
        quiz_completed = []
        paper_record = PaperRecord(paper=paper, student=user, rebuild_count=rebuild_count, score=0,
                                   examine_id=paper.examine_ptr_id, study_point=0)
        paper_record.save()

    answers = request.REQUEST.get('answers')
    if not answers:
        raise APIException('答案不能为空')

    try:
        answers = json.loads(answers)
        answers = {a['id']: a['answer'] for a in answers}
    except ValueError:
        raise APIException('答案json解析错误')

    quizs = Quiz.objects.filter(paper=paper).all()

    quizs = {q.id: q for q in quizs}

    for qid in answers:
        if int(qid) not in quizs or qid in quiz_completed:
            continue
        quiz_record = QuizRecord(quiz=quizs[int(qid)], result=answers[qid], paper_record=paper_record)
        quiz_record.save()

    #计算正确率
    quiz_records = QuizRecord.objects.filter(paper_record=paper_record)
    quiz_records = {r.quiz_id: r for r in quiz_records}
    total = 0
    right = 0
    for qid in quiz_records:
        total += 1
        if quiz_records[qid].result == quizs[qid].result:
            right += 1
    if total != 0:
        accuracy = round(float(right)/total, 2)
    else:
        accuracy = 0
    paper_record.accuracy = accuracy
    paper_record.save()

    # 如果已经完成所有测验试题
    if len(get_uncomplete_quiz(user, paper, rebuild_count)) == 0:
        paper_score = 100 * accuracy

        # 在考核记录中更新学力和测验分
        paper_study_point = 0
        if paper.relation_type == 1:
            paper_study_point = 1
        elif paper.relation_type == 2:
            paper_study_point = 10
        update_study_point_score(user, paper_study_point, paper_score, paper, paper_record, None, rebuild_count)


# def _answer_quiz(request, quiz_id, select):
#     try:
#         cur_quiz = Quiz.objects.get(pk=quiz_id)
#         cur_paper = cur_quiz.paper
#         user = request.user
#     except Quiz.DoesNotExist:
#         raise APIException('没有该试题')
#
#         # 获取到course对象
#     try:
#         if cur_paper.relation_type == 1:
#             # 章节
#             cur_course = Lesson.objects.get(pk=cur_paper.relation_id).course
#         elif cur_paper.relation_type == 2:
#             # 课程
#             cur_course = Course.objects.get(pk=cur_paper.relation_id)
#     except Exception as e:
#         logger.error(e)
#         # 检查用户是否做过该题
#     rebuild_count = get_rebuild_count(user, cur_course)
#     if QuizRecord.objects.filter(paper_record__student=user, quiz=cur_quiz, paper_record__rebuild_count=rebuild_count).count() > 0:
#         raise APIException('用户已经做过该题')
#         # 生成做题记录
#     # 查询是否有paper_record的记录，如果没有则生成一条新的paper_record记录
#     paper_record = PaperRecord.objects.filter(paper=cur_paper, student=user, rebuild_count=rebuild_count)
#     if len(paper_record)>0:
#         paper_record = paper_record[0]
#     else:
#         paper_record = PaperRecord()
#         paper_record.paper = cur_paper
#         paper_record.examine_id = cur_paper.examine_ptr_id
#         paper_record.score = 0
#         paper_record.study_point = 0
#         paper_record.student = user
#         paper_record.rebuild_count = rebuild_count
#         paper_record.save()
#
#     quiz_record = QuizRecord()
#     quiz_record.quiz = cur_quiz
#     quiz_record.result = select
#     quiz_record.paper_record = paper_record
#     quiz_record.save()
#
#     # 如果已经完成所有测验试题
#     if len(get_uncomplete_quiz(user, cur_paper, rebuild_count)) == 0:
#         # 计算试卷准确率并更新
#         # 获取所有答题记录
#         quiz_record_list = QuizRecord.objects.filter(paper_record__student=user, quiz__paper=cur_paper, paper_record__rebuild_count=rebuild_count)
#         quiz_right_count = 0
#         for quiz_record in quiz_record_list:
#             if quiz_record.quiz.result.lower() == quiz_record.result.lower():
#                 quiz_right_count += 1
#             #该试卷下的总题数
#         quiz_all_count = Quiz.objects.filter(paper=cur_paper).count()
#         paper_accuracy = round(quiz_right_count / quiz_all_count, 2)
#         paper_score = 100 * paper_accuracy
#         paper_record.accuracy = paper_accuracy
#         paper_record.save()
#
#         # 在考核记录中更新学力和测验分
#         paper_study_point = 0
#         if cur_paper.relation_type == 1:
#             paper_study_point = 1
#         elif cur_paper.relation_type == 2:
#             paper_study_point = 10
#         update_study_point_score(user, paper_study_point, paper_score, cur_paper, paper_record, None, rebuild_count)

# 学生-提交总测验结果
@csrf_exempt
@response_init
def sendTotalTestResult(request):

    course_id = request.REQUEST.get('courseId')
    try:
        user = checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        try:
            paper = Paper.objects.get(relation_id=course_id, examine_type=2, relation_type=2)
        except Paper.DoesNotExist:
            raise APIException('没有对应的课程总测验')

        _answer_quiz(request,user,course,paper)

        Response.message = '保存成功'
        Response.success = True
        Response.data = {'accuracy': accuracy}

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 学生-项目制作
@csrf_exempt
@response_init
def getProjectInfo(request):

    course_id = request.REQUEST.get('courseId')

    try:
        user=checkUser(request, 'all')

        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise APIException('没有对应的课程')

        try:
            course_project = Project.objects.get(relation_id=course_id, examine_type=5, relation_type=2)
        except Project.DoesNotExist:
            raise APIException('没有对应的项目制作')

        rebuild_count = get_rebuild_count(user, course)

        course_project_name="项目制作"
        course_project_state=""
        course_project_desc=course_project.description
        #if len(course_project) > 0:
        course_project_records = ProjectRecord.objects.filter(rebuild_count=rebuild_count,project=course_project,
                                                              student=user)
        if len(course_project_records) > 0:
            if course_project_records[0].upload_file:
                if course_project_records[0].score:
                    course_project_state="已打分:" + str(course_project_records[0].score)
                    course_project_desc = course_project_records[0].project.description
                else:
                    course_project_state="已上传"
            else:
                course_project_state="未上传"
        else:
            course_project_state="未上传"


        Response.message = '获取成功'
        Response.success = True
        Response.data={
            "project_state":course_project_state,
            "project_name":course_project_name,
            "project_desc":course_project_desc
        }

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")
    pass

# 学生-获取行政区划列表
@csrf_exempt
@response_init
def getDivisionList(request):
    try:
        try:
            china = CountryDict.objects.get(name='中国')
        except CountryDict.DoesNotExist:
            raise APIException('没有查到中国的区域划分')

        provinces = ProvinceDict.objects.filter(country=china)

        if len(provinces) == 0:
            raise APIException('该国的省份信息为空')

        cities = CityDict.objects.filter(province__in=provinces)

        division = {p.id: {'id': p.id, 'province': p.name, 'city_list': []} for p in provinces}

        for c in cities:
            pid = c.province_id
            if pid not in division:
                continue
            city = {'id': c.id, 'name': c.name}
            division[pid]['city_list'].append(city)

        Response.message = '数据加载成功'
        Response.success = True
        Response.data['list'] = division.values()

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")


# 学生-修改密码
@csrf_exempt
@response_init
def modifyPwd(request):
    old_pwd = request.REQUEST.get('oldPwd')
    new_pwd = request.REQUEST.get('newPwd')

    try:
        if not old_pwd or not new_pwd:
            raise APIException('当前密码和新密码不能为空')
        if len(new_pwd) < 8:
            raise APIException('密码长度必须大于8位')
        if len(new_pwd) > 50:
            raise APIException('密码长度必须小于50位')

        user = checkUser(request, 'all')
        username = user.email if user.email else user.mobile
        user = auth.authenticate(username=username, password=old_pwd)
        if user is None:
            raise APIException('当前密码错误')

        user.password = make_password(new_pwd)
        user.save()

        Response.message = '密码修改成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

#优惠码
@csrf_exempt
@response_init
def validateDiscountCode(request):
    careercourse = request.REQUEST.get('careercourse',None)
    code = request.REQUEST.get('code','')
    try:
        user = checkUser(request, 'all')
        p = re.compile('^[A-Za-z0-9]+$')
        c = p.match(code)
        
        if code == "":
            raise APIException('优惠码不能为空')
        elif len(code) < 16 or len(code) > 16 or not(c):
            raise APIException('优惠码格式不正确')
        elif careercourse is None:
            raise APIException('请选择职业课程')

        coupon_details = Coupon_Details.objects.filter(Q(code_sno=code))
        if len(coupon_details) > 0:
            coupon = coupon_details[0]
        else:
            raise APIException('优惠码不存在')

        if coupon.is_use:
            raise APIException('优惠码已经被使用')
        elif coupon.is_lock and coupon.user != user:
            raise APIException('优惠码已被其他用户占用')
        elif coupon.careercourse_id is not None and careercourse != coupon.careercourse_id:
            try:
                print coupon.careercourse_id
                Course = CareerCourse.objects.get(pk=coupon.careercourse_id)
                raise APIException("你已经绑定了"+Course.name+"职业课程!")
            except CareerCourse.DoesNotExist:
                raise APIException("未知错误!")
        else:

            if not coupon.is_lock:
                coupon.is_lock = True
                coupon.user = user
                coupon.use_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                coupon.careercourse_id = careercourse
                coupon.save()
            money_obj = Coupon.objects.get(id=coupon.coupon_id)
            money = money_obj.coupon_price

            Response.message = '优惠码可以使用'
            Response.success = True
            Response.data={
                "discount":money
            }

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)
    return HttpResponse(Response.dumps(), content_type="application/json")

#留言反馈
@csrf_exempt
@response_init
def feedback(request):
    content = request.REQUEST.get('content',None)

    try:

        if content is None:
            raise APIException('留言反馈内容不能为空')
        elif len(content) > 100:
                raise APIException('留言内容超出100长度')

        feedback = Feedback()
        feedback.content = content
        feedback.save()

        Response.message = '留言反馈成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

#版本更新评论
@csrf_exempt
@response_init
def checkUpdate(request):
    currVno = request.REQUEST.get('currVno',None)

    try:
        if currVno is None:
            raise APIException('当前版本号不能为空')

        # 是否有新版本
        has_new_version = False

        #最新版本号
        newVersion_list = AndroidVersion.objects.all().order_by("-id")
        if len(newVersion_list) > 0:
            if currVno != newVersion_list[0].vno:
                currVno_list = currVno.split(".")  # 当前版本号列表
                if len(currVno_list) != 3:
                    raise APIException('当前版本号格式不正确')
                newVno_list = newVersion_list[0].vno.split(".")
                for i in range(3):
                    if currVno_list[i] == newVno_list[i]:
                        continue
                    elif currVno_list[i] < newVno_list[i]:
                        has_new_version = True
                        break

            if has_new_version:
                Response.data = {
                    "new_version": {
                        "vno": newVersion_list[0].vno,
                        "size": newVersion_list[0].size,
                        "desc": newVersion_list[0].desc,
                        "is_force": newVersion_list[0].is_force,
                        "down_url": newVersion_list[0].down_url
                    }
                }
                Response.message = '检测到新版本'
                Response.success = True
            else:
                raise APIException('已经是最新版本')

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 创建订单
@csrf_exempt
@response_init
def createOrder(request):
    code = request.REQUEST.get('code',None)  # 优惠码
    careerId = request.REQUEST.get('careerId',None)  # 职业课程ID
    classCoding = request.REQUEST.get('classCoding',None)  # 班级编号
    price = request.REQUEST.get('price',None)  # 支付金额
    payType = request.REQUEST.get('payType',None)  # 支付类型
    try:

        # 权限验证
        user = checkUser(request, 'all')

        order_no = generation_order_no()
        target_stage_list = []
        pay_amount = 0
        cur_careercourse = None
        cur_class = None
        try:
            cur_careercourse = CareerCourse.objects.get(pk=careerId)
        except CareerCourse.DoesNotExist:
            raise APIException('职业课程不存在')

        if payType is None:
            raise APIException('必须传入支付类型')

        #如果是首付款或者全款的情况
        if payType in ("0","1"):
            # 判断该班级中是否已经有该学生
            try:
                cur_class = Class.objects.get(coding=classCoding)
                if cur_class.students.filter(id=user.id).count() == 0:
                    if cur_class.current_student_count >= cur_class.student_limit :
                        raise APIException('当前班级人数已经达到人数上限')
                # 判断用户是否已经在职业课程所属的其他某个班级
                if ClassStudents.objects.filter(Q(user=user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class)).count() > 0:
                    class_students = ClassStudents.objects.get(Q(user=user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class))
                    raise APIException('你已经加入该职业课程下的其他班级('+class_students.student_class.coding+')，不能重复加班')
            except Class.DoesNotExist:
                raise APIException('班级不存在')

        setattr(cur_careercourse, "buybtn_status", get_careercourse_buybtn_status(user, cur_careercourse))
        if cur_careercourse.buybtn_status == 0 :
            if payType == "0":
                # 职业课程所有阶段ID列表
                target_stage_list = get_careercourse_allstage_list(cur_careercourse)
                # 全额
                setattr(cur_careercourse, "total_price", get_careercourse_total_price(cur_careercourse))
                pay_amount = cur_careercourse.total_price
                # 如果有优惠码，查询优惠码对应的折扣价格
                if code is not None:
                    try:
                        coupon_details = Coupon_Details.objects.get(code_sno=code, user=user, is_lock=True, is_use=False)
                    except Coupon_Details.DoesNotExist:
                        raise APIException('优惠码不存在或状态不正确')
                    pay_amount = int(cur_careercourse.total_price) - int(coupon_details.coupon.coupon_price)
            elif payType == "1":
                # 职业课程试学阶段ID列表
                target_stage_list = get_careercourse_trystage_list(cur_careercourse)
                # 试学首付
                setattr(cur_careercourse, "first_payment", get_careercourse_first_payment(cur_careercourse))
                pay_amount = cur_careercourse.first_payment
        elif cur_careercourse.buybtn_status == 1:
            if payType == "2" :
                # 职业课程未支付还处于解锁的所有阶段ID列表
                target_stage_list = get_careercourse_lockstage_list(user, cur_careercourse)
                #计算尾款应支付金额
                setattr(cur_careercourse, "balance_payment", get_careercourse_balance_payment(user, cur_careercourse))
                #用户当前所属该职业课程下的某个班级
                setattr(cur_careercourse, "careercourse_class", get_careercourse_class(user, cur_careercourse))
                class_coding=cur_careercourse.careercourse_class
                cur_class = Class.objects.get(coding=class_coding)
                pay_amount = cur_careercourse.balance_payment
        elif cur_careercourse.buybtn_status == 2:
            raise APIException('该职业课程已经完全解锁，不需再买')
        else:
            raise APIException('未知的购买状态')

        #检查要支付的目标阶段是否已经解锁，如已解锁则提醒错误
        if is_unlock_in_stagelist(user, target_stage_list):
            raise APIException('待购买的课程阶段中包含已经解锁的阶段，请联系管理员')

        # 应支付金额和实际支付金额不一致
        if int(price) != int(pay_amount):
            raise APIException('传入金额与实际应支付金额不一致')

        # 生成订单并存入到数据库
        purchase = UserPurchase()
        purchase.user = user
        purchase.pay_price = int(pay_amount)
        purchase.order_no = order_no
        purchase.pay_type = payType
        purchase.pay_way = 2
        purchase.pay_status = 0
        purchase.pay_careercourse = cur_careercourse
        purchase.pay_class = cur_class
        purchase.save()
        purchase.pay_stage = Stage.objects.filter(id__in=target_stage_list)
        if code is not None and payType == "0":
            purchase.coupon_code = code
        purchase.save()

        Response.data = {
            "order_no": str(order_no),
            "qq": str(cur_class.qq)
        }
        Response.message = '订单生成成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

##################### 支付回调和签名验证 开始 #################################

# 验证消息是否是支付宝发出的合法消息
def alipayVerify(post):
    response_bool = False

    if post.get('notify_id') is not None and post.get('notify_id') != "":
        notify_id = post.get("notify_id")
        response_bool = verifyResponse(notify_id)

    sign = ""
    if post.get("sign") is not None and post.get("sign")!="":
        sign = post.get("sign")

    isSign = getSignVeryfy(post, sign)

    if isSign and response_bool:
        return True
    return False

# 根据反馈回来的信息，验证签名结果
def getSignVeryfy(post, sign):
    pub_key = RSA.importKey(base64.b64decode(settings.ALIPAY_PUBLIC_KEY))
    post = filter_para(dict(post.iterlists()))
    post = create_link_string(post, True, False)
    verifier = PKCS1_v1_5.new(pub_key)
    data = SHA.new(post.encode('utf-8'))
    return verifier.verify(data, base64.b64decode(sign))

def filter_para(paras):
    """过滤空值和签名"""
    for k,v in paras.items():
        paras[k] = v[0]
        if not v or k in ['sign', 'sign_type']:
            paras.pop(k)
    return paras

def create_link_string(paras, sort, encode):
    """对参数排序并拼接成query string的形式"""
    if sort:
        paras = sorted(paras.items(), key=lambda d:d[0])
    if encode:
        return urllib.urlencode(paras)
    else:
        if not isinstance(paras, list):
            paras = list(paras.items())
        ps = ''
        for p in paras:
            if ps:
                ps = '%s&%s=%s' % (ps, p[0], p[1])
            else:
                ps = '%s=%s' % (p[0], p[1])
        return ps


# 获取远程服务器ATN结果,验证返回URL
def verifyResponse(notify_id):
    veryfy_url = "https://mapi.alipay.com/gateway.do?service=notify_verify&partner=" + \
                 str(settings.ALIPAY_PARTNER) + "&notify_id=" + str(notify_id)
    return checkUrl(veryfy_url)

# 获取远程服务器ATN结果
def checkUrl(veryfy_url):
    veryfy_result = 'false'

    try:
        veryfy_result = requests.get(veryfy_url).text
    except Exception as e:
        logger.error(e)

    if veryfy_result.lower().strip() == 'true':
        return True
    return False

# 支付成功回调
@csrf_exempt
@response_init
def paySuccessCallback(request):
    '''
    支付成功后异步通知处理
    :param request:
    :return:
    '''
    try:
        if request.method == 'POST':
            verify_result = alipayVerify(request.POST) # 解码并验证数据是否有效
            if verify_result:
                order_no = request.POST.get('out_trade_no')
                trade_no = request.POST.get('trade_no')
                trade_status = request.POST.get('trade_status')
                result = order_handle(trade_status, order_no, trade_no)
                if result[0] == 'success':
                    return HttpResponse('success') #有效数据需要返回 'success' 给 alipay
    except Exception as e:
        logger.error(e)
    return HttpResponse('fail')

##################### 支付回调和签名验证 结束 #################################

# 我的消息列表
@csrf_exempt
@response_init
def getMyMessage(request):
    try:
        user = checkUser(request, 'all')
        message_list = MyMessage.objects.filter(Q(userB = user.id) | Q(userB = 0,action_type = 1)).order_by("-date_action")
        list_data = []
        for message in message_list:
            message.action_content,_ = re.subn(r'<a([^>]*)>([^<]*)</a>', '', message.action_content)
            try:
                user = UserProfile.objects.get(pk=message.userA)
                list_data.append(
                    {
                        "user_name":user.nick_name,
                        "avatar": settings.SITE_URL+settings.MEDIA_URL+str(user.avatar_url),
                        "desc":message.action_content,
                        "date":str(message.date_action),
                        "type":1
                    }
                )
            except Exception as e:
                list_data.append(
                    {
                        "user_name":'系统消息',
                        "avatar": settings.SITE_URL+settings.MEDIA_URL+'/avatar/default_big.png',
                        "desc":message.action_content,
                        "date":str(message.date_action),
                        "type":0
                    }
                )
        Response.data = {
            "list": list_data
        }
        Response.message = '获取消息成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 获取随堂测验结果
@csrf_exempt
@response_init
def getTestResult(request):
    courseId = request.REQUEST.get('courseId', None)  # 课程ID
    chapterId = request.REQUEST.get('chapterId', None)  # 章节ID

    try:
        user = checkUser(request, 'all')

        if courseId is None and chapterId is None:
            raise APIException("至少需要课程ID或章节ID")

        rebuild_count = 0
        papers = []
        list_ = []
        if courseId is not None:

            course = Course.objects.get(pk=courseId)
            rebuild_count = get_rebuild_count(user, course)

            # 根据课程ID查询该课程下对应的试题和用户是否答对该题
            # 该课程ID对应的试卷
            papers = Paper.objects.filter(examine_type=2, relation_type=2,
                                          relation_id=courseId)


        elif chapterId is not None:
            course = Lesson.objects.get(pk=chapterId).course
            rebuild_count = get_rebuild_count(user, course)
            # 该章节ID对应的试卷
            papers = Paper.objects.filter(examine_type=2, relation_type=1,
                                          relation_id=chapterId)

        if len(papers) > 0:
            # 该试卷对应的当前重修次数的考核记录
            paper_record_list = PaperRecord.objects.filter(paper__in=papers, student=user, is_active=True,
                                           rebuild_count=rebuild_count)

            if len(paper_record_list) <= 0:
                raise APIException("学员还未做过该试卷")

            # 获取学生已经做过的试题
            quiz_record_list = QuizRecord.objects.filter(paper_record__in=paper_record_list)

            # 试卷对应的试题
            quiz_list = Quiz.objects.filter(paper__in=papers)

            for quiz in quiz_list:
                is_right = "-1"
                for quiz_record in quiz_record_list:
                    if quiz.id == quiz_record.quiz.id:
                        # 获取正确答案，并判断学员是否做对该题
                        if quiz.result.lower() == quiz_record.result.lower():
                            is_right = True
                        else:
                            is_right = False
                        break
                list_.append({
                    "id": quiz.id,
                    "answer": quiz.result,
                    "is_right": is_right
                })

            Response.message = '数据获取成功'
            Response.success = True
            Response.data['list'] = list_

        else:
            raise APIException("没有查询到对应的试卷")

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# Add By Steven Yu for test
# @csrf_exempt
# @response_init
# def test(request):
#     try:
#
#         app_send_message_token("hello","world",["4f2635aa73bed8554325b11d9240a3fe754b3fff"])
#
#         Response.message = '数据更新成功'
#         Response.success = True
#         Response.data = {}
#
#     except APIException as e:
#         Response.message = e.message
#
#     except Exception as e:
#         logger.error(e)
#
#     return HttpResponse(Response.dumps(), content_type="application/json")

# 更新推送说明
@csrf_exempt
@response_init
def updatePushToken(request):
    pushToken = request.REQUEST.get('pushToken', None)  # 设备Token

    try:
        user = checkUser(request, 'all')

        if pushToken is None:
            pushToken = ""

        user.token=pushToken
        user.save()

        Response.message = '数据更新成功'
        Response.success = True
        Response.data = {}

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")

# 获取IOS正在审核的版本
@csrf_exempt
@response_init
def getIosCheckVersion(request):
    try:

        Response.data['vno'] = settings.IOSVERSION
        Response.message = '数据获取成功'
        Response.success = True

    except APIException as e:
        Response.message = e.message

    except Exception as e:
        logger.error(e)

    return HttpResponse(Response.dumps(), content_type="application/json")
