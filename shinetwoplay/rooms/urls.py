from django.urls import path
from .views import home, create_room, room_page

urlpatterns = [
    path("", home),
    path("create-room/", create_room),
    path("rooms/<str:code>/", room_page),
    path("r/<str:code>/", room_page),
]
