from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from testerapp.models import *
import sys
sys.path.insert(0, "../..")
from auto_related.utils import *
from auto_related.mixin import *
from auto_related.method_field import MethodField as SerializerMethodField
class ChildChildSerializer(ModelSerializer):
    class Meta:
        model = ChildChild
        fields = '__all__'


class ChildSerializer(ModelSerializer):
    child=ChildChildSerializer()
    class Meta:
        model = Child
        fields = '__all__'


class ParentSerializer(ModelSerializer):
    child=ChildSerializer()
    slug_related_childchild_text=serializers.SlugRelatedField(
        read_only=True,
        slug_field='text',
        source='child.child'
     )
    string_related_child = serializers.StringRelatedField(source='child')
    
    class Meta:
        model = Parent
        fields = '__all__'


class HyperLinkedParentSerializer(serializers.HyperlinkedModelSerializer):
    hyperlinked_child = serializers.HyperlinkedRelatedField(many=True, view_name='parent-detail', read_only=True, source='child', lookup_field='text')
    class Meta:
        model = Parent
        fields = '__all__'


class ChildChildSerializer2(ModelSerializer):
    parents=ChildSerializer(many=True)
    slug_related_parents=serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='text',
        source='parents'
     )
    class Meta:
        model = ChildChild
        fields = '__all__'


class CourseSerializer(ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'


class TeacherSerializer(ModelSerializer):
    teaches=CourseSerializer(many=True)
    class Meta:
        model = Teacher
        fields = ['id', 'text', 'teaches'] # big_text_field is not included to see the effect of using only()


class StudentSerializer(ModelSerializer):
    courses=CourseSerializer(many=True)
    parent = ParentSerializer(many=False)
    class Meta:
        model = Student
        fields = '__all__'


class CourseSerializer2(ModelSerializer):
    teached_by=TeacherSerializer(many=True, source='teacher_set')
    taken_by=StudentSerializer(many=True, source='student_set')
    class Meta:
        model = Course
        fields = '__all__'


# a super teacher is a teacher who has more than 10 students
# lets implement it with a method field
class IsSuperTeacherSerializer(ModelSerializer):
    is_super_teacher= SerializerMethodField(sources=['teaches__student_set'])

    def get_is_super_teacher(self, obj):
        return sum([course.student_set.count() for course in obj.teaches.all()])


    class Meta:
        model = Teacher
        fields = ['id', 'text', 'teaches', 'is_super_teacher']


#this serializer shows that a method field could work event it is nested in another serializer 
class CourseSerializerWithSuperTeacherSerializer(ModelSerializer):
    teached_by=IsSuperTeacherSerializer(many=True, source='teacher_set')
    class Meta:
        model = Course
        fields = '__all__'


class UserSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, source='user_name') 


class CommentSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=200)
    user= UserSerializer()


class SubSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    comments = CommentSerializer(many=True, source='comment_set')


class BlogPostSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    comment = CommentSerializer()
    sub=SubSerializer()
