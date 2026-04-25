from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Favourite, GenForm, Library, Song, User


class FourDigitNumericPasswordValidator:
	def validate(self, password, user=None):
		if password is None:
			raise ValidationError("Password is required.")
		if len(password) != 4 or not password.isdigit():
			raise ValidationError("Password must be exactly 4 digits.")

	def get_help_text(self):
		return "Your password must be exactly 4 digits."


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ("user_id", "display_name", "email")
	search_fields = ("display_name", "email")
	ordering = ("user_id",)
	fieldsets = (
		("User", {"fields": ("display_name", "email")}),
	)
	readonly_fields = ("user_id",)


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
	list_display = ("id", "user")
	search_fields = ("user__display_name", "user__email")
	fieldsets = (("Library", {"fields": ("user",)}),)


@admin.register(GenForm)
class GenFormAdmin(admin.ModelAdmin):
	list_display = ("title", "mood_tone", "genre", "voice", "description")
	list_filter = ("voice", "genre")
	search_fields = ("title", "mood_tone", "genre", "description", "user__display_name", "user__email")
	fieldsets = (
		("Gen-form", {"fields": ("user", "title", "mood_tone", "genre", "voice", "description")}),
	)


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
	list_display = ("timestamp", "status", "e_rating", "title")
	list_filter = ("status", "e_rating")
	search_fields = ("title", "library__user__display_name", "library__user__email")
	fieldsets = (
		("Song", {"fields": ("library", "gen_form", "title", "status", "e_rating", "timestamp")}),
	)
	readonly_fields = ("timestamp",)


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
	list_display = ("id", "library", "song")
	search_fields = ("library__user__display_name", "song__title")
	fieldsets = (
		("Favourite", {"fields": ("library", "song")}),
	)
