from rest_framework.relations import (
    RelatedField,
    ManyRelatedField,
    PrimaryKeyRelatedField,
    HyperlinkedRelatedField
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
import warnings

"""
NOTE:
HyperlinkedIdentityFields' source is also * like SerializerMethodField. 
Since HyperlinkedIdentityField uses field of the object itself it may not need optimization other than only() and defer()

"""


#TODO: When used with primarykeyrelated field it does not include source field or pk 
#pk may be included but when accesing a models field pk is not listed there. So some changes are required to do that

#TODO:HyperlinkedRelatedField uses pk as default but can access to other fields of a model with a different lookup_key parameter that requires a db hit.

#NOTE: if output of this will be given to only or defer then reverse relations other than onetoone should be removed(django not supports it) and
#primarykeyrelated and HyperlinkedRelatedField fields should be added. For now those fields are not included in result since they
#only access pk of the object which does not require to fetch whole object. But only() needs them to work properly.
def get_all_sources(serializer, include_pk=False):
    #if it is class get instance, if it is instance leave as is.
    serializer=serializer() if isclass(serializer) else serializer
    try:
        fields=serializer.child.fields if isinstance(serializer, ListSerializer) else serializer.fields
    except AttributeError as e:
        warnings.warn('Fields cannot be accessed hence sources cannot be fully accessed. There is probably a BaseSerializer in the fields.')
        return []
    #fields=serializer._declared_fields this version uses class definition hence do not include source info of the fields
    
    res=[]
    for key in fields:
        field=fields[key]
        source=field.source if field.source is not None else field.name
        
        #if it is SerializerMethodField
        if source == '*':
            if hasattr(field, '_auto_related_sources'):
                res+=field._auto_related_sources
            continue
        
        # if it is a many related_field get child relation for below isintance checks to work since ManyRelatedField is not subclass of them they are useless if we dont get child_relation
        # Child relation will have the same source so there is no problem there
        if isinstance(field, ManyRelatedField):
            field=field.child_relation

        #This is a special case. Normally source of a primarykey related field is not used while serializing but pk value is used
        #hence no need to prefetch related model when using primary key related field
        if isinstance(field, PrimaryKeyRelatedField) and include_pk==False:
            continue
        
        #HyperlinkedRelatedField uses pk only optimization like PrimaryKeyRelatedField if lookup_field is 'pk' which is its default
        """
        if (isinstance(field, HyperlinkedRelatedField)) and field.lookup_field=='pk' and include_pk==False:
            continue
        """

        # Another special case
        # HyperlinkedRelatedField uses pk only optimization like PrimaryKeyRelatedField if lookup_field is 'pk' which is its default
        if isinstance(field, HyperlinkedRelatedField):
            if field.lookup_field=='pk':
                if include_pk==False:
                    continue
            else:
                source+='.{}'.format(str(field.lookup_field))

        res.append(source)
        if isinstance(field, (BaseSerializer)):
            recursing=field.child if isinstance(field, ListSerializer) else field
            res+=[source+'.'+each_source for each_source in get_all_sources(recursing, include_pk)]

    return res


"""
Below code is util functions for django's cache logic. For now they are not used.

"""

#gets django queryset as input and outputs if queryset is evaluated, that is, already hit the database
def is_evaluated(queryset):
    """
    if it is a select query than when it is evaluated this attribure is set.
    but for queries using count, delete, update etc this probably do not work
    """
    return queryset._result_cache is not None


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


def are_nested_fields_cached(qs_or_model, fields):
    """
    qs_or_model: it could be either a queryset instance or a model instance
    fields: list of strings representing sources to be accessed on qs_or_model such as ['field', 'related_field.field', ...]

    returns: True if all fields are cached and no db hit is required to access sources and False otherwise 
    """
    if isinstance(qs_or_model, models.query.QuerySet):
        if not is_evaluated(qs_or_model):
            #NOTE: not evaluating it does not mean that it has n+1 problem.
            return [] # none of them is cached
        elif(len(qs_or_model)==0):
            #NOTE: normally len() leads queryset to be evaluated but above if conditon guarantees that it will be evaluted when this code is executed, so no problem
            return fields # all of them are cached
        else:
            #TODO: first item of the queryset may be fetched but it does not mean other items are fetched too. This code is problematic
            return not(False in [is_nested_field_cached(qs_or_model[0], field) for field in fields])
    return not(False in [is_nested_field_cached(qs_or_model, field) for field in fields])


def nested_fields_not_cached(qs_or_model, fields):
    """
    qs_or_model: it could be either a queryset instance or a model instance
    fields: list of strings representing sources to be accessed on qs_or_model such as ['field', 'related_field.field', ...]

    returns: True if all fields are cached and no db hit is required to access sources and False otherwise 
    """
    if isinstance(qs_or_model, models.query.QuerySet):
        if not is_evaluated(qs_or_model):
            #NOTE: not evaluating it does not mean that it has n+1 problem.
            return [] # none of them is cached
        elif(len(qs_or_model)==0):
            #NOTE: normally len() leads queryset to be evaluated but above if conditon guarantees that it will be evaluted when this code is executed, so no problem
            return fields # all of them are cached
        else:
            #TODO: first item of the queryset may be fetched but it does not mean other items are fetched too. This code is problematic
            pass
    return [field for field in fields if is_nested_field_cached(qs_or_model, field)]


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


def patch_related_fields():
    old=DjangoRelatedField.__getattribute__
    old2=ForeignObjectRel.__getattribute__
    fields=[]
    def patched(*args, **kwargs):
        fields.append(args[0])
        return old(*args, **kwargs)
    def patched2(*args, **kwargs):
        fields.append(args[0])
        return old2(*args, **kwargs)
    DjangoRelatedField.__getattribute__=patched
    ForeignObjectRel.__getattribute__=patched2
    res=str([c.student_set.all()[0].pk for c in obj.teaches.all()])
    DjangoRelatedField.__getattribute__=old
    ForeignObjectRel.__getattribute__=old2
    print(set([(f.name, f.model) for f in fields]))
    return res


"""
import sys
sys.path.insert(0, "../..")
from auto_related.utils import *
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