# -*- coding: utf-8 -*-

from django.db import models
from datetime import datetime
from django.conf import settings
from mz_course.models import *
from mz_lps.models import Class

# 支付订单模型.
class UserPurchase(models.Model):

    user                    = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=u"用户")
    pay_price               = models.IntegerField(verbose_name=u"金额")
    order_no                = models.CharField(max_length=100, unique=True, verbose_name=u"订单号")
    trade_no                = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name=u"交易号")
    pay_type                = models.SmallIntegerField(choices=((0, u"全款"),(1, u"试学首付款"),(2, u"尾款"),(3,u"阶段款")), default=0, verbose_name=u"支付类型")
    date_add                = models.DateTimeField(default=datetime.now(), auto_now_add=True, verbose_name=u"下单时间")
    date_pay                = models.DateTimeField(null=True, blank=True, verbose_name=u"支付时间")
    pay_way                 = models.SmallIntegerField(choices=((1, u"网页支付宝"),(2, u"移动支付宝"),), verbose_name=u"支付方式")
    pay_status              = models.SmallIntegerField(null=True, blank=True, default=0, choices=((0, u"未支付"), (1, u"支付成功"),(2, u"支付失败"),), verbose_name=u"支付状态")
    pay_careercourse        = models.ForeignKey(CareerCourse, verbose_name=u"支付订单对应职业课程")
    pay_class               = models.ForeignKey(Class, verbose_name=u"支付订单对应班级号")
    pay_stage               = models.ManyToManyField(Stage, null=True, blank=True, verbose_name=u"支付订单对应阶段")
    coupon_code             = models.CharField(max_length=20,null=True, blank=True,verbose_name=u"优惠码")

    class Meta:
        verbose_name        = u"订单"
        verbose_name_plural = verbose_name