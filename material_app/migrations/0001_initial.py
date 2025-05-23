# Generated by Django 5.2 on 2025-04-30 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RplMaterial',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('matnr', models.CharField(max_length=40)),
                ('plant', models.CharField(max_length=4)),
                ('sales_org', models.CharField(max_length=4)),
                ('dis_channel', models.CharField(max_length=2)),
                ('material_name', models.CharField(blank=True, max_length=40, null=True)),
                ('producer_company', models.CharField(blank=True, max_length=3, null=True)),
                ('team1', models.CharField(blank=True, max_length=3, null=True)),
                ('pack_size', models.TextField(blank=True, null=True)),
                ('unit_tp', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('unit_vat', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('mrp', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('brand_name', models.CharField(blank=True, max_length=255, null=True)),
                ('brand_description', models.CharField(blank=True, max_length=255, null=True)),
                ('active', models.CharField(blank=True, max_length=1, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'rpl_material',
                'managed': False,
            },
        ),
    ]
