# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse,HttpResponseRedirect
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate,login,logout
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import Group
from django.db.utils import IntegrityError
from captcha.models import CaptchaStore
from datetime import datetime, timedelta
from PIL import Image, ImageFile
from utils.tool import generate_random, second_to_time, upload_generation_dir
from utils.yunpian import *
from mz_user.forms import *
from mz_common.models import EmailVerifyRecord, MobileVerifyRecord, MyMessage
from mz_common.decorators import student_required, teacher_required
from mz_common.views import *
from django.contrib.auth.decorators import login_required
from models import *
from mz_lps.models import *
from mz_course.models import *
from mz_course.views import get_recent_learned_lesson
from django.db.models import Count
from aca_course.models import *

import base64, json, re, urllib, urllib2, os, uuid, logging, ucenter

logger = logging.getLogger('mz_user.views')

def user_login(request):
    '''
    前台登录
    :param request:
    :return:
    '''
    login_form = LoginForm(request.POST)
    if login_form.is_valid():
        #获取表单信息
        account = login_form.cleaned_data["account_l"]
        password = login_form.cleaned_data["password_l"]
        source_url = request.POST.get("source_url",None)
        if source_url is None:
            source_url = request.META['HTTP_REFERER']
        #登录验证
        user = authenticate(username=account, password=password)
        if user is not None:
            # 登录
            login(request, user)
            # 同步登录到论坛
            common_uc_user_synlogin(request, user, password)
            return HttpResponse('{"status":"success", "url":"'+source_url+'"}', content_type="application/json")
        else:
            # 如果主站未查询到对应的账号信息，则尝试从老网站验证用户登录信息，如果验证通过，则在新网站里面插入对应账号信息
            try:
                # 如果已有对应账号，则不需再去老网站验证
                UserProfile.objects.get(Q(email=account) | Q(mobile=account))
            except UserProfile.DoesNotExist:
                # 如果没有查询到对应账号则向老网站验证
                # http://www.maiziedu.com/services-api/app/reglogin.php?type=login&username=test&password=123456&client=ios
                try:
                    url = settings.OLD_SITE_URL+'/services-api/app/reglogin.php'
                    values = {'type':'login','username':account,'password':password}
                    data = urllib.urlencode(values)
                    req = urllib2.Request(url, data)
                    response = urllib2.urlopen(req, timeout=3)
                    result = json.loads(response.read())
                    # 通过老网站验证
                    if result['result'] == "true":
                        # 向新网站注册一个新的账号
                        common_register(request, account, password, "老网站")
                        # 注册成功之后立马登录
                        user = UserProfile.objects.get(username=account)
                        user.backend = 'mz_user.auth.CustomBackend'
                        login(request, user)
                        # 同步登录到论坛
                        common_uc_user_synlogin(request, user, password)
                        return HttpResponse('{"status":"success", "url":"'+source_url+'"}', content_type="application/json")
                except Exception,e:
                    logger.error(e)
            except Exception,e:
                logger.error(e)
            return HttpResponse('{"status":"failure"}', content_type="application/json")
    return HttpResponse(json.dumps(login_form.errors), content_type="application/json")

def user_logout(request):
    '''
    前台注销
    :param request:
    :return:
    '''
    try:
        logout(request)
        # 同步从论坛登出
        uc_user_synlogout(request)
    except Exception as e:
        logger.error(e)
    return HttpResponseRedirect(reverse('index_front'))

# 判断该进哪个用户中心
def user_center(request):
    if request.user.is_authenticated():
        if request.user.is_student():
            response = HttpResponseRedirect("/user/student")
            response.set_cookie("is_jump",1)
            response.set_cookie("f_number",False)
        else:
            response = HttpResponseRedirect("/user/teacher")
            response.set_cookie("is_jump",1)
            response.set_cookie("f_number",False)
        return response
    else:
        return render(request, 'mz_common/failure.html',{'reason':'请先登录再进入个人中心。'})

def email_register(request):
    '''
    邮件注册账号表单
    :param request:
    :return:
    '''
    register_form = EmailRegisterForm(request.POST)
    if register_form.is_valid():
        #获取表单信息
        password = register_form.cleaned_data["password"]
        email = register_form.cleaned_data["email"]
        common_register(request, email, password, "新网站")
        #发送注册激活邮件
        do_send_mail(email, request.META['REMOTE_ADDR'], 0)
    return HttpResponse(json.dumps(register_form.errors), content_type="application/json")

def mobile_register(request):
    '''
    手机注册账号表单
    :param request:
    :return:
    '''
    register_form = MobileRegisterForm(request.POST)
    if register_form.is_valid():
        #获取表单信息
        password = register_form.cleaned_data["password_m"]
        mobile = register_form.cleaned_data["mobile"]
        common_register(request, mobile, password, "新网站")
    return HttpResponse(json.dumps(register_form.errors), content_type="application/json")

