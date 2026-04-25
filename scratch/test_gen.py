import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from music.views.generator_views import GeneratorViewController, GenerationPayload
from music.models import User, GenForm

def test_generation():
    # Try to find a user
    user = User.objects.first()
    if not user:
        print("No user found in database.")
        return

    print(f"Testing generation for user: {user.display_name}")
    
    # Create a dummy gen form
    gen_form = GenForm.objects.create(
        user=user,
        title="Test Song",
        mood_tone="Happy",
        genre="Pop",
        voice="Male",
        description="A test song generation"
    )
    
    print(f"GenForm created: {gen_form.pk}")
    
    # Test strategy resolution
    try:
        strategy = GeneratorViewController.resolve_generation_strategy("mock")
        print(f"Strategy resolved: {strategy.key}")
        
        payload = GenerationPayload.from_gen_form(gen_form)
        result = strategy.generate(payload)
        print(f"Generation Result: {result}")
        print("SUCCESS: Mock generation works.")
    except Exception as e:
        print(f"FAILURE: Mock generation failed: {e}")

if __name__ == "__main__":
    test_generation()
