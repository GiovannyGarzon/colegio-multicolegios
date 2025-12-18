from django.contrib import admin
from .models import PublicPage, HomeBlock, NewsPost, SchoolPublicConfig, HomeHeroSlide, AboutSlide


@admin.register(AboutSlide)
class AboutSlideAdmin(admin.ModelAdmin):
    list_display = ("school", "order", "is_active")
    list_filter = ("school", "is_active")
    ordering = ("school", "order")

@admin.register(PublicPage)
class PublicPageAdmin(admin.ModelAdmin):
    list_display = ("school", "slug", "title", "is_active")
    list_filter = ("school", "slug", "is_active")
    search_fields = ("title", "subtitle", "content")

@admin.register(HomeBlock)
class HomeBlockAdmin(admin.ModelAdmin):
    list_display = ("school", "title", "order", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("title", "text")
    ordering = ("school", "order")

@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("school", "title", "published_at", "is_published")
    list_filter = ("school", "is_published")
    search_fields = ("title", "summary", "content")

@admin.register(SchoolPublicConfig)
class SchoolPublicConfigAdmin(admin.ModelAdmin):
    list_display = ("school", "whatsapp", "email_public")
    search_fields = ("school__name", "whatsapp", "email_public")

@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
    list_display = ("school", "order", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("school__name",)
    ordering = ("school", "order")