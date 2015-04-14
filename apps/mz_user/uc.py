# -*- coding=utf-8 -*-
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from mz_user.models import UserProfile, RegisterWay
from django.contrib.auth import login,logout
import ucenter, logging

logger = logging.getLogger('mz_user.uc')

@csrf_exempt
def uc_index(request):
    code = request.GET.get("code",None)
    api = MyUcenterAPI(request)
    result = "0"
    if code != None:
        result = api(code)
    return HttpResponse(result)

class MyUcenterAPI(ucenter.UcenterAPI):

    def __init__(self, request):
        self.request = request

    def do_test(self, **kwargs):
        return self.API_RETURN_SUCCEED

    def do_synlogin(self, **kwargs):
        # 根据论坛用户的uid查询到对应的主站用户
        try:
            user = UserProfile.objects.get(uid=kwargs['uid'])
            user.backend = 'mz_user.auth.CustomBackend'
            # 登录
            login(self.request, user)
        except Exception,e:
            print e
            logger.error(e)
            return self.API_INVALID
        return self.API_RETURN_SUCCEED

    def do_synlogout(self, **kwargs):
        try:
            logout(self.request)
        except Exception,e:
            logger.error(e)
            return self.API_INVALID
        return self.API_RETURN_SUCCEED