#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from functools import wraps, partial

from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404, get_list_or_404
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.contrib import messages, auth
from django.views.decorators.http import require_http_methods, require_GET, require_POST

from .forms import LoginForm
from .helper import intval, Route


route = Route.route
logger = logging.getLogger('mz_nadmin.views')


@route(url_regex=r"^login$", name="login")
@require_http_methods(["GET", "POST"])
def login(request):

    _render = partial(render, request, "mz_nadmin/login.html")

    if request.method == "GET":
        form = LoginForm()

        return _render({"form": form})

    else:
        form = LoginForm(request.POST)
        if not form.is_valid():
            return _render({"form": form})

        cleaned_data = form.cleaned_data

        username = cleaned_data["username"]
        password = cleaned_data["password"]

        user = auth.authenticate(username=username, password=password)

        if user == None:
            form.add_error("password", u"用户名或密码错误")
            return _render({"form": form})

        elif not user.is_active:
            form.add_error("username", u"用户没有激活")
            return _render({"form": form})

        elif user.groups.filter(name=u"后台编辑").count() <= 0:
            form.add_error("username", u"该用户没有相应的后台编辑权限")
            return _render({"form": form})

        else:
            auth.login(request, user)
            return HttpResponseRedirect(reverse("nadmin:home_page"))


@route(url_regex=r"^logout$", name="logout")
@require_GET
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse("nadmin:home_page"))


