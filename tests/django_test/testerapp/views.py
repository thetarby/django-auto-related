from django.shortcuts import render
from rest_framework import status,generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view,parser_classes
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser

from testerapp.views import *
from testerapp.models import *
from testerapp.serializers import *

import sys
sys.path.insert(0,'C:\\Users\\heymannn\\Desktop\\components\\auto_related')

from auto_related.tracer import *
from auto_related.utils import *
# Create your views here.
class CustomListView(generics.ListAPIView):
    #a custom base view to support old urls and behaviours .../1 and .../all works as nothing is changed
    #and query params are also supported with this approach
    
    def get(*args, **kwargs):
        slug=(kwargs.get('slug',None))
        self=args[0]
        request=args[1]
        if slug == 'slow':
            return Response(self.get_serializer_class()(self.get_serializer_class().Meta.model.objects.all(),many=True).data)
        return generics.ListAPIView.get(self, request)

class ParentList(CustomListView):
    serializer_class = ParentSerializer
    def get_queryset(self):
        s,p=optimized_queryset(ParentSerializer)
        t=Tracer(ParentSerializer())
        t.trace()

        return Parent.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class TeacherList(CustomListView):
    serializer_class = TeacherSerializer
    def get_queryset(self):
        s,p=optimized_queryset(TeacherSerializer)
        t=Tracer(TeacherSerializer())
        t.trace()

        return Teacher.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class StudentList(CustomListView):
    serializer_class = StudentSerializer
    def get_queryset(self):
        s,p=optimized_queryset(StudentSerializer)
        t=Tracer(StudentSerializer())
        t.trace()

        return Student.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class CourseList(CustomListView):
    serializer_class = CourseSerializer2
    def get_queryset(self):
        s,p=optimized_queryset(CourseSerializer2)
        t=Tracer(CourseSerializer2())
        t.trace()
        print(s, p)
        return Course.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class ChildChildList(CustomListView):
    serializer_class = ChildChildSerializer2
    def get_queryset(self):
        s,p=optimized_queryset(ChildChildSerializer2)
        t=Tracer(ChildChildSerializer2())
        t.trace()

        return ChildChild.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())