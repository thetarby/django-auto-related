from django.db import models

# Create your models here.
class Parent(models.Model):
    text=models.TextField()
    child = models.ForeignKey('Child', on_delete=models.CASCADE)

class Child(models.Model):
    text=models.TextField()
    child = models.ForeignKey('ChildChild', on_delete=models.CASCADE, related_name='parents', null=True, default=None)

class ChildChild(models.Model):
    text=models.TextField()




class Teacher(models.Model):
    text=models.TextField()
    big_text_field=models.TextField(null=True)
    teaches=models.ManyToManyField('Course')


class Course(models.Model):
    text=models.TextField()


class Student(models.Model):
    text=models.TextField()
    courses=models.ManyToManyField('Course')
    parent = models.OneToOneField(Parent, on_delete=models.SET_NULL, null=True)