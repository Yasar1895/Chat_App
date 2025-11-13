from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.lobby, name='lobby'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('rooms/create/', views.create_room, name='create_room'),
    path('rooms/<str:room_name>/', views.room_view, name='room'),
    path('rooms/<str:room_name>/upload/', views.upload_file, name='upload_file'),
    path('api/messages/<str:room_name>/', views.messages_api, name='messages_api'),  # pagination
]
