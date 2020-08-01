from .utils import *
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel,
)
from django.db.models.fields.related import (
    RelatedField as DjangoRelatedField, ForeignKey, OneToOneField
)
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import SerializerMethodField


#from django docs: 
#You can refer to any ForeignKey or OneToOneField relation in the list of fields passed to select_related().
#You can also refer to the reverse direction of a OneToOneField

#given a trail(trace) it returns select_related and prefetch_related for that trail. It works for only one trail. 
#It should be applied to all sources of a serializer and resulting sets should be added. 
def select_and_prefetch(trace):
    select=[]
    prefetch=[]
    for i,field in enumerate(trace):
        if isinstance(field['field'], OneToOneRel) or isinstance(field['field'], ForeignKey) or isinstance(field['field'], OneToOneField):
            select.append(field['accessor'])
            continue
        elif field['field'].related_model is None:
            break
        else:
            #TODO: related_modelı none olan bir field ile karşılaştığında prefetchi build etmeyide kesmeli
            prefetch=[f['accessor'] for f in trace if f['field'].related_model is not None]
            break
   
    if len(select)!=0 or len(prefetch)!=0:
        print('bakbi >' + str(trace), "__".join(select), "__".join(prefetch))
    return "__".join(select), "__".join(prefetch)


#same as below but without classes
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
    default_error_messages = {
        'invalid': _('%(model)s instance with %(field)s %(value)r does not exist.')
    }
    description = _("Foreign Key (type determined by related field)")
    
    
    def __init__(self, serializer):
        self.serializer=serializer


    def trace(self):
        sources=get_all_sources(self.serializer)
        trails=[]
        for source in sources:
            trails.append(Trail(self.trace_source(source)))
        self.trails=trails
        return trails 
    
    
    def trace_source(self, source, include_reverse=True):
        serializer=self.serializer
        model=serializer.Meta.model
        #TODO: no need to call this func every time. save it somehow instead
        fields=get_model_accessors(model)

        trace=[]
        source=source.split('.')
        for each_field_name in source:
            #find field by its name in fields
            try:
                field = [f for f in fields if f['accessor']==each_field_name][0]
            except IndexError:
                raise Exception('No such field')
            
            if include_reverse==False and isinstance(field['field'], ForeignObjectRel):
                break
            trace.append(field['field'])
            
            #TODO: does it support GenericForeignKeys ?
            if not(isinstance(field['field'], ForeignObjectRel) or isinstance(field['field'], DjangoRelatedField)):
                # if it is not a related or reverse related field than trail is done. Source should finish here as well
                #if it does not it should give attribute error. Maybe it should be checked to see possible errors
                break
            else:
                fields=get_model_accessors(field['field'].related_model)

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
        if hasattr(field, 'get_accessor_name'):
            return field.get_accessor_name()
        else:
            #NOTE: there is also field.attname. It might be more appropriate 
            return field.name
    

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
    fields=get_model_accessors(model)

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
            fields=get_model_accessors(field['field'].related_model)

    return trace


def get_model_accessors(model):
    """
        given django model instance it returns all of its fields with its accessor(just like trail object below)
        including related and reverse related fields like;
        [{'field':field_instance, 'accessor':'parent'}, {'field':field_instance, 'accessor':'child_set'}]
    """
    res=[]
    for f in model._meta.get_fields():
        #ForeignObjectRel instances have this attribute. returns default name like 'parent_set' or related_name if it is set 
        if hasattr(f, 'get_accessor_name'):
            res.append({'field':f, 'accessor':f.get_accessor_name()})
        else:
            #I am using f.name but django uses attname in its source code even though they look like the same thing 
            #attname do not work. Found it attname is like child_id whereas name is like child. so attname is do not work for relations
            res.append({'field':f, 'accessor':f.name}) 
    return res
