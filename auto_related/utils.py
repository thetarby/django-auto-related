from rest_framework.relations import (
    ManyRelatedField,
    PrimaryKeyRelatedField,
    HyperlinkedRelatedField
)
from rest_framework.serializers import BaseSerializer, ListSerializer
from inspect import isclass
import warnings

"""
NOTE:
HyperlinkedIdentityFields' source is also * like SerializerMethodField. 
Since HyperlinkedIdentityField uses field of the object itself it may not need optimization other than only() and defer()
"""


#TODO: When used with primarykeyrelated field it does not include source field or pk 
#pk may be included but when accesing a models field pk is not listed there. So some changes are required to do that

#TODO:HyperlinkedRelatedField uses pk as default but can access to other fields of a model with a different lookup_key parameter that requires a db hit.

#NOTE: if output of this will be given to only or defer then reverse relations other than onetoone should be removed(django doesnt support it)
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


def patch_cursor():
    """
    when called in django environment it patches django cursor object
    so that on each db hit it prints how many queries executed. 
    Useful to detect n+1 problems but should not be used in production. 
    """
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


