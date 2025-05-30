# Unified Viewable Layers Endpoint & Data Scoping Plan

This document outlines the implementation of the `UnifiedViewableLayersView` endpoint and the subsequent plan (Phase 4) for ensuring correct data scoping across related APIs, particularly for the "View As" functionality for Baker Tilly Admins.

## Phase 1 & 2: `UnifiedViewableLayersView` Implementation

**Objective:** Provide a single, consistent API endpoint for frontend features (Dashboard, Submission Status, Submission Viewing) to fetch a list of viewable layers/entities based on user role and context.

**Endpoint:** `GET /api/dashboard/viewable-layers/`

**View Class:** `data_management.views.dashboard_api.UnifiedViewableLayersView`

**Permissions:** `IsAuthenticated` (internal logic handles role-specific behavior)

**Key Backend Components:**
*   **`accounts.services.layer_services.py`**:
    *   `get_specific_layer_instance(layer_proxy)`: Helper to get specific layer model instances.
    *   `get_layer_parent_specific(layer_instance)`: Helper to get a specific parent layer instance.
    *   `get_layer_children_specific(layer_instance)`: Helper to get specific child layer instances.
    *   `get_full_group_layer_data(group_id)`: Service function that fetches the complete hierarchical data for a given `group_id` (Group, its Subsidiaries, and their Branches). Used for Baker Tilly Admin "View As" scenario. Returns raw model instances in a structured dictionary.
    *   `get_user_accessible_layer_data(user, assignment_id=None)`: Service function that fetches specific layer model instances accessible to the given `user`, optionally filtered by the context of a `TemplateAssignment` (including its relevant parents, children, and grandchildren). Used for Company Admins and other non-BT Admin roles, or BT Admins not using "View As".

**Query Parameters for `GET /api/viewable-layers/`:**

*   `view_as_group_id` (integer, optional):
    *   **Target User:** Baker Tilly Admins.
    *   **Function:** If provided by a Baker Tilly Admin, the endpoint returns a flat list representing the full structure (group, all its subsidiaries, all their branches) of the specified `view_as_group_id`.
    *   If provided by a non-BT Admin, a 403 Forbidden error is returned.
