from django.contrib import admin
from .models import Favorite, GenForm, Library, Song


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
	list_display = ("id", "user")


@admin.register(GenForm)
class GenFormAdmin(admin.ModelAdmin):
	list_display = ("id", "user", "title", "voice", "genre")
	list_filter = ("voice", "genre")
	search_fields = ("title", "mood_tone", "genre", "description", "user__username", "user__email")


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
	list_display = ("id", "title", "library", "status", "e_rating", "timestamp")
	list_filter = ("status", "e_rating")
	search_fields = ("title", "library__user__username", "library__user__email")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
	list_display = ("id", "library", "song")
	search_fields = ("library__user__username", "song__title")
