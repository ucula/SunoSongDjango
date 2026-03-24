from django.db import transaction

from music.models import Library, User


class UserController:
	@staticmethod
	@transaction.atomic
	def create_user(display_name, email=None, password=None, **extra_fields):
		user = User.objects.create_user(
			display_name=display_name,
			email=email,
			password=password,
			**extra_fields,
		)
		Library.objects.get_or_create(user=user)
		return user

	@staticmethod
	def get_user(user_id):
		return User.objects.select_related("library").get(pk=user_id)

	@staticmethod
	def get_user_by_display_name(display_name):
		return User.objects.select_related("library").get(display_name=display_name)

	@staticmethod
	def list_users():
		return User.objects.all().order_by("display_name")

	@staticmethod
	@transaction.atomic
	def update_user(user_id, **updates):
		user = User.objects.get(pk=user_id)
		for field, value in updates.items():
			if field == "password" and value:
				user.set_password(value)
			elif hasattr(user, field):
				setattr(user, field, value)
		user.save()
		return user

	@staticmethod
	@transaction.atomic
	def delete_user(user_id):
		user = User.objects.get(pk=user_id)
		user.delete()
		return True
