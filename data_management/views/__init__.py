"""
Data management views.
This package is being refactored to be more modular.
"""

# Import classes from the modules for backward compatibility
from .modules.evidence import ESGMetricEvidenceViewSet
from .templates import (
    ESGFormViewSet,
    ESGFormCategoryViewSet,
    ESGMetricViewSet,
    TemplateViewSet,
    ESGMetricSubmissionViewSet,
    TemplateAssignmentView,
    UserTemplateAssignmentView
)

# Re-export all classes for backward compatibility
__all__ = [
    'ESGMetricEvidenceViewSet',
    'ESGFormViewSet',
    'ESGFormCategoryViewSet',
    'ESGMetricViewSet',
    'TemplateViewSet',
    'ESGMetricSubmissionViewSet',
    'TemplateAssignmentView',
    'UserTemplateAssignmentView'
] 