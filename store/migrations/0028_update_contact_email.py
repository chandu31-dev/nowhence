from django.db import migrations, models


OLD_EMAIL = 'info@NowhenceClothings.com'
NEW_EMAIL = 'nowhenceclothings@gmail.com'


def update_default_contact_email(apps, schema_editor):
    ContactInfo = apps.get_model('store', 'ContactInfo')
    ContactInfo.objects.using(schema_editor.connection.alias).filter(
        email__iexact=OLD_EMAIL,
    ).update(email=NEW_EMAIL)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0027_order_amount_paid_order_is_preorder_and_more'),
    ]

    operations = [
        migrations.RunPython(
            update_default_contact_email,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='email',
            field=models.EmailField(default=NEW_EMAIL, max_length=254),
        ),
    ]
