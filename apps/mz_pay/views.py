# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
from django.core.mail import send_mail
from utils.alipay import create_direct_pay_by_user, notify_verify
from utils.tool import generation_order_no
from mz_course.views import get_careercourse_total_price,get_careercourse_first_payment,get_careercourse_class, \
    get_careercourse_trystage_list,get_careercourse_balance_payment,get_careercourse_buybtn_status,\
    get_careercourse_lockstage_list, get_careercourse_allstage_list, is_unlock_in_stagelist, sys_send_message, \
    app_send_message
from mz_course.models import CareerCourse, Stage
from mz_lps.models import Class, ClassStudents
from mz_pay.models import UserPurchase
from mz_user.models import UserUnlockStage, MyCourse
import logging
from mz_common.views import *

logger = logging.getLogger('mz_pay.views')

@login_required(login_url="/")
def goto_pay(request, careercourse_id, stage_id, buy_source, source_id, pay_type, class_coding):
    '''
    服务端验证客户端支付数据，无误后跳转支付宝即时到账接口
    :param request:
    :return:
    '''
    try:
        # 获取应该支付的金额
        if request.user.is_authenticated() :
                # 获取优惠码
                code_sno = request.session.get('code_sno', None)
                money = request.session.get('money',None)
                # 得到当前职业课程对象
                cur_careercourse = CareerCourse.objects.get(pk=careercourse_id)
                # 判断当前班级是否已经达到人数上限student_limit、current_student_count
                cur_class = Class()
                if pay_type in ("0","1","3"):
                    # 判断该班级中是否已经有该学生
                    try:
                        cur_class = Class.objects.get(coding=class_coding)
                        if cur_class.students.filter(id=request.user.id).count() == 0:
                            if cur_class.current_student_count >= cur_class.student_limit :
                                return render(request, 'mz_common/failure.html',{'reason':'当前班级人数已经达到人数上限'})
                        # 判断用户是否已经在职业课程所属的其他某个班级
                        if ClassStudents.objects.filter(Q(user=request.user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class)).count() > 0:
                            class_students = ClassStudents.objects.get(Q(user=request.user), Q(student_class__career_course=cur_class.career_course), ~Q(student_class=cur_class))
                            return render(request, 'mz_common/failure.html',{'reason':'你已经加入该职业课程下的其他班级('+class_students.student_class.coding+')，不能重复加班'})
                    except Class.DoesNotExist:
                        logger.error("无此班级编号")

                # 需提交支付宝的参数
                order_no = generation_order_no()
                pay_amount = 0          # 支付金额
                pay_title = "职业课程：《"+cur_careercourse.name+"》"          # 支付名称
                pay_description = ""    # 支付描述
                # 需要解锁的阶段
                target_stage_list = []
                # 课程购买按钮的状态，0全款或首付款，1余款，2已经购买
                # pay_type 0 全额，1 试学首付款，2 尾款， 3 阶段款
                # 不以阶段方式购买
                if pay_type != "3" :
                    setattr(cur_careercourse, "buybtn_status", get_careercourse_buybtn_status(request.user, cur_careercourse))
                    if cur_careercourse.buybtn_status == 0 :
                        if pay_type == "0":
                            # 职业课程所有阶段ID列表
                            target_stage_list = get_careercourse_allstage_list(cur_careercourse)
                            # 全额
                            setattr(cur_careercourse, "total_price", get_careercourse_total_price(cur_careercourse))
                            pay_description="你现在正在支付《"+cur_careercourse.name+"》职业课程的全款,班级号："+class_coding
                            pay_amount = cur_careercourse.total_price
                            if code_sno is not None and money is not None:
                                pay_amount = int(pay_amount) - int(money)
                        elif pay_type == "1":
                            # 职业课程试学阶段ID列表
                            target_stage_list = get_careercourse_trystage_list(cur_careercourse)
                            # 试学首付
                            setattr(cur_careercourse, "first_payment", get_careercourse_first_payment(cur_careercourse))
                            pay_description="你现在正在支付《"+cur_careercourse.name+"》职业课程的首付款,班级号："+class_coding
                            pay_amount = cur_careercourse.first_payment
                    elif cur_careercourse.buybtn_status == 1 :
                        if pay_type == "2" :
                            # 职业课程未支付还处于解锁的所有阶段ID列表
                            target_stage_list = get_careercourse_lockstage_list(request.user, cur_careercourse)
                            #计算尾款应支付金额
                            setattr(cur_careercourse, "balance_payment", get_careercourse_balance_payment(request.user, cur_careercourse))
                            #用户当前所属该职业课程下的某个班级
                            setattr(cur_careercourse, "careercourse_class", get_careercourse_class(request.user, cur_careercourse))
                            class_coding=cur_careercourse.careercourse_class
                            cur_class = Class.objects.get(coding=class_coding)
                            pay_description="你现在正在支付《"+cur_careercourse.name+"》职业课程的余款,班级号："+class_coding
                            pay_amount = cur_careercourse.balance_payment
                    elif cur_careercourse.buybtn_status == 2:
                        return render(request, 'mz_common/failure.html',{'reason':'该职业课程已经完全解锁，不需再买'})
                    else:
                        return render(request, 'mz_common/failure.html',{'reason':'未知的购买状态'})
                else:
                    # 以阶段方式购买
                    buy_status = get_careercourse_buybtn_status(request.user, cur_careercourse)
                    if buy_status == 1 :
                        class_coding = get_careercourse_class(request.user, cur_careercourse)
                    stage = Stage.objects.get(pk=stage_id)
                    target_stage_list.append(stage.id)
                    pay_description="你现在正在支付《"+cur_careercourse.name+"》职业课程的《"+stage.name+"》阶段,班级号："+class_coding
                    pay_amount = stage.price

                #检查要支付的目标阶段是否已经解锁，如已解锁则提醒错误
                if is_unlock_in_stagelist(request.user, target_stage_list) :
                    return render(request, 'mz_common/failure.html',{'reason':'待购买的课程阶段中包含已经解锁的阶段，请联系管理员'})

                # 生成订单并存入到数据库
                purchase = UserPurchase()
                purchase.user = request.user
                purchase.pay_price = pay_amount
                purchase.order_no = order_no
                purchase.pay_type = pay_type
                purchase.pay_way = 1
                purchase.pay_status = 0
                purchase.pay_careercourse = cur_careercourse
                purchase.pay_class = cur_class
                purchase.save()
                purchase.pay_stage = Stage.objects.filter(id__in=target_stage_list)
                if code_sno is not None:
                    purchase.coupon_code = code_sno
                    request.session['code_sno'] = None
                    request.session['money'] = None
                purchase.save()
                extra_common_param = "'"+buy_source+","+source_id+"'"

                payurl = create_direct_pay_by_user(order_no, pay_title, pay_description, pay_amount, extra_common_param)
                return render(request, 'mz_pay/tips.html',{'payurl':payurl})
        else:
            return render(request, 'mz_common/failure.html',{'reason':'请先登录再进行支付'})
    except Exception as e:
        logger.error(e)
        print e
        return render(request, 'mz_common/failure.html',{'reason':'服务器繁忙，请稍后再试'})

