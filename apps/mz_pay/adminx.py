# -*- coding: utf-8 -*-
import xadmin
from models import *

class UserPurchaseAdmin(object):
    list_display = ('user', 'pay_price','order_no','pay_type','date_add','pay_status','id')
    list_filter = ('pay_type', 'pay_way','pay_status')
    search_fields = ['order_no','trade_no','id']

xadmin.site.register(UserPurchase, UserPurchaseAdmin)
