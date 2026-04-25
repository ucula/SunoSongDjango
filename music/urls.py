from django.urls import path

from .views import GeneratorViewController, LibraryViewController, UserViewController


urlpatterns = [
    path("", GeneratorViewController.gen_form_template_view, name="index"),
    path("login/", UserViewController.login_template_view, name="login-template"),
    path("login/google/", UserViewController.google_login_start_view, name="google-login-start"),
    path("login/google/callback/", UserViewController.google_login_callback_view, name="google-login-callback"),
    path("logout/", UserViewController.logout_view, name="logout"),
    path("generate/", GeneratorViewController.gen_form_template_view, name="gen-form-template"),
    path("generate/song/<int:gen_form_id>/", GeneratorViewController.generate_song_api_view, name="generate-song-api"),
    path("library/", LibraryViewController.library_template_view, name="library-template"),

    path("favourite/", LibraryViewController.favourite_template_view, name="favourite-template"),
]
