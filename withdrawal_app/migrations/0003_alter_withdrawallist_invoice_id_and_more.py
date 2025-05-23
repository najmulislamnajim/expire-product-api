# Generated by Django 5.2 on 2025-05-04 11:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('withdrawal_app', '0002_alter_withdrawalinfo_delivery_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='withdrawallist',
            name='invoice_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='withdrawal_list', to='withdrawal_app.withdrawalinfo'),
        ),
        migrations.AlterField(
            model_name='withdrawalrequestlist',
            name='invoice_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='request_list', to='withdrawal_app.withdrawalinfo'),
        ),
    ]
