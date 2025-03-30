"""
Data management views.
This package is being refactored to be more modular.
"""

# Import classes from the modules for backward compatibility
from .modules.evidence import ESGMetricEvidenceViewSet

# Import refactored views
from .metrics import ESGMetricViewSet
from .evidence import BatchEvidenceView
from .form_categories import ESGFormCategoryViewSet
from .template_assignments import TemplateAssignmentView
from .user_templates import UserTemplateAssignmentView
from .template_viewset import TemplateViewSet
from .submissions import ESGMetricSubmissionViewSet
from .forms import ESGFormViewSet
from .schema_registry import SchemaRegistryViewSet

# Re-export all classes for backward compatibility
__all__ = [
    'ESGMetricEvidenceViewSet',
    'ESGFormViewSet',
    'ESGFormCategoryViewSet',
    'ESGMetricViewSet',
    'TemplateViewSet',
    'ESGMetricSubmissionViewSet',
    'TemplateAssignmentView',
    'UserTemplateAssignmentView',
    'BatchEvidenceView',
    'SchemaRegistryViewSet',
    'BatchSubmissionViewSet'
] 