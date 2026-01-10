from django.urls import path
from . import views

urlpatterns = [
    # Template views
    path("", views.home, name="home"),
    path("create/", views.create_room_view, name="create_room"),
    path("rooms/<str:code>/", views.room_page, name="room"),
    
    # Room Management API
    path("api/rooms/create", views.api_create_room, name="api_create_room"),
    path("api/rooms/join", views.api_join_room, name="api_join_room"),
    path("api/rooms/<str:room_code>", views.api_get_room, name="api_get_room"),
    path("api/rooms/<str:room_code>/share", views.api_get_share_link, name="api_get_share_link"),
    
    # Message Operations API
    path("api/rooms/<str:room_code>/messages", views.api_get_messages, name="api_get_messages"),
    path("api/rooms/<str:room_code>/messages/react", views.api_react_message, name="api_react_message"),
    
    # Media Upload API
    path("api/upload/voice", views.api_upload_voice, name="api_upload_voice"),
    path("api/upload/image", views.api_upload_image, name="api_upload_image"),
    
    # Game Operations API
    path("api/games", views.api_list_games, name="api_list_games"),
    path("api/games/<str:game_id>", views.api_get_game, name="api_get_game"),
    path("api/rooms/<str:room_code>/game/start", views.api_start_game, name="api_start_game"),
]
