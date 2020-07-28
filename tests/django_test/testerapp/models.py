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


