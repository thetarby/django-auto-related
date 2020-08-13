from .utils import get_all_sources
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel,
)
from django.db.models.fields.related import (
    RelatedField as DjangoRelatedField, ForeignKey, OneToOneField
)
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import SerializerMethodField
from rest_framework.serializers import BaseSerializer, ListSerializer
from rest_framework.relations import (
    ManyRelatedField,
)
from functools import lru_cache
from inspect import isclass

import warnings

#from django docs: 
#You can refer to any ForeignKey or OneToOneField relation in the list of fields passed to select_related().
#You can also refer to the reverse direction of a OneToOneField

#given a trail(trace) it returns select_related and prefetch_related for that trail. It works for only one trail. 
#It should be applied to all sources of a serializer and resulting sets should be added. 
def select_and_prefetch(trace):
    select=[]
    prefetch=[]
    for field in trace:
        if isinstance(field['field'], (OneToOneRel, ForeignKey, OneToOneField)):
            select.append(field['accessor'])
            continue
        elif field['field'].related_model is None:
            break
        else:
            #TODO: related_modelı none olan bir field ile karşılaştığında prefetchi build etmeyide kesmeli
            prefetch=[f['accessor'] for f in trace if f['field'].related_model is not None]
            break
   
    return "__".join(select), "__".join(prefetch)


#given trails returned from Tracer.update method 
#returns two sets first of which is arguments for select_related and second one is arguments to pass to prefetch_related 
def optimized_queryset_given_trails(trails):
    select=set()
    prefetch=set()
    for trail in trails:
        s,p=select_and_prefetch(trail)
        select.add(s)
        prefetch.add(p)
    
    select.discard(''), prefetch.discard('')

    return select, prefetch


class Tracer:
    """
        Examines a serializer and trace all of its sources.
        Those trails are used to decide what to prefetch_related and what to select_related
    """


    def __init__(self, serializer):
        self.serializer=serializer
        self.is_values=self.values_optim()


    def trace(self):
        sources=get_all_sources(self.serializer)
        trails=[]
        for source in sources:
            trails.append(Trail(self.trace_source(source)))
        self.trails=trails
        return trails 
    
    
    def trace_source(self, source, include_reverse=True):
        """Traces a source like model.other_model.field and returns
        """
        serializer=self.serializer
        model=serializer.Meta.model
        fields=Trail.get_model_accessors(model)

        trace=[]
        source=source.split('.')
        for each_field_name in source:
            #find field by its name in fields
            try:
                field = [f for f in fields if f['accessor']==each_field_name][0]
            except IndexError:
                # NOTE: does not work with fields with source like 'get_xxx_display' eventhough django rest could handle them. 
                # sources that includes get_xxx_display will still work since that field cannot be related. Hence not inluding 
                # it in the trails will have no harm.

                # warn when one of the sources is not included
                warnings.warn('auto-related: Source cannot be traced: {}. Hence it might not be fully optimized.'.format(source))
                break

            if include_reverse==False and isinstance(field['field'], ForeignObjectRel):
                break

            trace.append(field['field'])
            
            #TODO: does it support GenericForeignKeys ?
            if not(isinstance(field['field'], ForeignObjectRel) or isinstance(field['field'], DjangoRelatedField)):
                # if it is not a related or reverse related field than trail is done. Source should finish here as well
                # if it does not it should give an attribute error anyway. Maybe it should be checked to see possible errors
                break
            else:
                fields=Trail.get_model_accessors(field['field'].related_model)

        return trace


    #same as trace method but this do not include reverse related fields. It is useful to decide what to pass to only() since
    #it does not support reverse relations
    def eliminate_reverse(self):
        sources=get_all_sources(self.serializer, include_pk=True)
        trails=[]
        for source in sources:
            t=self.trace_source(source, include_reverse=False)
            if len(t)==0: continue
            trails.append(Trail(t))
        return trails 


    #method that returns what to pass to only()
    def build_only(self):
        trails=self.eliminate_reverse()
        return [trail.get_as_source().replace('.','__') for trail in trails]


    def values_optim(self):
        serializer=self.serializer
        serializer=serializer() if isclass(serializer) else serializer
        fields=serializer.child.fields if isinstance(serializer, ListSerializer) else serializer.fields
        
        for key in fields:
            field=fields[key]
            if isinstance(field, (BaseSerializer, ListSerializer, ManyRelatedField)):
                return False

        return True


