from django.test import TestCase


class UmlTemplateRouteTests(TestCase):
    def test_login_template_route_renders(self):
        response = self.client.get("/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LoginTemplate")

    def test_gen_form_template_route_renders(self):
        response = self.client.get("/generate/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GenFormTemplate")

    def test_library_template_route_renders(self):
        response = self.client.get("/library/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LibraryTemplate")

    def test_song_template_route_renders(self):
        response = self.client.get("/song/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SongTemplate")

    def test_favourite_template_route_renders(self):
        response = self.client.get("/favourite/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FavouriteTemplate")
