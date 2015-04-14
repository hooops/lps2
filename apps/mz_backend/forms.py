# -*- coding: utf-8 -*-
from django import forms

class UserForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "username"}), label='用户名：',max_length=100)
    password = forms.CharField(label='密码：',widget=forms.PasswordInput(attrs={"class": "pwd"}))