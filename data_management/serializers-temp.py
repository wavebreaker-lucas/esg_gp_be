from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from .models import (
    Template, Question, QuestionChoice, TemplateAssignment,
    BoundaryItem, EmissionFactor, ESGData, DataEditLog
)

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

class BoundaryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BoundaryItem
        fields = '__all__'

class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = '__all__'

class ESGDataSerializer(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    boundary_item = BoundaryItemSerializer(read_only=True)
    submitted_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False
    )
    verified_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = ESGData
        fields = '__all__'

class DataEditLogSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False
    )
    esg_data = ESGDataSerializer(read_only=True)

    class Meta:
        model = DataEditLog
        fields = '__all__'