# Generated by Django 3.0 on 2020-07-27 13:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testerapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parent',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parents', to='testerapp.Child'),
        ),
    ]