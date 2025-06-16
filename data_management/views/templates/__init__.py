# Export views from the templates package

from .template_viewset import TemplateViewSet
from .template_assignments import TemplateAssignmentView
from .user_templates import UserTemplateAssignmentView
from .user_templates import UserTemplateAssignmentStructureView
from .form_completion import FormCompletionStatusViewSet, TemplateVerificationStatusView

__all__ = [
    'TemplateViewSet',
    'TemplateAssignmentView',
    'UserTemplateAssignmentView',
    'UserTemplateAssignmentStructureView',
    'FormCompletionStatusViewSet',
    'TemplateVerificationStatusView',
]
