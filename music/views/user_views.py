import json
import secrets
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.utils import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render

from music.models import Library, User


class UserViewController:
	GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
	GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
	GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

	@staticmethod
	def is_google_oauth_configured():
		return bool(
			getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
			and getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
			and getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "")
		)

	@staticmethod
	def is_google_email(email):
		return bool(email) and email.lower().endswith("@gmail.com")

	@staticmethod
	def build_unique_display_name(base_name):
		base = (base_name or "google-user").strip()
		if not base:
			base = "google-user"

		base = base[:240]
		candidate = base
		suffix = 1
		while User.objects.filter(display_name=candidate).exists():
			suffix += 1
			candidate = f"{base}-{suffix}"[:255]
		return candidate

	@staticmethod
	def exchange_code_for_token(code):
		payload = urlencode(
			{
				"code": code,
				"client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
				"client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
				"redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
				"grant_type": "authorization_code",
			}
		).encode("utf-8")
		request = Request(
			url=UserViewController.GOOGLE_TOKEN_URL,
			data=payload,
			headers={"Content-Type": "application/x-www-form-urlencoded"},
			method="POST",
		)

		try:
			with urlopen(request, timeout=10) as response:
				raw = response.read().decode("utf-8")
		except HTTPError as exc:
			detail = ""
			try:
				detail = exc.read().decode("utf-8")
			except Exception:
				detail = ""
			raise ValueError(f"Google token exchange failed: {detail or exc.code}") from exc
		except URLError as exc:
			raise ValueError(f"Google token exchange failed: {exc.reason}") from exc

		try:
			token_data = json.loads(raw)
		except json.JSONDecodeError as exc:
			raise ValueError("Google token response is not valid JSON.") from exc

		if not token_data.get("access_token"):
			raise ValueError("Google token response missing access token.")
		return token_data

	@staticmethod
	def fetch_google_user_profile(access_token):
		request = Request(
			url=UserViewController.GOOGLE_USERINFO_URL,
			headers={"Authorization": f"Bearer {access_token}"},
			method="GET",
		)

		try:
			with urlopen(request, timeout=10) as response:
				raw = response.read().decode("utf-8")
		except HTTPError as exc:
			detail = ""
			try:
				detail = exc.read().decode("utf-8")
			except Exception:
				detail = ""
			raise ValueError(f"Google user info request failed: {detail or exc.code}") from exc
		except URLError as exc:
			raise ValueError(f"Google user info request failed: {exc.reason}") from exc

		try:
			profile = json.loads(raw)
		except json.JSONDecodeError as exc:
			raise ValueError("Google user info response is not valid JSON.") from exc
		return profile

	@staticmethod
	def find_or_create_google_user(profile):
		email = (profile.get("email") or "").strip().lower()
		if not email:
			raise ValueError("Google account did not provide an email.")
		if not profile.get("email_verified"):
			raise ValueError("Google email is not verified.")

		user = User.objects.filter(email=email).first()
		if user:
			return user

		name_hint = profile.get("name") or profile.get("given_name") or email.split("@")[0]
		display_name = UserViewController.build_unique_display_name(name_hint)
		return UserViewController.create_user(
			display_name=display_name,
			email=email,
			password=secrets.token_urlsafe(24),
		)

	@staticmethod
	def get_active_user(request):
		user_id = request.session.get("active_user_id")
		if not user_id:
			return None
		try:
			return User.objects.get(pk=user_id)
		except User.DoesNotExist:
			return None

	@staticmethod
	def login_template_view(request):
		active_user = UserViewController.get_active_user(request)

		# Manual POST login is disabled to enforce Google OAuth.
		if request.method == "POST":
			messages.error(request, "Manual sign-in is disabled. Please use Google Auth.")
			return HttpResponseRedirect("/login/")

		return render(
			request,
			"music/LoginTemplate.html",
			{
				"active_user": active_user,
				"google_oauth_configured": UserViewController.is_google_oauth_configured(),
			},
		)

	@staticmethod
	def google_login_start_view(request):
		if not UserViewController.is_google_oauth_configured():
			messages.error(request, "Google OAuth is not configured yet.")
			return HttpResponseRedirect("/login/")

		state = secrets.token_urlsafe(32)
		request.session["google_oauth_state"] = state

		query = urlencode(
			{
				"client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
				"redirect_uri": settings.GOOGLE_OAUTH_REDIRECT_URI,
				"response_type": "code",
				"scope": "openid email profile",
				"state": state,
				"prompt": "select_account",
			}
		)
		return HttpResponseRedirect(f"{UserViewController.GOOGLE_AUTH_URL}?{query}")

	@staticmethod
	def google_login_callback_view(request):
		error = request.GET.get("error")
		if error:
			messages.error(request, f"Google login failed: {error}")
			return HttpResponseRedirect("/login/")

		received_state = request.GET.get("state")
		expected_state = request.session.pop("google_oauth_state", None)
		if not received_state or not expected_state or received_state != expected_state:
			messages.error(request, "Invalid OAuth state. Please try again.")
			return HttpResponseRedirect("/login/")

		code = request.GET.get("code")
		if not code:
			messages.error(request, "Google OAuth callback missing code.")
			return HttpResponseRedirect("/login/")

		try:
			token_data = UserViewController.exchange_code_for_token(code)
			profile = UserViewController.fetch_google_user_profile(token_data["access_token"])
			user = UserViewController.find_or_create_google_user(profile)
		except ValueError as exc:
			messages.error(request, str(exc))
			return HttpResponseRedirect("/login/")

		request.session["active_user_id"] = user.pk
		messages.success(request, f"Logged in with Google as {user.display_name}.")
		return HttpResponseRedirect("/generate/")

	@staticmethod
	def logout_view(request):
		request.session.pop("active_user_id", None)
		request.session.pop("google_oauth_state", None)
		messages.success(request, "Logged out.")
		return HttpResponseRedirect("/login/")

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
