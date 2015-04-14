#!/usr/bin/env python
# -*- coding: utf-8 -*-

from functools import partial, wraps
from django.conf.urls import patterns, url

from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.exceptions import ObjectDoesNotExist


def intval(num):
    try:
        num = int(num)
        return num

    except Exception as e:
        return 0


def floatval(num):
    try:
        num = float(num)
        return num

    except Exception as e:
        return 0.0


def page_items(query_set, page_num, per_page=20):
    """ 普通的列表分页显示
        (QuerySet, int, int) -> [item]
    """

    paginator = Paginator(query_set, per_page)

    try:
        items = paginator.page(page_num)

    except PageNotAnInteger:
        items = paginator.page(1)

    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    return items


def get_or_none(Model, **kwargs):
    try:
        model = Model.objects.get(**kwargs)
        return model

    except ObjectDoesNotExist as e:
        return None


def get_or_create(Model, **kwargs):
    model = get_or_none(Model, **kwargs)

    if model == None:
        model = Model(**kwargs)
        model.save()

    return model


def authenticated(func):
    """给 login_required 绑定 nadmin 的 login_url"""

    # @TODO reverse 为何解析失败
    return login_required(login_url="/nadmin/login")(func)


class Route(object):
    """@TODO 解决 route 只能添加到最开始，
    可以将其他的 decor 作为参数传递"""

    prefix = r"nadmin"

    __url_parttens = []

    @classmethod
    def urls(cls):
        return cls.__url_parttens

    @classmethod
    def route(cls, url_regex="", name=""):

        def wraps(view_func):
            assert view_func != None, "view_func is None"

            url_partten = url(url_regex, view_func, name=name)
            cls.__url_parttens += patterns("", url_partten)

        return wraps


__all__ = ["intval", "page_items", "authenticated"]


