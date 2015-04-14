__author__ = 'admin'

from django import template
from django.template import Context, Template, loader, resolve_variable
import string

register=template.Library()

@register.tag(name='download_icon')
def download_icon(parser,token):
    try:
        tag_name,download_url=token.split_contents()
    except :
        raise template.TemplateSyntaxError(" tag  error!")
    return DownloadIcon(download_url)

class DownloadIcon(template.Node):
    def __init__(self,download_url):
        self.download_url=template.Variable(download_url)

    def render(self, context):
        return_str = ""
        down_url = self.download_url.resolve(context)
        str_url = down_url.storage.path(down_url.name)

        if str_url.lower().find(".rar") > 0 :
            return_str = "/static/images/doc/rar.png"
        elif str_url.lower().find(".zip") > 0 :
            return_str = "/static/images/doc/zip.png"
        elif str_url.lower().find(".pdf") > 0 :
            return_str = "/static/images/doc/pdf.png"
        else :
            return_str = "/static/images/doc/others.png"

        return return_str