def common_register(request, account, password, source):
    #将注册信息写入数据库
    user = UserProfile()
    user.username = account
    user.password = make_password(password)
    if re.compile(settings.REGEX_EMAIL).match(account):
        user.email = account
        # 查询nick_name是否已经存在
        nick_name = account.split("@")[0]
        nick_name_count = UserProfile.objects.filter(nick_name__icontains=nick_name).count()
        if nick_name_count > 0:
            nick_name = str(nick_name) + "_" + str(nick_name_count)
        user.nick_name = nick_name
    elif re.compile(settings.REGEX_MOBILE).match(account):
        user.mobile = account
        user.nick_name = account
        user.valid_mobile = 1
    try:
        user.register_way = RegisterWay.objects.get(name__iexact = source)
    except RegisterWay.DoesNotExist:
        user.register_way_id = 1
    #注册信息同步到ucenter
    uc_reg_result = uc_user_register(request, user.nick_name, password, account)
    if int(uc_reg_result) > 0:
        user.uid = uc_reg_result
    user.save()
    # 设置用户默认学生分组
    try:
        group = Group.objects.get(name="学生")
        group.user_set.add(user)
    except Exception,e:
        logger.error(e)

    return user

def find_password(request):
    findpassword_form = FindPasswordForm(request.POST)
    if findpassword_form.is_valid():
        #获取表单信息
        account = findpassword_form.cleaned_data["account"]
        #判断账号是邮箱还是手机号
        if re.compile(settings.REGEX_MOBILE).match(account):
            #手机则发送短信并进入短信验证界面
            result = do_send_sms(account, request.META['REMOTE_ADDR'], 1)
            return HttpResponse(result, content_type="application/json")
        elif re.compile(settings.REGEX_EMAIL).match(account):
            #发送找回密码邮件
            do_send_mail(account, request.META['REMOTE_ADDR'], 1)

    return HttpResponse(json.dumps(findpassword_form.errors), content_type="application/json")

def find_password_mobile_code(request):
    '''
    手机注册账号表单
    :param request:
    :return:
    '''
    find_password_mobile_form = FindPasswordMobileForm(request.POST)
    if find_password_mobile_form.is_valid():
        #获取表单信息
        return HttpResponse('{"status":"success"}', content_type="application/json")
    return HttpResponse(json.dumps(find_password_mobile_form.errors), content_type="application/json")

def reset_password(request, account, code):

    '''
    重置密码
    :param request:
    :param email: 邮箱或手机账号
    :param code: 随机码
    :return:
    '''
    if re.compile(settings.REGEX_MOBILE).match(account):
        #手机则发送短信并进入短信验证界面
        record = MobileVerifyRecord.objects.filter(Q(mobile=account), Q(code=code), Q(type=1)).order_by("-created")
        if record:
            if datetime.now()-timedelta(minutes=30) > record[0].created:
                return render(request, 'mz_common/failure.html',{'reason':'手机验证码已经过期，请到重新发送手机验证码'})
        else:
            return render(request, 'mz_common/failure.html',{'reason':'找回密码信息错误，无法找回'})
    else:
        account = base64.b64decode(account)
        if re.compile(settings.REGEX_EMAIL).match(account):
            #发送找回密码邮件
            record = EmailVerifyRecord.objects.filter(Q(email=account), Q(code=code), Q(type=1)).order_by("-created")
            if record:
                if datetime.now()-timedelta(days=1) > record[0].created:
                    return render(request, 'mz_common/failure.html',{'reason':'找回密码链接已经过期，请到重新发送找回密码邮件'})
            else:
                return render(request, 'mz_common/failure.html',{'reason':'找回密码信息错误，无法找回'})

    #设置session临时保存通过验证的account信息
    request.session['reset_account'] = account
    #跳转到密码重置界面
    return HttpResponseRedirect(reverse('user:update_reset_password_view'))

#密码重置界面
def update_reset_password_view(request):
    update_password_form = UpdatePasswordForm()
    return render(request, 'mz_user/reset_password.html',locals())

# 密码重置Ajax处理
def update_reset_password(request):
    update_password_form = UpdatePasswordForm(request.POST)
    if update_password_form.is_valid():
        password = make_password(update_password_form.cleaned_data['password'])
        #从服务端获取对应的账号
        account = request.session['reset_account']
        try:
            user = UserProfile.objects.get(Q(email=account) | Q(mobile=account))
            user.password = password
            user.save()
            return HttpResponse('{"status":"success"}', content_type="application/json")
        except UserProfile.DoesNotExist:
            return HttpResponse('{"status":"failure"}', content_type="application/json")
    return HttpResponse(json.dumps(update_password_form.errors), content_type="application/json")

