# Generated by Django 3.0 on 2020-07-28 10:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testerapp', '0003_auto_20200727_1841'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parent',
            name='child',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='testerapp.Child'),
        ),
    ]