class Trail:

    """
    Trail is a list of django field instance and its accessors as string pair such as
    [{'field':field_instance, 'accessor':'parent'}, {'field':field_instance, 'accessor':'child_set'}]

    It is generated when a tracer is applied to a serializer. Trail is the list of visited django field instances of related models 
    when a source is tried to be accessed. For example if from model Parent, we want to access child's toys' we would do this;

    Parent.child.toys

    Here we visit Parent, Child and Toy models hence we need to prefetch all of them. Trail helps us to decide what to prefetch or select
    by examining visited fields. A onetoone field leads to select_related while a manytomany or reverse_related fields requires prefetch_related
    """
    def __init__(self, fields):
        self.fields=fields
    

    @staticmethod
    def get_accessor(field):
        if isinstance(field, SerializerMethodField):
            raise Exception('SerializerMethodField has no accessor')
        #ForeignObjectRel instances have this attribute. returns default name like 'parent_set' or related_name if it is set 
        if hasattr(field, 'get_accessor_name'):
            return field.get_accessor_name()
        else:
            #NOTE: there is also field.attname. It might be more appropriate 
            return field.name
    

    @staticmethod
    @lru_cache(maxsize=20, typed=True) # Since this function will very likely be called more than once with the same model caching it makes sense.
    def get_model_accessors(model):
        """
            given django model instance it returns all of its fields with its accessor(just like trail object)
            including related and reverse related fields like;
            [{'field':field_instance, 'accessor':'parent'}, {'field':field_instance, 'accessor':'child_set'}]
        """
        res=[]
        for f in model._meta.get_fields():
            res.append({'field':f, 'accessor':Trail.get_accessor(f)})
        return res


    def __getitem__(self, key):
        if isinstance(key, slice):
            indices = range(*key.indices(len(self.fields)))
            return [{'field':self.fields[i], 'accessor': Trail.get_accessor(self.fields[i])} for i in indices]
        return {'field':self.fields[key], 'accessor': Trail.get_accessor(self.fields[key])}
    
    
    def __repr__(self):
        return str(self.fields)
    
    
    def get_as_source(self, seperator='.'):
        return seperator.join([Trail.get_accessor(f) for f in self.fields])


#this function does the same thing with Trace class without classes
def trace_source(source, serializer):
    model=serializer.Meta.model
    #TODO: no need to call this func every time. use it in class and cache it somehow instead
    fields=Trail.get_model_accessors(model)

    trace=[]
    source=source.split('.')
    for each_field_name in source:
        #find field by its name in fields
        try:
            field = [f for f in fields if f['accessor']==each_field_name][0]
        except IndexError:
            raise Exception('No such field: {}'.format(each_field_name))
        
        trace.append(field)
        
        #TODO: does it support GenericForeignKeys ?
        if not(isinstance(field['field'], ForeignObjectRel) or isinstance(field['field'], DjangoRelatedField)):
            # if it is not a related or reverse related field than trail is done. Source should finish here as well
            #if it does not it should give attribute error. Maybe it should be checked to see possible errors
            break
        else:
            fields=Trail.get_model_accessors(field['field'].related_model)

    return trace


#same as optimized_queryset_given_trails but without using classes Tracer, Trail
def optimized_queryset(serializer):
    traces=[]
    for s in get_all_sources(serializer):
        traces.append(trace_source(s,serializer))

    select=set()
    prefetch=set()
    for trace in traces:
        s,p=select_and_prefetch(trace)
        select.add(s)
        prefetch.add(p)
    
    select.discard(''), prefetch.discard('')

    return select, prefetch