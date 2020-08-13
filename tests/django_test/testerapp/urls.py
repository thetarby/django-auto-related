from django.urls import path
from testerapp.views import *
from rest_framework import generics
from testerapp.models import *

urlpatterns=[
    path('parent', ParentList.as_view(), name='parent'),
    path('parent/<slug>', ParentList.as_view()),

    path('teacher', TeacherList.as_view()),
    path('teacher/<slug>', TeacherList.as_view()),

    path('student', StudentList.as_view()),
    path('student/<slug>', StudentList.as_view()),

    path('childchild', ChildChildList.as_view()),
    path('childchild/<slug>', ChildChildList.as_view()),
    
    path('course', CourseList.as_view()),
    path('course/<slug>', CourseList.as_view()),

    path('simple-course', SimpleCourseList.as_view()),
    path('simple-course/<slug>', SimpleCourseList.as_view()),

    path('simple-teacher', SimpleTeacherList.as_view()),
    path('simple-teacher/<slug>', SimpleTeacherList.as_view()),
]