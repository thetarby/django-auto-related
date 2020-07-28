from rest_framework.relations import (
    RelatedField,
    ManyRelatedField,
    HyperlinkedIdentityField,
    HyperlinkedRelatedField,
    PrimaryKeyRelatedField
)
from rest_framework.serializers import ModelSerializer, BaseSerializer, ListSerializer
from inspect import isclass
from django.db import models
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel,
)
from django.db.models.fields.related import (
    RelatedField as DjangoRelatedField, ForeignKey, OneToOneField
)

"""
logic:

if is_evaluated(qs):
    for each field:
        is_related_field_cached(qs[0], field)
    
    prefetch_uncached
else:
    build(get_related_fields(serializer))
"""

"""
import sys
sys.path.insert(0, "../..")
from auto_related.demo import *
from testerapp.models import *
from testerapp.serializers import *
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel,
)
from django.db.models.fields.related import (
    RelatedField as DjangoRelatedField
)
from auto_related.tracer import *
patch_cursor()
"""


#gets django queryset as input and outputs if queryset is evaluated, that is, already hit the database
def is_evaluated(queryset):
    """
    if it is a select query than when it is evaluated this attribure is set.
    but for queries using count, delete, update etc this probably do not work
    """
    return queryset._result_cache is not None


def get_related_fields(serializer):
    """
    serializer:django rest serializer instance

    return value:list of fields that requires a select related or prefetch related
    """
    #if it is class get instance, if it is instance leave as is.
    serializer=serializer() if isclass(serializer) else serializer

    #if it is a list serializer fields are in child attribute
    fields=serializer.child.fields if isinstance(serializer, ListSerializer) else serializer.fields
    #fields=serializer._declared_fields this version uses class definition hence do not include source info of the fields
    
    res=[]
    for key in fields:
        field=fields[key]
        if isinstance(field, (BaseSerializer, RelatedField, ManyRelatedField)): # or '.' in field.source
            if isinstance(field, BaseSerializer):
                recursing=field.child if isinstance(field, ListSerializer) else field
                res.append({ 'field' : field, "childs": get_related_fields(recursing)})
            else:
                res.append({'field':field, "childs":[]})

    return res


#TODO: When used with primarykeyrelated field it does not include source field or pk 
#pk may be included but when accesing a models field pk is not listed there. So some changes are required to do that
def get_all_sources(serializer):
    #if it is class get instance, if it is instance leave as is.
    serializer=serializer() if isclass(serializer) else serializer
    fields=serializer.child.fields if isinstance(serializer, ListSerializer) else serializer.fields
    #fields=serializer._declared_fields this version uses class definition hence do not include source info of the fields
    
    res=[]
    for key in fields:
        field=fields[key]
        source=field.source if field.source is not None else field.name
        
        #if it is SerializerMethodField
        if source == '*':
            continue

        #This is a special case. Normally source of a primarykey related field is not used while serializing but pk value is used
        #hence no need to prefetch related model when using primary key related field
        if isinstance(field,PrimaryKeyRelatedField):
            continue
        res.append(source)
        if isinstance(field, (BaseSerializer, RelatedField, ManyRelatedField)): # or '.' in field.source
            if isinstance(field, BaseSerializer):
                recursing=field.child if isinstance(field, ListSerializer) else field
                res+=[source+'.'+each_source for each_source in get_all_sources(recursing)]

    return res


def build(related_fields):
    """
    related_fields: output of the get related fields
    return value: list of related sources
    """
    return build_helper(related_fields, '', set())


def build_helper(childs, prepend, res):
    for field in childs:
        res.add(prepend+field['field'].source)
        build_helper(field['childs'], prepend+field['field'].source+'__', res)
    return res 


def setup_query(serializer):
    fields=get_related_fields(serializer)
    return list(build(fields))


#TODO: model instance can be manually created.It might be problematic
def not_cached_relation_fields(model_instance):
    """
    model_instance: A django model instance.
    return value: list of uncached fields relation fields such as foreign key, onetonefield etc...

    return value do not include back references like ***field_set. Django rest deals with them in list serializer like this;
    # Dealing with nested relationships, data can be a Manager,
    # so, first get a queryset from the Manager if needed
    iterable = data.all() if isinstance(data, models.Manager) else data
    """
    res=[]
    for field in model_instance._meta.concrete_fields:
        # If the related field isn't cached, then an instance hasn't
        # been assigned and there's no need to worry about this check.
        if field.is_relation and field.is_cached(model_instance):
            continue
        else:
            res.append(field)
    return res



def is_related_field_cached(model_instance, field):
    """
    model_instance: A django model instance.
    field: name of the related field as string

    return value: can be considered as !(is_hit_needed)
    """
    
    if field in [instance.name for instance in model_instance._meta.concrete_fields]:
        field=[instance for instance in model_instance._meta.concrete_fields if instance.name==field][0]
        
        if field.is_relation: return field.is_cached(model_instance)
        #TODO: it is assumed that if it is not a related field then no need for db hit
        else: return True

    #TODO: this may cause a db hit. Normally this is for backrefs.
    elif isinstance(getattr(model_instance, field), models.Manager):
        qs=getattr(model_instance, field).all()
        return is_evaluated(qs)

    else:
        raise Exception("Model instance has no such related field")


def are_nested_fields_cached(model_instance, fields):
    return not(False in [is_nested_field_cached(model_instance, field) for field in fields])


def are_nested_fields_cached2(qs_or_model, fields):
     if isinstance(qs_or_model, models.query.QuerySet):
        if not is_evaluated(qs_or_model):
            #TODO: not evaluating it does not mean that it has n+1 problem.
            return False
        elif(len(qs_or_model)==0):
            return True
        else:
            return not(False in [is_nested_field_cached(qs_or_model[0], field) for field in fields])
     return not(False in [is_nested_field_cached(qs_or_model, field) for field in fields])


def is_nested_field_cached(model_instance, field):
    """
    model_instance: A django model instance.
    field: name of the related field as string seperated by dot like field_name.another_field_name.related_field_name etc..

    return value: returns True if no db hit is needed and returns false otherwise
    """
    nested_fields=field.split('.')
    if len(nested_fields)==1:
        return is_related_field_cached(model_instance, nested_fields[0])
    return is_related_field_cached(model_instance, nested_fields[0]) and is_nested_field_cached(getattr(model_instance, nested_fields[0]), ".".join(nested_fields[1:]))


def patch_cursor():
    # when called in django environment it patches django cursor object
    # so that at each db hit it prints how many queries executed. Useful to detect n+1 problems.
    from django.db import connection as c
    old_execute= c.cursor().__class__.execute
    old_callproc= c.cursor().__class__.callproc
    old_executemany= c.cursor().__class__.executemany
    def callproc(*args, **kwargs):
        print('callproc')
        print('query_count: '+str(len(c.queries)))
        return old_callproc(*args, **kwargs)

    def execute(*args, **kwargs):
        print('execute')
        print('query_count: '+str(len(c.queries)))

        return old_execute(*args, **kwargs)

    def executemany(*args, **kwargs):
        print('executemany')
        print('query_count: '+str(len(c.queries)))

        return old_executemany(*args, **kwargs)
    
    c.cursor().__class__.execute=execute
    c.cursor().__class__.callproc=callproc
    c.cursor().__class__.executemany=executemany