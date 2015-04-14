# -*- coding: utf-8 -*-
__author__ = 'admin'

from django import template
from django.template import Context, Template, loader, resolve_variable
import string
from  datetime import *
import  time

register=template.Library()

@register.tag(name='date_convert')
def date_convert(parser,token):
    try:
        tag_name,format_string=token.split_contents()
    except :
        raise template.TemplateSyntaxError(" tag  error!")
    return DateConvert(format_string)

class DateConvert(template.Node):
    def __init__(self,format_string):
        self.format_string=template.Variable(format_string)
    def render(self, context):
    	times = self.format_string.resolve(context)
    	t = time.mktime(time.strptime(str(times), '%Y-%m-%d %H:%M:%S'))
    	tt= datetime.now() - times
    	if int(tt.days / 365 > 0):
    		return  str(int(tt.days / 365)) + '年前'
    	elif int(tt.days /30)  > 0:
    		return  str(int(tt.days / 30)  ) + '个月前'
    	elif int(tt.total_seconds() / 60 / 60 / 24) > 0:
    		return  str(int(tt.total_seconds() / 60 / 60 / 24)  ) + '天前'
    	elif int(tt.total_seconds() / 60 / 60 ) > 0:
    		return  str(int(tt.total_seconds() / 60 / 60 )  ) + '小时前'
    	elif int(tt.total_seconds() / 60 ) > 0:
    		return  str(int(tt.total_seconds() / 60)  ) + '分钟前'
    	elif int(tt.total_seconds()) <60 :
    		return  '刚刚'