# boilerplate_project

## Submission package

### 1) Source code

- Django models: [music/models.py](music/models.py)
- Migrations: [music/migrations/0001_initial.py](music/migrations/0001_initial.py)
- Supporting configuration: [boilerplate_project/settings.py](boilerplate_project/settings.py)
- Admin CRUD setup: [music/admin.py](music/admin.py)

### 2) Domain layer implementation

Implemented domain entities and constraints from the provided model:

- `Library` (one per user)
- `GenForm` (many per user)
- `Song` (many per library, optional one-to-one with `GenForm`)
- `Favorite` (library-song mapping with uniqueness)
- Enumerations: `Voice` (`male`, `female`) and `Status` (`generating`, `failed`, `ready`)
- Constraint: `Song.e_rating` must be `"E"` or blank

### 3) ORM and database migrations

- Migration file exists and is committed: [music/migrations/0001_initial.py](music/migrations/0001_initial.py)
- Database schema applied with:

```bash
/Users/cherio/Documents/boilerplate_project/.venv/bin/python manage.py migrate
```

### 4) Evidence of CRUD functionality (real persisted data)

CRUD was demonstrated against SQLite using Django ORM (`manage.py shell`), with create/read/update/delete on core entities.

Command used:

```bash
/Users/cherio/Documents/boilerplate_project/.venv/bin/python manage.py shell -c "from django.contrib.auth import get_user_model; from music.models import Library, GenForm, Song, Favorite, Status, Voice; User=get_user_model(); u,_=User.objects.get_or_create(username='submit_demo_user', defaults={'email':'submit_demo@example.com'}); lib,_=Library.objects.get_or_create(user=u); gf=GenForm.objects.create(user=u,title='Submit Demo',mood_tone='Energetic',genre='Pop',voice=Voice.FEMALE,description='Submission demo'); s=Song.objects.create(library=lib,gen_form=gf,status=Status.GENERATING,e_rating='E',title='Submit Draft'); Favorite.objects.create(library=lib,song=s); print('CREATE_READ', {'gen_forms':GenForm.objects.filter(user=u).count(),'songs':Song.objects.filter(library=lib).count(),'favorites':Favorite.objects.filter(library=lib).count()}); s.status=Status.READY; s.title='Submit Final'; s.save(update_fields=['status','title']); s2=Song.objects.get(pk=s.pk); print('UPDATE', {'status':s2.status,'title':s2.title}); Favorite.objects.filter(library=lib,song=s).delete(); Song.objects.filter(pk=s.pk).delete(); GenForm.objects.filter(pk=gf.pk).delete(); print('DELETE_READ', {'gen_forms':GenForm.objects.filter(user=u).count(),'songs':Song.objects.filter(library=lib).count(),'favorites':Favorite.objects.filter(library=lib).count()})"
```

Observed output:

```text
CREATE_READ {'gen_forms': 1, 'songs': 1, 'favorites': 1}
UPDATE {'status': 'ready', 'title': 'Submit Final'}
DELETE_READ {'gen_forms': 0, 'songs': 0, 'favorites': 0}
```

This confirms CRUD operations are working on persisted data.