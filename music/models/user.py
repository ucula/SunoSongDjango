from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
	use_in_migrations = True

	def create_user(self, display_name, email=None, password=None, **extra_fields):
		if email:
			email = self.normalize_email(email)
		user = self.model(display_name=display_name, email=email, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, display_name, email=None, password=None, **extra_fields):
		extra_fields.setdefault("is_staff", True)
		extra_fields.setdefault("is_superuser", True)
		extra_fields.setdefault("is_active", True)
		if extra_fields.get("is_staff") is not True:
			raise ValueError("Superuser must have is_staff=True.")
		if extra_fields.get("is_superuser") is not True:
			raise ValueError("Superuser must have is_superuser=True.")
		return self.create_user(display_name, email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
	user_id = models.BigAutoField(primary_key=True, editable=False)
	email = models.EmailField(unique=True, blank=True, null=True)
	display_name = models.CharField(max_length=255, unique=True)
	is_active = models.BooleanField(default=True)
	is_staff = models.BooleanField(default=False)
	date_joined = models.DateTimeField(auto_now_add=True)

	objects = UserManager()

	USERNAME_FIELD = "display_name"
	REQUIRED_FIELDS = []

	class Meta:
		verbose_name = "user"
		verbose_name_plural = "users"

	def __str__(self) -> str:
		return self.display_name or (self.email or "")