@csrf_exempt
def alipay_notify(request):
    '''
    支付成功后异步通知处理
    :param request:
    :return:
    '''
    try:
        if request.method == 'POST':
            verify_result = notify_verify(request.POST) # 解码并验证数据是否有效
            if verify_result:
                order_no = request.POST.get('out_trade_no')
                trade_no = request.POST.get('trade_no')
                trade_status = request.POST.get('trade_status')
                result = order_handle(trade_status, order_no, trade_no)
                if result[0] == 'success':
                    return HttpResponse('success') #有效数据需要返回 'success' 给 alipay
    except Exception,e:
        logger.error(e)
    return HttpResponse('fail')

def alipay_return(request):
    '''
    支付成功后同步处理跳转告知用户
    :param request:
    :return:
    '''
    try:
        if request.method == 'GET':
            verify_result = notify_verify(request.GET) # 解码并验证数据是否有效
            if verify_result:
                order_no = request.GET.get('out_trade_no')
                trade_no = request.GET.get('trade_no')
                trade_status = request.GET.get('trade_status')
                extra_common_param = request.GET.get('extra_common_param').replace("'","")
                extra_common_param = extra_common_param.split(",")
                result = order_handle(trade_status, order_no, trade_no)
                if result[0] == "success":
                    if extra_common_param[0] == "course":
                        return HttpResponseRedirect("/course/"+str(extra_common_param[1])+"?b=true&qq="+str(result[1]))
                    elif extra_common_param[0] == "lesson":
                        return HttpResponseRedirect("/lesson/"+str(extra_common_param[1])+"?b=true&qq="+str(result[1]))
                    elif extra_common_param[0] == "learning_plan":
                        return HttpResponseRedirect("/lps/learning/plan/"+str(extra_common_param[1])+"?b=true&qq="+str(result[1]))
                    elif extra_common_param[0] == "stage":
                        return HttpResponseRedirect("/course/"+str(extra_common_param[1])+"/pay/other/?b=true&qq="+str(result[1]))
            else:
                return render(request, 'mz_common/failure.html',{'reason':'支付来源验证错误，请联系管理员'})
    except Exception,e:
        logger.error(e)

    return render(request, 'mz_common/failure.html',{'reason':'支付过程中出错，请联系管理员'})

