# Generated by Django 3.0 on 2020-07-30 19:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testerapp', '0005_course_student_teacher'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='big_text_field',
            field=models.TextField(null=True),
        ),
    ]
