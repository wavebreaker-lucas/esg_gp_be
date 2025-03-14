from rest_framework import serializers
from accounts.models import CustomUser, LayerProfile
from ..models import Template, Question, QuestionChoice, TemplateAssignment

class QuestionChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionChoice
        fields = ['id', 'text', 'value', 'order', 'score']

class QuestionSerializer(serializers.ModelSerializer):
    choices = QuestionChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'help_text', 'is_required', 'order', 
                 'question_type', 'question_category', 'validation_rules', 
                 'section', 'unit_type', 'custom_unit', 'requires_evidence',
                 'has_score', 'max_score', 'choices']

class TemplateSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'name', 'description', 'category', 'template_type',
                 'is_active', 'version', 'created_at', 'updated_at', 
                 'created_by', 'reporting_period', 'questions']

    def create(self, validated_data):
        questions_data = validated_data.pop('questions')
        template = Template.objects.create(**validated_data)
        
        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(template=template, **question_data)
            
            for choice_data in choices_data:
                QuestionChoice.objects.create(question=question, **choice_data)
        
        return template

    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', [])
        # Update template fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle questions update
        if questions_data:
            # Remove existing questions and their choices
            instance.questions.all().delete()
            
            # Create new questions and choices
            for question_data in questions_data:
                choices_data = question_data.pop('choices', [])
                question = Question.objects.create(template=instance, **question_data)
                
                for choice_data in choices_data:
                    QuestionChoice.objects.create(question=question, **choice_data)
        
        return instance

class TemplateAssignmentSerializer(serializers.ModelSerializer):
    template = TemplateSerializer(read_only=True)
    company = serializers.PrimaryKeyRelatedField(queryset=LayerProfile.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = TemplateAssignment
        fields = '__all__' 