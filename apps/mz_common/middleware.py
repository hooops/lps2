# -*- coding: utf-8 -*-

from django.http import HttpResponsePermanentRedirect
from django.core.urlresolvers import reverse
import re

class CheckBrowser(object):

    def process_request(self, request):
        try:
            agent = request.META.get('HTTP_USER_AGENT')
            p = re.findall('MSIE [678]\.0', agent)
            if len(p) > 0 and request.get_full_path().find("services-api/app") == -1:
                warning = request.META.get('PATH_INFO')
                war = re.findall('common/browser/warning/',warning)
                if len(war) == 0:
                    return HttpResponsePermanentRedirect('/common/browser/warning/')
        except  Exception as e:
            pass