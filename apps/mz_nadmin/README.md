### settings 文件添加

`TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates').replace('\\', '/'),
    os.path.join(PROJECT_ROOT, 'templates/mz_nadmin/'),
)`

> `STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static').replace('\\', '/'),
    os.path.join(PROJECT_ROOT, 'static/mz_nadmin').replace('\\', '/'),
)`

### maiziedu_website/urls.py 文件添加
`
url(r'^nadmin/', include('mz_nadmin.urls', namespace='nadmin')),
`


