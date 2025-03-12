from django.db import migrations
from django.contrib.auth.hashers import make_password

def create_initial_bt_admin(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    Group = apps.get_model('auth', 'Group')
    
    # Create initial Baker Tilly admin
    bt_admin = CustomUser.objects.create(
        email='baker.admin@example.com',
        password=make_password('SecurePass123!'),  # You should change this password
        is_staff=True,
        is_active=True,
        is_baker_tilly_admin=True,
        must_change_password=False
    )
    
    # Add to Baker Tilly Admin group
    bt_group = Group.objects.get(name='Baker Tilly Admin')
    bt_admin.groups.add(bt_group)

def remove_initial_bt_admin(apps, schema_editor):
    CustomUser = apps.get_model('accounts', 'CustomUser')
    CustomUser.objects.filter(email='baker.admin@example.com').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_create_baker_tilly_group'),
    ]

    operations = [
        migrations.RunPython(create_initial_bt_admin, remove_initial_bt_admin),
    ] 