# 根据支付宝返回结果处理解锁和订单结果
@transaction.commit_manually
def order_handle(trade_status, order_no, trade_no):
    try:
        # 根据商户订单号查询到对应订单信息
        purchase = UserPurchase.objects.get(order_no = order_no)
        if purchase.coupon_code:
            coupon = Coupon_Details.objects.get(code_sno=purchase.coupon_code)
            coupon_obj = Coupon.objects.get(id=coupon.coupon_id)
            coupon.user = purchase.user
            coupon.is_use = True
            coupon.use_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            coupon.save()
            coupon_obj.surplus = coupon_obj.surplus - 1
            coupon_obj.save()
        # 订单对应班级
        cur_class = Class.objects.get(coding=purchase.pay_class.coding)
        if purchase.pay_status == 1:
            transaction.rollback()
            return ("success", cur_class.qq)
        if trade_status in ('TRADE_FINISHED','TRADE_SUCCESS'):
            # 解锁相应的阶段
            # 获取该订单对应的阶段
            for stage in purchase.pay_stage.all() :
                try:
                    UserUnlockStage.objects.get(user=purchase.user, stage=stage)
                except UserUnlockStage.DoesNotExist:
                    unlock_stage = UserUnlockStage()
                    unlock_stage.user = purchase.user
                    unlock_stage.stage = stage
                    unlock_stage.save()
            #修改班级目前报名人数和更新学员到对应班级
            if cur_class.students.filter(pk=purchase.user.id).count() == 0:
                cur_class.current_student_count += 1
                cur_class.save()
                class_students = ClassStudents()
                class_students.student_class = cur_class
                class_students.user = purchase.user
                # 获取当前学力
                class_students.study_point = get_study_point(purchase.user, cur_class.career_course)
                class_students.save()

                #### 给学生发送通知消息 开始 ####

                # 发送站内信
                alert_msg = "恭喜你报名成功，请加入"+str(cur_class.coding)+"班QQ群"+str(cur_class.qq)+"开始和同学一起学习吧！"
                sys_send_message(0,purchase.user.id,1,alert_msg + "<a href='"+str(settings.SITE_URL)+"/lps/learning/plan/"+str(cur_class.career_course.id)+"'>进入课程LPS</a>")

                # 发送邮件
                if purchase.user.email is not None:
                    try:
                        send_mail(settings.EMAIL_SUBJECT_PREFIX + "班级报名成功邮件", alert_msg, settings.EMAIL_FROM, [purchase.user.email])
                    except Exception,e:
                        logger.error(e)

                # app推送
                app_send_message("系统消息", alert_msg, [purchase.user.token])

                #### 给学生发送通知消息 结束 ####

                #### 给对应带班老师发送通知消息 开始 ####
                alert_msg = "有新生报名了你的班级"+str(cur_class.coding)+"，<a href='"+str(settings.SITE_URL)+"/lps/user/teacher/class_manage/"+str(cur_class.id)+"/'>快去看看吧！</a>"
                sys_send_message(0,cur_class.teacher.id,1,alert_msg)

                alert_msg = "有新生报名了你的班级"+str(cur_class.coding)+"，快去看看吧！</a>"
                app_send_message("系统消息", alert_msg, [cur_class.teacher.token])
                #### 给对应带班老师发送通知消息 结束 ####

            #添加职业课程到我的课程
            if MyCourse.objects.filter(user=purchase.user, course=purchase.pay_careercourse.id, course_type=2).count() == 0 :
                my_course = MyCourse()
                my_course.user = purchase.user
                my_course.course = purchase.pay_careercourse.id
                my_course.course_type = 2
                my_course.index = 1
                my_course.save()

            # 改变该订单的状态
            purchase.trade_no = trade_no
            purchase.date_pay = datetime.now()
            purchase.pay_status = 1
            purchase.save()

            transaction.commit()
            return ("success", cur_class.qq)
        elif trade_status != "WAIT_BUYER_PAY":
            purchase.pay_status = 2
            purchase.save()
            transaction.commit()
    except Exception, e:
        logger.error(e)
        transaction.rollback()
    return ("fail","lose")
