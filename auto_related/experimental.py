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

def monkeypatch_listserializer(serializer_instance):
    from types import MethodType
    def new(*args, **kwargs):
        data=args[1]
        if not isinstance(data, QuerySet):
            pass
        elif is_evaluated(data):
            pass
        else:
            t=Tracer(serializer_instance.child)
            traces=t.trace()
            s,p=optimized_queryset_given_trails(traces)
            data=data.select_related(*s).prefetch_related(*p).only(*t.build_only())
        return ListSerializer.to_representation(args[0], data, **kwargs)
    serializer_instance.to_representation  = MethodType(new, serializer_instance)
    return serializer_instance
