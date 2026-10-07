from django.db import migrations, models


OLD_PHONE = '+91 8096584948'
NEW_PHONE = '+91 9014352958'


def update_default_contact_phone(apps, schema_editor):
    ContactInfo = apps.get_model('store', 'ContactInfo')
    ContactInfo.objects.using(schema_editor.connection.alias).filter(
        phone=OLD_PHONE,
    ).update(phone=NEW_PHONE)


def restore_default_contact_phone(apps, schema_editor):
    ContactInfo = apps.get_model('store', 'ContactInfo')
    ContactInfo.objects.using(schema_editor.connection.alias).filter(
        phone=NEW_PHONE,
    ).update(phone=OLD_PHONE)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0019_alter_herosection_subtitle'),
    ]

    operations = [
        migrations.RunPython(
            update_default_contact_phone,
            restore_default_contact_phone,
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='phone',
            field=models.CharField(
                default='+91 9014352958',
                max_length=30,
            ),
        ),
    ]
