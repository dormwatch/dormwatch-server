from django.db import migrations


def move_workers_and_delete_role(apps, schema_editor):
    """Retire the stray 'worker' role without losing the people behind it.

    Workers are a separate roster (the Worker model) of accountless contractors,
    so 'worker' was never a valid resident role — it only appeared as leftover
    seed data, and registration creates just 'admin'/'student'. Any user who
    ended up with it is really a contractor, so we migrate each into the Worker
    table (full_name from their profile name, company/phone left blank), delete
    their account, then drop the role.

    UserProfile.user is a OneToOne PK with on_delete=CASCADE, so deleting the
    auth.User cascades the profile away too (no orphaned account left behind).
    """
    Role = apps.get_model('complaints', 'Role')
    UserProfile = apps.get_model('complaints', 'UserProfile')
    Worker = apps.get_model('complaints', 'Worker')
    User = apps.get_model('auth', 'User')

    worker_roles = Role.objects.filter(role_name__iexact='worker')
    profiles = UserProfile.objects.filter(role__in=worker_roles)

    user_ids = []
    for p in profiles:
        full_name = f"{p.first_name} {p.last_name}".strip() or p.email
        Worker.objects.create(full_name=full_name, company="", phone="")
        user_ids.append(p.user_id)

    # Delete the accounts; the OneToOne cascade removes their profiles.
    User.objects.filter(pk__in=user_ids).delete()
    # Role is now unreferenced.
    worker_roles.delete()


class Migration(migrations.Migration):
    dependencies = [('complaints', '0013_worker_remove_ticket_user_ticket_worker')]
    operations = [
        migrations.RunPython(
            move_workers_and_delete_role,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
