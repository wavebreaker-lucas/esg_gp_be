# Frontend UI Concept: Unified Input Entry

This document outlines a proposed UI concept to handle ESG metric data entry in a unified way, accommodating both single and multiple submissions per metric/period/layer, integrating evidence uploads more closely, and working with time-based reporting.

## Core Idea: The "Input Entry" Component

Instead of separate value fields and evidence upload buttons, the UI centers around a unified "Input Entry" component for each data point. This component encapsulates:

1.  **Value Input(s):** The field(s) for `value` and/or `text_value`. Supports multi-value metrics by displaying all necessary fields defined by `MetricValueField`.
2.  **Notes:** A text area for notes specific *to this particular entry*.
3.  **Integrated Evidence:** An area *within the component* for attaching/viewing evidence files directly linked to this specific data entry. This could be a drag-and-drop zone or an "Attach File(s)" button displaying thumbnails/links of associated `ESGMetricEvidence`.

## Handling Different Metric Configurations

The UI adapts based on metric configuration flags (`aggregates_inputs`, `requires_time_reporting`):

**1. Simple Metrics (Single Submission Allowed, Not Time-Based):**
   - The UI displays **one static instance** of the "Input Entry" component for the metric/layer.
   - Saving creates/updates the single `ESGMetricSubmission` record (or potentially `ReportedMetricValue` if that's the chosen backend model for simple cases).

**2. Aggregated Metrics (Multiple Submissions Allowed - Approach B, `aggregates_inputs=True`, Not Time-Based):**
   - The UI displays an area showing a **list of existing "Input Entry" components** for the metric/layer.
   - An **"Add New Entry" button** is present. Clicking it adds a new, blank "Input Entry" component to the list.
   - Each entry in the list can be edited/deleted individually (targeting the specific `ESGMetricSubmission` via its ID).
   - A separate, clearly labelled field displays the **final calculated value** (from `ReportedMetricValue`), e.g., "Calculated Total: [Value]".

**3. Time-Based Metrics (`requires_time_reporting=True`):**
   - The UI first presents the **expected time slots** (e.g., "January 2024", "February 2024", ...) based on the assignment's date range and the metric's frequency. This could be a list, table, or use a period selector dropdown/timeline.
   - **For each time slot:**
     - If **single submission** is allowed for that metric, **one instance** of the "Input Entry" component is shown for that period.
     - If **multiple submissions** are allowed, the **list of "Input Entry" components** (plus the "Add" button) specific to *that period* is shown. The final calculated value *for that period* is also displayed nearby.
   - Saving an entry within a specific time slot ensures the `reporting_period` is set correctly on the corresponding `ESGMetricSubmission` record(s).

## Benefits

*   **Unified Experience:** Provides a consistent pattern for data entry across different metric types.
*   **Integrated Evidence:** Makes the link between a data value and its supporting evidence clear and intuitive.
*   **Handles Complexity:** Scales naturally from simple manual entries to complex, multi-input, evidence-backed, time-based scenarios.
*   **Clear Context:** Notes and evidence are tied to specific input values, improving auditability.

This approach aims to balance backend flexibility (like allowing multiple submissions via Approach B) with a more intuitive and less confusing frontend experience for the user. 