def send_sms_code(request):
    '''
    发送手机验证码ajax请求方法
    :param request:
    :return:
    '''
    mobile = request.POST["mobile"]
    error_message=""
    #检验手机号码格式
    if mobile == "":
        error_message = '{ "mobile":"请输入手机号" }'
    else:
        p=re.compile(settings.REGEX_MOBILE)
        if not p.match(mobile):
            error_message = '{ "mobile":"注册账号需为手机格式" }'
        elif UserProfile.objects.filter(mobile=mobile).count() > 0:
            #检验该手机号是否注册
            error_message = '{ "mobile":"该账号已被注册" }'

    if error_message != "":
        return HttpResponse(error_message, content_type="application/json")
        #发送短信
    result = do_send_sms(mobile, request.META['REMOTE_ADDR'], 0)
    return HttpResponse(result, content_type="application/json")

def do_send_sms(mobile, ip, type=0):
    '''
    生成短信发送记录并发送手机验证码
    :param request:
    :param mobile:
    :return:
    '''

    #查询同IP是否超出最大短信数量发送限制
    start = datetime.now() - timedelta(hours=23, minutes=59, seconds=59)
    send_count=MobileVerifyRecord.objects.filter(Q(ip=ip),Q(created__gt = start)).count()
    if send_count > settings.SMS_COUNT:
        return '{"status":"failure","mobile": "该IP超过当日短信发送限制数量"}'
    #生成激活码
    random_str = generate_random(6, 0)
    #邮件发送记录写入数据库
    mobile_record = MobileVerifyRecord()
    mobile_record.code = random_str
    mobile_record.mobile = mobile
    mobile_record.type = type
    mobile_record.ip = ip
    mobile_record.save()

    #发送短信
    apikey = settings.SMS_APIKEY
    tpl_id = settings.SMS_TPL_ID  #短信模板ID
    tpl_value = '#code#=%(code)s&#company#=%(company)s' % {'code': random_str, 'company':settings.SMS_COMPANY}
    try:
        result=json.loads(tpl_send_sms(apikey, tpl_id, tpl_value, mobile))
        if(result['code'] == 0):
            result='{"status":"success"}'
        else:
            result='{"status":"failure"}'
        return result
    except Exception,e:
        logger.error(e)

def do_send_mail(email, ip, type=0):

    '''
    生成邮件发送记录并发送注册激活邮件
    :param request:
    :param email:目标邮箱地址
    :param type:邮件类型（0：注册激活邮件；1：找回密码邮件）
    :return:
    '''

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
    email_record.type = type
    email_record.ip = ip
    email_record.save()

    #发送验证邮件
    email_title=email_body=""
    if type == 0:
        email_title = settings.EMAIL_SUBJECT_PREFIX + "注册账号激活邮件"
        email_body = """欢迎使用麦子学院账号激活功能 \r\n
请点击链接激活账号：\r
%(site_url)s/user/active/%(email)s/%(random_str)s \r\n
(该链接在24小时内有效)  \r
如果上面不是链接形式，请将地址复制到您的浏览器(例如IE)的地址栏再访问。 \r
        """ % {'site_url': settings.SITE_URL, 'email': base64.b64encode(email), 'random_str': random_str}
    elif type == 1:
        email_title = settings.EMAIL_SUBJECT_PREFIX + "找回密码邮件"
        email_body = """欢迎使用麦子学院找回密码功能 \r\n
请点击链接重置密码：\r
%(site_url)s/user/password/reset/%(email)s/%(random_str)s \r\n
(该链接在24小时内有效)  \r
如果上面不是链接形式，请将地址复制到您的浏览器(例如IE)的地址栏再访问。 \r
        """ % {'site_url': settings.SITE_URL, 'email': base64.b64encode(email), 'random_str': random_str}

    try:
        return send_mail(email_title, email_body, settings.EMAIL_FROM, [email])
    except Exception,e:
        logger.error(e)

