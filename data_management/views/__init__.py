"""
Data management views.
This package is being refactored to be more modular.
"""

# Import refactored views from form_definition
from .form_definition import (
    ESGFormCategoryViewSet, ESGFormViewSet
)

# Import from submissions package
from .submissions import (
    ESGMetricSubmissionViewSet, ESGMetricEvidenceViewSet, BatchEvidenceView,
    AvailableLayersView, SumSubmissionsByLayerView,
    ReportedMetricValueViewSet
)

# Import from templates package
from .templates import TemplateViewSet, TemplateAssignmentView, UserTemplateAssignmentView, UserTemplateAssignmentStructureView

# Import utilities
from .utils import get_required_submission_count, attach_evidence_to_submissions  # attach_evidence_to_submissions is kept for backward compatibility

# Import from aggregation package
# from .aggregation import AggregatedMetricDataView # Commented out as it doesn't exist yet

# Re-export all classes for backward compatibility
__all__ = [
    'ESGMetricSubmissionViewSet',
    'ESGMetricEvidenceViewSet',
    'BatchEvidenceView',
    'AvailableLayersView',
    'SumSubmissionsByLayerView',
    'ReportedMetricValueViewSet',
    'TemplateViewSet',
    'TemplateAssignmentView',
    'UserTemplateAssignmentView',
    'UserTemplateAssignmentStructureView',
    'ESGFormCategoryViewSet',
    'ESGFormViewSet',
    # 'AggregatedMetricDataView', # Commented out
    'get_required_submission_count',
    'attach_evidence_to_submissions',
] 