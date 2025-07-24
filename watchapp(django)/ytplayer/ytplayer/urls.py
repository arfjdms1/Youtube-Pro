from django.contrib import admin
from django.urls import path
from player.views import index, watch_page, get_stream_data, proxy_stream

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('watch/', watch_page, name='watch'),
    path('stream/<str:video_id>/', get_stream_data, name='stream_data'),
    path('proxy/<path:url>/', proxy_stream, name='proxy_stream'),
]