def do_active(request, email, code):
    '''
    邮箱激活
    :param request:
    :param code:激活码
    :return:
    '''
    #验证激活码是否正确或过期
    email = base64.b64decode(email)
    try:
        user = UserProfile.objects.get(email__iexact=email)
        if user.valid_email == 0:
            record = EmailVerifyRecord.objects.filter(email__iexact=email, code__exact=code, type=0).order_by("-created")
            if record:
                if datetime.now()-timedelta(days=1) > record[0].created:
                    return render(request, 'mz_common/failure.html',{'reason':'激活链接已经过期，请到个人中心再次发送激活邮件'})
                # 改变账号状态
                user.valid_email = 1
                # 如果用户的uid为空，则进行相关绑定操作
                if user.uid is None:
                    #通过验证了之后查询ucenter是否有一样的邮箱账号，如有则进行绑定，没有则创建新的ucenter账号
                    uc_user_info = uc_get_user(request, user.nick_name)
                    if uc_user_info != 0:
                        if uc_user_info[0] > 0 and uc_user_info[2] == user.email:
                            user.uid = uc_user_info[0]
                    else:
                        uc_reg_result = uc_user_register(request, user.nick_name, user.password, user.email)
                        if int(uc_reg_result) > 0:
                            user.uid = uc_reg_result
                user.save()
                # 同步登录到论坛
                uc_user_synlogin(request, uid=user.uid)
            else:
                return render(request, 'mz_common/failure.html',{'reason':'激活信息错误，无法激活'})
        else:
            return render(request, 'mz_common/failure.html',{'reason':'该邮箱已经被激活'})
        return render(request, 'mz_common/success.html',{'reason':'邮箱激活成功'})
    except UserProfile.DoesNotExist:
        return render(request, 'mz_common/failure.html',{'reason':'无此用户'})

# 学生用户中心公用变量
@student_required
def student_common(request):
    # 获取章节学习总时间
    mylesson_time=request.user.mylesson.extra(select={'sum': 'sum(video_length)'}).values('sum')[0]['sum']
    if mylesson_time != None:
        mylesson_time = second_to_time(mylesson_time)
    else:
        mylesson_time = "0小时"
        # 获取课程总数
    mycourse_count = MyCourse.objects.filter(user = request.user).extra(select={'count': 'count(course)'}).values('count')[0]['count']

    locals={"mylesson_time":mylesson_time,"mycourse_count":mycourse_count}

    return locals

# 我的课程
@student_required
def student_mycourse_view(request):
    common_val = student_common(request)

    #获取高校课程列表
    academic_courses = AcademicUser.objects.filter(user= request.user).order_by("-id")
    academic_course_list=[]
    course_list=[]
    for course in academic_courses:
        try:
            academic_course = AcademicCourse.objects.get(pk=course.academic_course)
        except AcademicCourse.DoesNotExist:
            continue
            #根据职业课程找到对应的班级,计算班级排名未完成
        curren_stu_ranking = current_user_ranking(academic_course, request.user)
        if curren_stu_ranking !="NotSignUp":
            all_stu = all_stu_ranking(academic_course,request.user)
            setattr(academic_course, "cur_ranking", int(curren_stu_ranking))
            setattr(academic_course, "stu_count", len(all_stu))
        else:
            setattr(academic_course, "cur_ranking","NotSignUp")
        academic_course_list.append(academic_course)


    # 获取职业课程列表
    mycourses = MyCourse.objects.filter(user = request.user).order_by("index","-id")
    career_course_list=[]
    course_list=[]
    for course in mycourses:
        if course.course_type == 2 :
            try:
                career_course = CareerCourse.objects.get(pk=course.course)
                #Add by Steven YU,已经添加到高校专区的，就不在这里显示
                if career_course.course_scope is not None:
                    continue

            except CareerCourse.DoesNotExist:
                continue
            #根据职业课程找到对应的班级,计算班级排名未完成
            curren_stu_ranking = current_user_ranking(career_course,request.user)
            if curren_stu_ranking !="NotSignUp":
                all_stu = all_stu_ranking(career_course,request.user)
                setattr(career_course, "cur_ranking", int(curren_stu_ranking))
                setattr(career_course, "stu_count", len(all_stu))
            else:
                setattr(career_course, "cur_ranking","NotSignUp")
            career_course_list.append(career_course)
        elif course.course_type == 1:
            try:
                course = Course.objects.get(pk=course.course)
            except Course.DoesNotExist:
                continue
            # 最近观看的章节
            setattr(course, "recent_learned_lesson", "还未观看过该课程")
            recent_learned_lesson = get_recent_learned_lesson(request.user, course)
            if recent_learned_lesson != None:
                course.recent_learned_lesson = "最近观看《"+str(recent_learned_lesson.lesson.name)+"》"
            course_list.append(course)
    return render(request, 'mz_user/student_mycourse_view.html',locals())

# 我的收藏
@student_required
def student_myfavorite_view(request):
    common_val = student_common(request)
    favorited_courses = MyFavorite.objects.filter(user=request.user).order_by("-date_favorite")
    current_page = int(request.GET.get('page', '1'))
    pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(favorited_courses,current_page,settings.COURSE_LIST_PAGESIZE)
    course_list=[]
    for favorite in pl:
        # 最近观看的章节
        setattr(favorite.course, "recent_learned_lesson", "还未观看过该课程")
        recent_learned_lesson = get_recent_learned_lesson(request.user, favorite.course)
        if recent_learned_lesson != None:
            favorite.course.recent_learned_lesson = "最近观看《"+str(recent_learned_lesson.lesson.name)+"》"
        course_list.append(favorite.course)
    return render(request, 'mz_user/student_myfavorite_view.html',locals())

