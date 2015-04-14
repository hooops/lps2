# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from django.views.generic import TemplateView
from django.conf import settings
from django.views.decorators.cache import cache_page
from mz_common import views

urlpatterns = patterns('',
  url(r'^course/list/$', views.index_course_ajax_page, name="index_course_ajax_page"),
  url(r'^terminal/$', views.terminal, name="terminal"),
  url(r'^recommend_keyword/$', cache_page(settings.CACHE_TIME)(views.recommend_keyword), name="recommend_keyword"),
  url(r'^course/search/$', views.course_search, name="course_search"),
  url(r'^terminal/$', views.terminal, name="terminal"),
  url(r'^apppage/$', views.apppage, name="apppage"),
  url(r'^mobile/search/$', views.mobile_search, name="mobile_search"),
  url(r'^newmessage/count/$', views.get_new_message_count, name="get_new_message_count"),
  url(r'^coupon/vlidate/$', views.coupon_vlidate, name="coupon_vlidate"),
  url(r'^browser/warning/$',  TemplateView.as_view(template_name="mz_common/browser_warning.html"), name="browser_warning"),
  url(r'^lps/demo/$',  TemplateView.as_view(template_name="mz_common/lps_demo.html"), name="lps_demo"),
  url(r'^ajax/careercourse_list/$', views.index_ajax_careercourse_list, name="index_ajax_careercourse_list"),
  url(r'^app_consult_info/add/$', views.app_consult_info_add, name="app_consult_info_add"),
  )