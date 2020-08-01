# AutoRelated
AutoRelated package automatically creates correct use of `select_related()`, `prefetch_related()` and `only()` methods of django for django-rest serializers. 

  - Pass your serializer to Tracer object
  - Build your query with the returned parameters
  - Your query is optimized

Note that a SerializerMethodField which causes n+1 problem cannot be solved by AutoRelated since inspecting what is happening in a method field is really hard. To solve it you can still pass extra arguments to select or prefetch_related in queryset attribute of class based views.

## Requirements

AutoRelated is developed and tested against;

* Django version: 3.0, 3.0.5
* Django REST framework version: 3.10.3, 3.11.0
* Python version: 3.6, 3.7, 3.8

It requires only:

* Django
* Django REST framework

For development in addition to above:

* Django Debug Toolbar


## Installation
For now only git clone will work.

## Usage

If you have a serializer like this defined in your serializers.py file;
```python
from restframework import serializers

class SomeSerializer(serializer.Serializers):
    field=SomeotherSerializer(many=True)
    .
    .
    .

```

You can use it in your views like this;
```python
from auto_related.tracer import Trace, optimized_queryset_given_trails
from rest_framework import status,generics

class ParentList(generics.ListAPIView):
    serializer_class = SomeSerializer
    def get_queryset(self):
        t=Tracer(StudentSerializer())
        traces=t.trace()
        s,p=optimized_queryset_given_trails(traces)
        return SomeSerializer.model.objects.select_related(*s)\
                                            .prefetch_related(*p)\
                                            .only(*t.build_only())

```

Or you can use mixins that basically do the same thing

```python
from auto_related.mixin import ViewMixin, ViewMixinWithOnlyOptim
from rest_framework import status,generics

#this mixin does not use only() and defer() optimization
class ParentList(ViewMixin, generics.ListAPIView):
    serializer_class = SomeSerializer
    # you can pass extra parameters here for SerializerMethodFields
    queryset=Parent.objects.all() 

#this mixin uses only() and defer() optimization
class ParentList(ViewMixinWithOnlyOptim, generics.ListAPIView):
    serializer_class = SomeSerializer
    queryset=Parent.objects.all()
```

## How It Works

First a util function `get_all_sources()` inspects a serializer deeply by iterating over all of its fields including fields of the nested serializers. Say that you have serializer like this;

```python

class SomeSerializer(serializer.Serializers):
    field=SomeOtherSerializer(many=True, source='some_other')
    text=CharField()

class SomeOtherSerializer(serializer.Serializers):
    name=CharField()
    attr=IntegerField()     
```

then all sources of a serializer is obtained by;
```python
get_all_sources(SomeSerializer)
#returns ['field', 'text',' some_other.name', 'some_other.attr']
```

which is all attributes that this serializer will access when it is passed with a data. We somehow have to inspect those sources to decide what to prefetch.

Then, the tracer object traces all these sources on model that this serializer is assigned to. For example some_other.attr source first visits some_other relational field and then attr integerfield of SomeOther model. Note that those fields has nothing to do with rest framework fields, they are django's field objects. Fields helps us to decide what to prefetch. For instance, If a field is a related or reverse related field then it could be said that  it should be prefetched. However there are two methods to do that in django which are `select_related` and `prefetch_related`. Fields classes helps to decide which is which. For example a onetoone field can be prefetched using `select_related` but we should use `prefetch_related` for manytomany fields or reverse related fields etc..
## Development

Want to contribute? Great!

Currently no automated tests. You can clone the repo and run the test project; 

```sh
$ cd projectfolder/autorelated/tests
$ python manage.py runserver
```
Django toolbar is installed in the project so that you can examine how many queries are executed and lots of other things as well for testing purposes. For instance you can go to `http://localhost:8080/test/course` and `http://localhost:8080/test/course/slow` to compare speed and query count difference between auto_related applied and not applied queries. Each url in the test project has its counter part `...url/slow` which does not use auto_related and only use `model.objects.all()` as queryset. 

## Todos

 - Writing Tests
 - Performance improvements by caching some functions which are called with same parameters many times
 - Examining queryset or model instances passed to serializers to check if they are cached and properly configured and if not optimize them automatically.
 - AutoRelated does not work with serializers which has SerializerMethodField which causes n+1 problem. That problem might be solved by overriding or patching queryset classes within method field. 
License
----

MIT