# 我的证书
@student_required
def student_mycertificate_view(request):
    common_val = student_common(request)
    certificate_list = request.user.certificate.all()
    current_page = int(request.GET.get('page', '1'))
    pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(certificate_list,current_page,settings.COURSE_LIST_PAGESIZE)
    return render(request, 'mz_user/student_mycertificate_view.html',locals())

# 证书下载
@student_required
def student_mycertificate_download(request,certificate_id):
    # 根据证书ID获取证书图片路径
    certificate = Certificate.objects.get(pk=certificate_id)
    filename = settings.SITE_URL+settings.MEDIA_URL+str(certificate.image_url)
    f = urllib2.urlopen(filename, timeout=3)
    data = f.read()
    f.close()

    # 以证书名称作为下载名称
    filename = "certificate_"+str(certificate.id)+"."+str(certificate.image_url).split(".")[-1]
    response = HttpResponse(data, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=%s' % filename
    return response

# 用户的消息
@login_required(login_url="/")
def user_mymessage_view(request):
    common_val = student_common(request)
    message_list_tmp = MyMessage.objects.filter(Q(userB = request.user.id) | Q(userB = 0,action_type = 1)).order_by("-date_action")
    current_page = int(request.GET.get('page', '1'))
    pn,pt,pl,pp,np,ppn,npn,cp,pr = instance_pager(message_list_tmp,current_page,settings.MYMESSAGE_PAGESIZE)
    message_list = []
    for message in pl :
        #将消息设置为已读
        message.is_new = False
        message.date_action = message.date_action
        message.save()
        #根据需要取出对应信息
        if message.userA != 0 and message.userA != None:
            userA = UserProfile.objects.filter(pk=message.userA)[:1]
            message.userA = userA[0] if userA else ''
        if message.action_type == "2" :
            #课程
            action_id = Lesson.objects.filter(pk=message.action_id)[:1]
            message.action_id = action_id[0] if action_id else ''
        if message.action_type == "3" :
            #替换内容中的链接地址
            hyperlink_pat = re.compile(r'<\s*[Aa]{1}\s+[^>]*?[Hh][Rr][Ee][Ff]\s*=\s*[\"\']?([^>\"\']+)[\"\']?.*?>')
            comment_pat = re.compile(r'<!--(.*?)-->')
            html_source = comment_pat.sub('', message.action_content)
            match_links = hyperlink_pat.findall(html_source)
            for links in match_links:
                links_new = links.replace(links,settings.BBS_SITE_URL+"/"+links)
                message.action_content = message.action_content.replace(links,links_new)
        message_list.append(message)
    return render(request, 'mz_user/user_mymessage_view.html',locals())

# 老师班级中心
@teacher_required
def teacher_myclass_view(request):
    # 获取老师课程列表
    try:
        user= request.user
        if user.is_academic_teacher():
            ac_user = AcademicUser.objects.get(user = user)
            school = ac_user.owner_college
            acourse = AcademicCourse.objects.filter(owner=school)
            for course in acourse:
                classobj = AcademicClass.objects.get(career_course_id=course.id)
                setattr(course, "class_id",classobj.id)
            return render(request, 'mz_user/school_teacher_view.html', locals())
        else:
            classing = Class.objects.filter(teacher = request.user,status = 1,is_active = True).annotate(num_students=Count('students'))
            classfinish = Class.objects.filter(teacher = request.user,status = 2,is_active = True).annotate(num_students=Count('students'))
            return render(request, 'mz_user/teacher_myclass_view.html', locals())
    except Exception as e:
        logger.error(e)
    return HttpResponse("failure", content_type="text/plain")

# 个人资料 - 头像裁切
@login_required(login_url="/")
def avatar_crop(request):

    marginTop=0
    marginLeft=0
    width=0
    height=0
    picheight=0
    picwidth=0

    if request.GET.get('marginTop'):
        marginTop=int(request.GET.get('marginTop'))
    if request.GET.get('marginLeft'):
        marginLeft=int(request.GET.get('marginLeft'))
    if request.GET.get('width'):
        width=int(request.GET.get('width'))
    if request.GET.get('height'):
        height=int(request.GET.get('height'))
    if request.GET.get('picheight'):
        picheight=int(request.GET.get('picheight'))
    if request.GET.get('picwidth'):
        picwidth=int(request.GET.get('picwidth'))

    #裁切
    avatar_up_small = "" #upload Thumbnail
    avatar_target_path = ""
    avatar_middle_target_path = ""
    avatar_small_target_path = ""
    try:
        # 获取头像临时图片名称
        avatar_tmp = request.session.get("avatar_tmp",None)
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
    except Exception,e:
        logger.error(e)

    # 将裁切后的图片路径信息更新图片字段
    request.user.avatar_url = avatar_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    request.user.avatar_middle_thumbnall = avatar_middle_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    request.user.avatar_small_thumbnall = avatar_small_target_path.split("..")[-1].replace('/uploads','').replace('\\','/')[1:]
    request.user.save()

    if request.user.uid:
        sync_avatar(request.user.uid, avatar_target_path)

    return HttpResponse('{"status":"success"}', content_type="application/json")


def sync_avatar(forum_uid, big):
    import shutil

    root_path = settings.PROJECT_ROOT
    filename, extension = os.path.splitext(big)
    filename = filename.split("../")[-1]
    pure_name = '_'.join(filename.split('_')[:-1])

    forum_uid = "%09d" % forum_uid
    dir1 = forum_uid[0:3]
    dir2 = forum_uid[3:5]
    dir3 = forum_uid[5:7]
    prefix = forum_uid[-2:]

    for size in ('big', 'middle', 'small'):
        main_avatar_path = root_path + "/" + pure_name + '_' + size + extension

        forum_avatar_dir_path = root_path + '/forum/uc_server/data/avatar/' + dir1 + '/' + dir2 + '/' + dir3

        if not os.path.exists(forum_avatar_dir_path):
            os.makedirs(forum_avatar_dir_path)

        avatar_name = prefix + '_avatar_' + size + extension
        forum_avatar_path = forum_avatar_dir_path + '/' + avatar_name
        if os.path.exists(forum_avatar_path):
            os.remove(forum_avatar_path)

        shutil.copyfile(main_avatar_path, forum_avatar_path)

# 个人资料 - 头像上传
@csrf_exempt
@login_required(login_url="/")
def avatar_upload(request):
    ret="0"
    file = request.FILES.get("Filedata",None)
    if file:
        result =_upload(file)
        if result:
            if result[0] == True:
                ret='{"status":"success","filename":"'+str(result[1])+'","width":'+str(result[2])+',"height":'+str(result[3])+'}'
            else:
                ret='{"status":"failure","message":"'+str(result[1])+'"}'
                #头像上传成功，则暂时保存头像名称的session
            request.session['avatar_tmp'] = result[1]
    return HttpResponse(ret, content_type="text/plain")

#头像图片上传
def _upload(file):
    '''''图片上传函数'''
    if file:
        if file.size / 1024 > settings.AVATAR_SIZE_LIMIT :
            return (False,"头像大小超过"+str(settings.AVATAR_SIZE_LIMIT)+"KB限制")
            # 判断图片格式
        if settings.AVATAR_SUFFIX_LIMIT.find(file.name.split(".")[-1]) == -1 :
            return (False,"头像必须为GIF/JPG/PNG/BMP格式")
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
            return (False,"头像上传失败")
        return (True,file_name, width, height)
    return (False,"头像上传失败")

# 用户的个人资料
@login_required(login_url="/")
def user_myinfo_view(request):
    common_val = student_common(request)
    changeform = ChangePassword(request.POST)
    user = request.user
    update_mobile_form = UpdateMobileForm({'mobile_um':user.mobile,'uid_um':user.id})
    update_email_form = UpdateEmailForm({'email_ue':user.email,'uid_ue':user.id})
    mobile_code_update_mobile_form = FindPasswordMobileForm()
    userform = UserInfoSave({'nick_name':user.nick_name,'position':user.position,'description':user.description,'qq':user.qq,'mobile':user.mobile,'email':user.email})
    return render(request, 'mz_user/user_myinfo_view.html',locals())

# 根据省份查城市
@login_required(login_url="/")
def city_list(request):
    provid = request.GET['provid']
    city_list = {}
    citys = CityDict.objects.filter(province = provid)
    for city in citys:
        city_list.setdefault("cityid", [ ]).append([city.id,city.name])
    return HttpResponse(json.dumps(city_list), content_type="application/json")

#用户信息保存
@login_required(login_url="/")
def user_info_save(request):
    try:
        userinfosave = UserInfoSave(request.POST)
        if userinfosave.is_valid():
           nick_name = userinfosave.cleaned_data["nick_name"]
           position = userinfosave.cleaned_data["position"]
           description = userinfosave.cleaned_data["description"]
           qq = userinfosave.cleaned_data["qq"]
           cityid = userinfosave.cleaned_data["city"]
           user = request.user
           user.nick_name = nick_name
           user.position = position
           user.city_id = cityid
           user.description = description
           user.qq = qq
           user.save()
           uc_user_edit(request, user.uid, user.nick_name, user.password, '', user.email)
    except IntegrityError:
        return HttpResponse('{"status":"昵称（姓名）不能重复"}', content_type="application/json")
    except Exception,e:
       logger.error(e)
       return HttpResponse('{"status":"操作失败，请稍后再试"}', content_type="application/json")
    return HttpResponse(json.dumps(userinfosave.errors), content_type="application/json")

# 个人资料保存 - 发送激活邮件
@login_required(login_url="/")
def user_info_email(request):
    email = request.POST["email"]
    error_message=""
    #检验手机号码格式
    if email == "":
        error_message = '{ "email":"请输入邮箱账号" }'
    else:
        p=re.compile(settings.REGEX_EMAIL)
        if not p.match(email):
            error_message = '{ "email":"邮箱账号格式不正确" }'
    if error_message != "":
        return HttpResponse(error_message, content_type="application/json")
    #发送激活邮件
    if do_send_mail(email, request.META['REMOTE_ADDR'], 0) == 1:
        result = '{"status":"success"}'
    else:
        result = '{"status":"failure"}'
    return HttpResponse(result, content_type="application/json")

# 个人资料 - 密码修改
@login_required(login_url="/")
def change_password(request):
    changeform = ChangePassword(request.POST)
    if changeform.is_valid():
        account = request.user.username
        original_pass = changeform.cleaned_data["original_pass"]
        pass1 = changeform.cleaned_data["newpass1"]
        user = authenticate(username=account, password=original_pass)
        if user is not None:
            request.user.password = make_password(pass1)
            request.user.save()
            uc_user_edit(request, user.uid, user.nick_name, user.password, pass1, user.email)
        else:
            error_message = '{ "error":"原密码不正确" }'
            return HttpResponse(error_message, content_type="application/json")
    return HttpResponse(json.dumps(changeform.errors), content_type="application/json")

# 个人资料 - 手机修改验证 - 短信发送
@login_required(login_url="/")
def user_update_mobile_sendsms(request):
    update_mobile_form = UpdateMobileForm(request.POST)
    if update_mobile_form.is_valid():
        #验证通过返回成功，发送短信并继续下一步
        mobile_um = update_mobile_form.cleaned_data["mobile_um"]
        request.session["new_update_mobile"] = mobile_um
        result = do_send_sms(mobile_um, request.META['REMOTE_ADDR'], 1)
        return HttpResponse(result, content_type="application/json")
    return HttpResponse(json.dumps(update_mobile_form.errors), content_type="application/json")

# 个人资料 - 手机修改验证 - 保存数据
@login_required(login_url="/")
def user_update_mobile(request):
    update_mobile_form = FindPasswordMobileForm(request.POST)
    if update_mobile_form.is_valid():
        try:
            request.user.mobile = request.session["new_update_mobile"]
            request.user.username = request.session["new_update_mobile"]
            request.user.valid_mobile = 1
            request.user.save()
            return HttpResponse('{"status":"success"}', content_type="application/json")
        except Exception,e:
            logger.error(e)
            return HttpResponse('{"status":"failure"}', content_type="application/json")
    return HttpResponse(json.dumps(update_mobile_form.errors), content_type="application/json")

# 个人资料 - 邮箱修改验证
@login_required(login_url="/")
def user_update_email(request):
    update_email_form = UpdateEmailForm(request.POST)
    if update_email_form.is_valid():
        email = update_email_form.cleaned_data["email_ue"]
        request.user.email = email
        request.user.username = email
        request.user.valid_email = 0
        request.user.save()
        uc_user_edit(request, request.user.uid, request.user.nick_name, request.user.password, '', email)
        result = do_send_mail(email, request.META['REMOTE_ADDR'], 0)
        if result == 1 :
            return HttpResponse('{"status":"success"}', content_type="application/json")
        else:
            return HttpResponse('{"status":"failure"}', content_type="application/json")
    return HttpResponse(json.dumps(update_email_form.errors), content_type="application/json")

#获取职业课程
@teacher_required
def get_careercourse(request):
    allcourse = CareerCourse.objects.filter(course_scope=None)
    json_str = [{"id":c.id,"name":c.name.strip(),"short":c.short_name.upper()} for c in allcourse ]
    return HttpResponse(json.dumps(json_str),content_type="application/json")


def create_class_save(request):
    classno =""
    qun = ""
    classno = request.POST['classno']
    qun = request.POST['qun']
    selectclass = request.POST['selectclass']
    se_year = request.POST['se_year']
    se_month = request.POST['se_month']
    se_day = request.POST['se_day']
    if qun =="":
    	message = '{"message":"QQ群不能为空"}'
    	return HttpResponse(message,content_type="application/json")
    is_true = Class.objects.filter(coding=classno)
    if is_true:
    	message = '{"message":"创建的班级号已经存在"}'
    	return HttpResponse(message,content_type="application/json")

    if classno != "" : #判断班级号是否存在
        createclass = Class()
        timedate = se_year+"-"+se_month+"-"+se_day
        createclass.coding = str(classno)
        createclass.qq = qun
        createclass.date_open = timedate
        createclass.teacher = request.user
        createclass.career_course_id = selectclass
        createclass.save()
        message = '{"message":"success"}'
    else:
        message = '{"message":"error"}'
    return HttpResponse(message,content_type="application/json")

###################### 移动端登录注册 开始 #######################################
def mobile_login_view(request):
    if request.user.is_authenticated():
        return render(request, 'mz_common/failure.html',{'reason':'已经登录，无须重复登录。<a href="javascript:history.go(-1)">返回</a>'})
    login_form = LoginForm()
    # 上一个页面请求地址
    source_url = request.META['HTTP_REFERER']
    return render(request, 'mz_user/mobile_login.html',locals())
def mobile_register_view(request):
    if request.user.is_authenticated():
        return render(request, 'mz_common/failure.html',{'reason':'已经登录，不能注册。<a href="javascript:history.go(-1)">返回</a>'})
    login_form = LoginForm()
    email_register_form = EmailRegisterForm()
    mobile_register_form = MobileRegisterForm()
    # 上一个页面请求地址
    source_url = request.GET.get("source_url", None)
    if source_url == None: source_url = settings.SITE_URL
    return render(request, 'mz_user/mobile_register.html',locals())
###################### 移动端登录注册 结束 #######################################

###################### ucenter 同步需要的代码 ####################################
def destory_ucsynlogin_session(request):
    try:
        del request.session['ucsynlogin']
    except Exception,e:
        logger.error(e)
    return HttpResponse("success")

# 同步注册信息到ucenter
def uc_user_register(request, username, password, email):
    client = ucenter.Client(request.META['HTTP_USER_AGENT'])
    return client.uc_user_register(username=username, password=password, email=email)

# 获取ucenter用户信息
def uc_get_user(request, username):
    client = ucenter.Client(request.META['HTTP_USER_AGENT'])
    return client.uc_user_get_user(username=username)

# 修改ucenter用户信息
def uc_user_edit(request, uid, username, oldpw, newpw, email):
    client = ucenter.Client(request.META['HTTP_USER_AGENT'])
    return client.uc_user_edit(uid=uid, username=username, oldpw=oldpw, newpw=newpw, email=email, ignoreoldpw=1)

# 同步登录到论坛
def uc_user_synlogin(request, uid):
    client = ucenter.Client(request.META['HTTP_USER_AGENT'])
    ucsynlogin = client.uc_user_synlogin(uid=uid)
    request.session['ucsynlogin'] = ucsynlogin

# 同步登出论坛
def uc_user_synlogout(request):
    client = ucenter.Client(request.META['HTTP_USER_AGENT'])
    ucsynlogin = client.uc_user_synlogout()
    request.session['ucsynlogin'] = ucsynlogin

# 同步登录到论坛
def common_uc_user_synlogin(request, user, password):
    # 同步登录到论坛
    try:
        if user.uid is None:
            # 如果用户邮箱不为空
            if user.email is not None:
                #uid为空的话获取ucenter对应的用户信息，如能查询到用户则进行绑定
                uc_user_info = uc_get_user(request, user.nick_name)
                print uc_user_info
                if uc_user_info != 0:
                    if uc_user_info[0] > 0 and uc_user_info[2] == user.email and user.valid_email == 1:
                        user.uid = uc_user_info[0]
                        user.save()
                else:
                    # 如登录时还没有查询到ucenter对应的账号，则创建新的ucenter账号
                    uc_reg_result = uc_user_register(request, user.nick_name, password, user.email)
                    if int(uc_reg_result) > 0:
                        user.uid = uc_reg_result
                        user.save()
        if user.uid is not None:
            # 同步登录到论坛
            uc_user_synlogin(request, uid=user.uid)
    except Exception,e:
        logger.error(e)

# 进入论坛前判断
def user_goto_bbs(request):
    # 判断用户是否有邮箱地址
    if request.user.email is not None and request.user.uid is not None:
        # 邮箱不为空则直接跳转到论坛地址
        return HttpResponseRedirect(settings.BBS_SITE_URL)
    else:
        # 如果邮箱不为空则提示用户完善邮箱信息，并跳转到新增邮箱界面
        return HttpResponseRedirect("/user/info?popemail=true")