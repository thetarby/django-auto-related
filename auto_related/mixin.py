from rest_framework.relations import (
    RelatedField,
    ManyRelatedField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
)
from rest_framework.serializers import ModelSerializer, BaseSerializer, ListSerializer
from inspect import isclass
from django.db import models
from django.db.models.query import QuerySet
from django.db.models import prefetch_related_objects
from .utils import *
from .tracer import Tracer, optimized_queryset_given_trails


class ViewMixin:
    def get_queryset(self):
        t=Tracer(self.get_serializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)
        queryset=super().get_queryset()
        return queryset.select_related(*s).prefetch_related(*p)

class ViewMixinWithOnlyOptim:
    def get_queryset(self):
        t=Tracer(self.get_serializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)
        queryset=super().get_queryset()
        return queryset.select_related(*s).prefetch_related(*p).only(*t.build_only())

