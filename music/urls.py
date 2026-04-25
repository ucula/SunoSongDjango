from django.urls import path

from .views import GeneratorViewController, LibraryViewController, UserViewController


urlpatterns = [
    path("login/", UserViewController.login_template_view, name="login-template"),
    path("generate/", GeneratorViewController.gen_form_template_view, name="gen-form-template"),
    path("library/", LibraryViewController.library_template_view, name="library-template"),
    path("song/", LibraryViewController.song_template_view, name="song-template"),
    path("favourite/", LibraryViewController.favourite_template_view, name="favourite-template"),
]
