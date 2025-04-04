"""
Data management views.
This package is being refactored to be more modular.
"""

# Import refactored views from form_definition
from .form_definition.metrics import ESGMetricViewSet, MetricValueFieldViewSet
from .form_definition.categories import ESGFormCategoryViewSet
from .form_definition.forms import ESGFormViewSet

# Import from submissions package
from .submissions import (
    ESGMetricSubmissionViewSet,
    ESGMetricEvidenceViewSet,
    BatchEvidenceView,
    AvailableLayersView,
    SumSubmissionsByLayerView,
    ReportedMetricValueViewSet,
)

# Import from templates package
from .templates import TemplateViewSet, TemplateAssignmentView, UserTemplateAssignmentView

# Import utilities
from .utils import get_required_submission_count, attach_evidence_to_submissions

# Re-export all classes for backward compatibility
__all__ = [
    'ESGMetricEvidenceViewSet',
    'ESGFormViewSet',
    'ESGFormCategoryViewSet',
    'ESGMetricViewSet',
    'MetricValueFieldViewSet',
    'TemplateViewSet',
    'ESGMetricSubmissionViewSet',
    'TemplateAssignmentView',
    'UserTemplateAssignmentView',
    'BatchEvidenceView',
    'AvailableLayersView',
    'SumSubmissionsByLayerView',
    'ReportedMetricValueViewSet',
    'get_required_submission_count',
    'attach_evidence_to_submissions',
] 