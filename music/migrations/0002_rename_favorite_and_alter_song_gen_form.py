import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("music", "0001_initial"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Favorite",
            new_name="Favourite",
        ),
        migrations.AlterField(
            model_name="song",
            name="gen_form",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="songs",
                to="music.genform",
            ),
        ),
    ]
