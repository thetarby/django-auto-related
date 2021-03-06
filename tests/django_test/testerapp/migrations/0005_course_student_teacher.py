# Generated by Django 3.0 on 2020-07-29 20:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('testerapp', '0004_auto_20200728_1325'),
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('teaches', models.ManyToManyField(to='testerapp.Course')),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('courses', models.ManyToManyField(to='testerapp.Course')),
                ('parent', models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='testerapp.Parent')),
            ],
        ),
    ]
