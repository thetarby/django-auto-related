from django.shortcuts import render
from rest_framework import status,generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view,parser_classes
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser


from testerapp.models import *
from testerapp.serializers import *

import sys
sys.path.insert(0,'C:\\Users\\heymannn\\Desktop\\components\\auto_related')

from auto_related.tracer import *
from auto_related.utils import *
from auto_related.mixin import *
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
        t=Tracer(ParentSerializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)

        return Parent.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class TeacherList(ViewMixinWithOnlyOptim,CustomListView):
    serializer_class = TeacherSerializer
    #extra prefetches caused by serializermethodfield can be set here. Mixin will populate the queryset for others.
    queryset=Teacher.objects.prefetch_related('teaches__student_set').all()
    """
    def get_queryset(self):
        t=Tracer(TeacherSerializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)

        return Teacher.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())
    """

class StudentList(CustomListView):
    serializer_class = StudentSerializer
    def get_queryset(self):
        t=Tracer(StudentSerializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)

        return Student.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())


class CourseList(ViewMixin,CustomListView):
    serializer_class = CourseSerializer2
    queryset=Course.objects.all()


class ChildChildList(CustomListView):
    serializer_class = ChildChildSerializer2
    def get_queryset(self):
        t=Tracer(ChildChildSerializer2())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)

        return ChildChild.objects.select_related(*s).prefetch_related(*p).only(*t.build_only())