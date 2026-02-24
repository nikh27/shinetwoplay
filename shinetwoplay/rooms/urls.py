from django.urls import path
from django.views.generic import TemplateView
from . import views

urlpatterns = [
    # SEO & Discoverability
    path("robots.txt", TemplateView.as_view(template_name="seo/robots.txt", content_type="text/plain")),
    path("sitemap.xml", TemplateView.as_view(template_name="seo/sitemap.xml", content_type="application/xml")),
    path("shine2play/", TemplateView.as_view(template_name="seo/shine2play.html"), name="seo_shine2play"),
    path("stp/", TemplateView.as_view(template_name="seo/stp.html"), name="seo_stp"),
    path("s2p/", TemplateView.as_view(template_name="seo/s2p.html"), name="seo_s2p"),

    # Template views
    path("", views.home, name="home"),
    path("rooms/<str:room_code>/", views.room_page, name="room_page"),
    
    # Room Management API (Redis only)
    path("api/rooms/create/", views.api_create_room, name="api_create_room"),
    path("api/rooms/join/", views.api_join_room, name="api_join_room"),
    path("api/rooms/<str:room_code>/", views.api_get_room, name="api_get_room"),
    
    # Media Upload API
    path("api/upload/voice/", views.api_upload_voice, name="api_upload_voice"),
    path("api/upload/image/", views.api_upload_image, name="api_upload_image"),
    
    # Game Operations API (Database - static)
    path("api/games/", views.api_list_games, name="api_list_games"),
    path("api/games/<str:game_id>/", views.api_get_game, name="api_get_game"),
]