*   `assignment_id` (integer, optional):
    *   **Target User:** Company Admins or other non-BT Admin roles (ignored if `view_as_group_id` is active for a BT Admin).
    *   **Function:** If provided, the list of layers normally accessible to the user is further filtered to those relevant to the context of this specific `TemplateAssignment` (i.e., the assignment's direct layer, its accessible parents, and its accessible children/grandchildren).

**Output Format (Consistent for all successful responses):**

A flat JSON array of layer objects. Each object has the following structure:
```json
[
  {
    "id": 123, // Integer, Primary key of the layer
    "name": "Layer Name", // String, e.g., company_name
    "type": "GROUP" / "SUBSIDIARY" / "BRANCH", // String, from LayerTypeChoices
    "location": "Location String", // String, e.g., company_location
    "parentId": 456 // Integer or null, ID of the parent layer in the list
  },
  // ... more layer objects
]
```
The list is sorted by layer type (Group, then Subsidiary, then Branch) and then by name.

**Behavior Summary:**

1.  **Baker Tilly Admin with `view_as_group_id`:**
    *   Calls `get_full_group_layer_data(view_as_group_id)`.
    *   Transforms the full hierarchical structure into the flat list DTO.
    *   Returns the complete structure of the target group.

2.  **Baker Tilly Admin WITHOUT `view_as_group_id`:**
    *   Falls into the "Company Admin / Other Users" path.
    *   Calls `get_user_accessible_layer_data(bt_admin_user, assignment_id)`.
    *   Returns layers directly accessible to the BT Admin account (potentially few or none, depending on setup), optionally filtered by `assignment_id`.

3.  **Company Admin / Other Non-BT Admin Users:**
    *   `view_as_group_id` is ignored or disallowed.
    *   Calls `get_user_accessible_layer_data(user, assignment_id)`.
    *   Returns layers accessible to that user, optionally filtered by `assignment_id` to provide context around a specific assignment (assignment's layer + relevant accessible hierarchy).

**Frontend Responsibility (Phase 3 - To be done by Frontend Team):**

*   Update UI features (Dashboard, Submission Status, Submission Viewing) to call `GET /api/viewable-layers/`.
*   Pass `view_as_group_id` when a Baker Tilly Admin is "Viewing As" a specific group.
*   Pass `assignment_id` when the context is specific to a `TemplateAssignment` for non-BT Admin users.
*   Process the returned flat list (using `id` and `parentId`) to render the layer hierarchy or list as needed.

---

## Phase 4: Update Other Data APIs for `effective_group_id` (Future Work)

**Objective:** Ensure that all backend APIs providing data *for* the displayed layers (e.g., emissions, statuses, metrics) correctly respect the "View As" context established by the `effective_group_id` (which is derived from `view_as_group_id` on the frontend).

**Why Phase 4 is Crucial:**

*   **Correct Data Scoping:** When a BT Admin "Views As" Group X, all data shown (emissions, submission counts, etc.) must pertain *only* to Group X and its constituents. Without Phase 4, data APIs might show data based on the BT Admin's general permissions, not confined to Group X.
*   **Security:** Prevents data leakage. If a `layer_id` is requested, Phase 4 ensures this layer belongs to the `effective_group_id` the BT Admin is "Viewing As." It also prevents non-BT Admins from spoofing a group context.

**APIs to Update (Examples - identify all relevant ones):**

*   `data_management.views.dashboard_api.total_emissions_api`
*   `data_management.views.dashboard_api.emissions_time_series_api`
*   `data_management.views.dashboard_api.vehicle_emissions_breakdown_api`
*   Any APIs used for fetching submission statuses per layer/metric.
*   Any APIs used for fetching detailed submission data.

**Required Changes for Each Data API in Phase 4:**

1.  **Accept `effective_group_id` Parameter:**
    *   Modify the API to accept an optional query parameter, e.g., `effective_group_id` (or `group_context_id`).

2.  **Implement Backend Logic:**
    *   Get the `effective_group_id` from request parameters.
    *   Get `request.user` and determine if they are a Baker Tilly Admin.
    *   **If `effective_group_id` is provided:**
        *   **Security Check 1 (Role):** Verify `request.user` is a Baker Tilly Admin. If not, and `effective_group_id` attempts to scope outside the user's own group, return 403 Forbidden or ignore.
        *   **Security Check 2 (Context Confinement - if `layer_id` also present):** If the API also accepts a `layer_id`, verify that this `layer_id` genuinely belongs to the hierarchy of the `effective_group_id`. If not, return 403 or 404.
        *   **Data Scoping:** All database queries **must** be filtered to only include data related to this `effective_group_id`. This requires ensuring your models (`CalculatedEmissionValue`, `ESGMetricSubmission`, `ReportedMetricValue`, `TemplateAssignment`, etc.) can be traced back to a "group" concept, likely via the `LayerProfile` they are associated with.
            *   Example: `queryset.filter(layer__<path_to_group_id_on_layer_model>=effective_group_id)`
    *   **If `effective_group_id` is NOT provided (or user is not BT Admin):**
        *   The API scopes data based on the `request.user`'s own group and permissions, as it likely does currently (e.g., using `get_accessible_layers` to filter by allowed `layer_id`s).

**Example Data Model Consideration for Scoping:**

For `effective_group_id` filtering to work, your `LayerProfile` model (or the specific `GroupLayer`, `SubsidiaryLayer`, `BranchLayer` models) needs a way to identify which "client group" it ultimately belongs to.
*   If `SubsidiaryLayer` has a `group_layer` ForeignKey to `GroupLayer`, and `BranchLayer` has a `subsidiary_layer` ForeignKey, you can traverse up to find the top-level `GroupLayer` ID.
*   Alternatively, `LayerProfile` could have a direct (possibly denormalized) `client_group_id` field indicating the top-level group it pertains to.

**Frontend Responsibility for Phase 4:**

*   When calling these data APIs, if a BT Admin is "Viewing As" (i.e., an `effectiveGroupId` is active in the frontend state), the frontend must pass this `effectiveGroupId` as the `effective_group_id` parameter to these data APIs.

This phased approach ensures that the UI for selecting and viewing layer structures is robust first, followed by the critical work of ensuring all data displayed within that structure is correctly scoped and secured. 