# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from mz_pay import views

urlpatterns = patterns('',
                       url(r'^go/(?P<careercourse_id>[\d]+)/(?P<stage_id>[\d]+)/(?P<buy_source>[^/]*)/(?P<source_id>[\d]+)/(?P<pay_type>[\d]{1})/(?P<class_coding>[^/]*)/$', views.goto_pay, name="goto_pay"),
                       url(r'^alipay/return/$', views.alipay_return,name="alipay_return"),
                       url(r'^alipay/notify/$', views.alipay_notify,name="alipay_notify"),
)