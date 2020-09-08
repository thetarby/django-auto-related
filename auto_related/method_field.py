from rest_framework.fields import SerializerMethodField

class MethodField(SerializerMethodField):
    def __init__(self, *args, sources ,**kwargs):
        # if double underscore syntax is used change it to dots.
        self._auto_related_sources=[source.replace('__', '.') for source in sources]
        return super().__init__(*args, **kwargs)
