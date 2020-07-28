from .utils import *
from django.db.models.fields.reverse_related import (
    ForeignObjectRel, ManyToManyRel, ManyToOneRel, OneToOneRel,
)
from django.db.models.fields.related import (
    RelatedField as DjangoRelatedField, ForeignKey, OneToOneField
)
from django.utils.translation import gettext_lazy as _
from rest_framework.fields import SerializerMethodField

def trace_source(source, serializer):
    model=serializer.Meta.model
    fields=get_accessor(model)

    trace=[]
    source=source.split('.')
    for each_field_name in source:
        #find field by its name in fields
        try:
            field = [f for f in fields if f['accessor']==each_field_name][0]
        except IndexError:
            raise Exception('No such field')
        
        trace.append(field)
        
        #TODO: does it support GenericForeignKeys ?
        if not(isinstance(field['field'], ForeignObjectRel) or isinstance(field['field'],DjangoRelatedField)):
            break
        else:
            fields=get_accessor(field['field'].related_model)

    return trace


def get_accessor(model):
    res=[]
    for f in model._meta.get_fields():
        #ForeignObjectRel instances have this attribute. returns default name like 'parent_set' or related_name if it is set 
        if hasattr(f, 'get_accessor_name'):
            res.append({'field':f, 'accessor':f.get_accessor_name()})
        else:
            res.append({'field':f, 'accessor':f.name})
    return res

#from django docs: 
#You can refer to any ForeignKey or OneToOneField relation in the list of fields passed to select_related().
#You can also refer to the reverse direction of a OneToOneField

#returns 0 for nothing 1 for select and 2 for prefetch
def select_or_prefetch(trace):
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


def optimized_queryset(serializer):
    traces=[]
    for s in get_all_sources(serializer):
        traces.append(trace_source(s,serializer))

    select=set()
    prefetch=set()
    for trace in traces:
        s,p=select_or_prefetch(trace)
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
            trails.append(Trail(Tracer.trace_source(source, self)))
        return trails 
    
    
    @staticmethod
    def trace_source(source, serializer):
        model=serializer.Meta.model
        fields=get_accessor(model)

        trace=[]
        source=source.split('.')
        for each_field_name in source:
            #find field by its name in fields
            try:
                field = [f for f in fields if f['accessor']==each_field_name][0]
            except IndexError:
                raise Exception('No such field')
            
            trace.append(field)
            
            #TODO: does it support GenericForeignKeys ?
            if not(isinstance(field['field'], ForeignObjectRel) or isinstance(field['field'],DjangoRelatedField)):
                break
            else:
                fields=get_accessor(field['field'].related_model)

        return trace


class Trail:

    """
    Trail is a list of django field instance and its accessors as string pair such as
    [{'field':field_instance, 'accessor':'parent'}, {'field':field_instance, 'accessor':'child_set'}]

    It is generated when a tracer is applied to a serializer. Trail is the list of visited related models when a source
    is tried to be accessed. For example if from model Parent, we want to access child's toys' we would do this;

    Parent.child.toys

    Here we visit Parent Child and Toy models hence we need to prefetch all of them. Trail helps us to decide what to prefetch.
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
            return field.name
    

    def __getitem__(self, key):
        return {'field':self.fields[key], 'accessor': Trail.get_accessor(self.fields[key])}
    

    def get_as_source(self):
        return ".".join([Trail.get_accessor(f) for f in self.fields])