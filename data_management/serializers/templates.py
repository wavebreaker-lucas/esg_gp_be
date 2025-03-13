from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import Template, Question, QuestionChoice, TemplateAssignment

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = '__all__'

class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ['id', 'text', 'value', 'score', 'order']

class QuestionSerializer(serializers.ModelSerializer):
    choices = QuestionChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'help_text', 'is_required', 'order', 
                 'question_type', 'validation_rules', 'section', 
                 'max_score', 'choices']

class TemplateAssignmentSerializer(serializers.ModelSerializer):
    template = TemplateSerializer(read_only=True)
    company = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = TemplateAssignment
        fields = '__all__' 