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

