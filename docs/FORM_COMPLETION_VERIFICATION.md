# Form Completion & Verification System

This document covers the **form-level completion and verification system** implemented in the ESG platform. This system provides a structured workflow for users to complete forms and administrators to verify them.

## 📋 Table of Contents

- [Overview](#overview)
- [Workflow](#workflow)
- [Data Models](#data-models)
- [API Endpoints](#api-endpoints)
- [Admin Interface](#admin-interface)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

### What is Form-Level Verification?

The form-level verification system allows:
- **Users**: Complete forms within template assignments
- **Baker Tilly Admins**: Verify completed forms or send them back for changes
- **System**: Track completion and verification progress across entire template assignments

### Why Form-Level?

Form-level verification was chosen as the optimal granularity because:
- ✅ **Natural unit of work**: Users complete forms, not individual metrics
- ✅ **Logical grouping**: Related metrics are verified together
- ✅ **Manageable scope**: 5-15 metrics per form (reasonable verification workload)
- ✅ **Progressive verification**: Can verify forms as they're completed
- ✅ **Clear accountability**: Easy to see which forms are verified vs pending

## 🔄 Workflow

### Sequential Workflow: Complete → Verify

```
📝 DRAFT → ✅ USER COMPLETE → 👀 PENDING VERIFICATION → ✓ ADMIN VERIFY
  ↑                              ↓
  ←--------← REVISION REQUIRED ←-←
```

### State Transitions

| Current State | User Action | Admin Action | Next State |
|---------------|-------------|--------------|------------|
| `DRAFT` | Mark Complete | - | `PENDING_VERIFICATION` |
| `REVISION_REQUIRED` | Mark Complete | - | `PENDING_VERIFICATION` |
| `PENDING_VERIFICATION` | - | Verify | `VERIFIED` |
| `PENDING_VERIFICATION` | - | Send Back | `REVISION_REQUIRED` |
| `VERIFIED` | - | Send Back | `REVISION_REQUIRED` |

### Business Rules

1. **Users can only complete forms** for their accessible layers
2. **Only Baker Tilly admins can verify** forms
3. **Forms must be completed** before they can be verified
4. **Verified forms can be sent back** for changes if needed
5. **Template assignments track overall progress** based on form completion/verification

## 📊 Data Models

### FormCompletionStatus

The core model tracking completion and verification status for each form.

```python
class FormCompletionStatus(models.Model):
    # References
    form_selection = ForeignKey(TemplateFormSelection)
    assignment = ForeignKey(TemplateAssignment)
    layer = ForeignKey(LayerProfile)
    
    # User completion fields
    is_completed = BooleanField(default=False)
    completed_at = DateTimeField(null=True, blank=True)
    completed_by = ForeignKey(CustomUser, null=True, blank=True)
    
    # Admin verification fields
    is_verified = BooleanField(default=False)
    verified_at = DateTimeField(null=True, blank=True)
    verified_by = ForeignKey(CustomUser, null=True, blank=True)
    verification_notes = TextField(blank=True)
```

### Key Properties

```python
# Status properties
form_status.status  # Returns: "DRAFT", "PENDING_VERIFICATION", "VERIFIED", "REVISION_REQUIRED"
form_status.get_status_display()  # Returns: "Draft", "Pending Verification", "Verified", "Revision Required"

# Business logic
form_status.can_complete()  # Can user mark as complete?
form_status.can_verify()    # Can admin verify?

# Actions
form_status.mark_completed(user)
form_status.mark_verified(admin_user, notes="")
form_status.send_back_for_changes(admin_user, reason="")
```

### TemplateAssignment Extensions

```python
# Verification progress tracking
assignment.verification_progress  # Returns detailed progress dict
assignment.is_fully_completed     # All forms completed?
assignment.is_fully_verified      # All forms verified?
```

## 🌐 API Endpoints

### Base URL: `/api/form-completion/`

### 1. List & Filter Form Completion Status

```http
GET /api/form-completion/
```

**Query Parameters:**
- `assignment_id` - Filter by template assignment
- `layer_id` - Filter by layer
- `form_id` - Filter by specific form
- `is_completed` - Filter by completion status (`true`/`false`)
- `is_verified` - Filter by verification status (`true`/`false`)
- `status` - Filter by status (`DRAFT`, `PENDING_VERIFICATION`, `VERIFIED`, `REVISION_REQUIRED`)

**Examples:**
```http
GET /api/form-completion/?assignment_id=1&status=PENDING_VERIFICATION
GET /api/form-completion/?layer_id=5&form_id=3&is_completed=true
GET /api/form-completion/?status=REVISION_REQUIRED
```

**Response:**
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "form_name": "Energy Consumption",
      "form_code": "HKEX-A2.1",
      "layer_name": "GreenPoint Technologies",
      "assignment_name": "HKEX ESG Reporting 2024",
      "is_completed": true,
      "completed_at": "2024-01-15T10:30:00Z",
      "completed_by_name": "john.doe",
      "is_verified": false,
      "verified_at": null,
      "verified_by_name": null,
      "verification_notes": "",
      "status": "PENDING_VERIFICATION",
      "status_display": "Pending Verification",
      "can_verify": true,
      "can_complete": false
    }
  ]
}
```

### 2. User Completes Form

#### Option A: Using FormCompletionStatus ID (Original)
```http
POST /api/form-completion/{id}/complete/
```

#### Option B: Using Form/Assignment IDs (User-Friendly)
```http
POST /api/form-completion/complete-by-ids/
```

**Request Body:**
```json
{
  "form_id": 3,
  "assignment_id": 1,
  "layer_id": 5  // Optional - defaults to user's layer
}
```

**Permissions:** User must have access to the form's layer

**Response:**
```json
{
  "message": "Form marked as complete successfully",
  "form_status": {
    "id": 1,
    "status": "PENDING_VERIFICATION",
    "is_completed": true,
    "completed_at": "2024-01-15T10:30:00Z"
  },
  "created_new_record": false
}
```

### 3. Admin Verifies Form

#### Option A: Using FormCompletionStatus ID (Original)
```http
POST /api/form-completion/{id}/verify/
```

#### Option B: Using Form/Assignment IDs (User-Friendly)
```http
POST /api/form-completion/verify-by-ids/
```

**Request Body:**
```json
{
  "form_id": 3,
  "assignment_id": 1,
  "layer_id": 5,  // Optional - defaults to assignment's layer
  "verification_notes": "Data looks accurate and complete. Verified."
}
```

**Permissions:** Baker Tilly Admin only

**Response:**
```json
{
  "message": "Form verified successfully",
  "form_status": {
    "id": 1,
    "status": "VERIFIED",
    "is_verified": true,
    "verified_at": "2024-01-15T14:30:00Z",
    "verified_by_name": "admin.user",
    "verification_notes": "Data looks accurate and complete. Verified."
  }
}
```

### 4. Admin Sends Form Back

#### Option A: Using FormCompletionStatus ID (Original)
```http
POST /api/form-completion/{id}/send_back/
```

#### Option B: Using Form/Assignment IDs (User-Friendly)
```http
POST /api/form-completion/send-back-by-ids/
```

**Request Body:**
```json
{
  "form_id": 3,
  "assignment_id": 1,
  "layer_id": 5,  // Optional - defaults to assignment's layer
  "reason": "Please update the energy consumption values for Q3 and Q4."
}
```

**Permissions:** Baker Tilly Admin only

**Response:**
```json
{
  "message": "Form sent back for changes successfully",
  "form_status": {
    "id": 1,
    "status": "REVISION_REQUIRED",
    "is_completed": true,
    "is_verified": false,
    "revision_required": true,
    "verification_notes": "Sent back for changes: Please update the energy consumption values for Q3 and Q4."
  }
}
```

### 5. Template Verification Overview

```http
GET /api/template-verification/{assignment_id}/verification_status/
```

**Response:**
```json
{
  "assignment_id": 1,
  "assignment_name": "HKEX ESG Reporting 2024",
  "layer_name": "GreenPoint Technologies",
  "total_forms": 8,
  "completed_forms": 6,
  "verified_forms": 4,
  "pending_verification": 1,
  "revision_required": 1,
  "draft_forms": 2,
  "completion_progress_percentage": 75.0,
  "verification_progress_percentage": 50.0,
  "is_fully_completed": false,
  "is_fully_verified": false,
  "assignment_status": "In Progress",
  "form_statuses": [
    {
      "id": 1,
      "form_name": "Energy Consumption",
      "status": "VERIFIED",
      "completed_at": "2024-01-15T10:30:00Z",
      "verified_at": "2024-01-15T14:30:00Z"
    }
  ]
}
```



## ⚙️ Admin Interface

### Django Admin Features

1. **List View**: Shows all forms with completion and verification status
2. **Filtering**: Filter by completion, verification, layer, template
3. **Search**: Search by company name, form name, verification notes
4. **Fieldsets**: Organized into Form Info, Completion, and Verification sections

### Admin URL
```
http://localhost:8000/admin/data_management/formcompletionstatus/
```

## 📝 Examples

### Complete User Workflow

```python
# 1. User fills out form data (separate process)
# 2. User marks form as complete
form_status = FormCompletionStatus.objects.get(id=1)
form_status.mark_completed(user)

# 3. Admin reviews and verifies
form_status.mark_verified(admin_user, "Data verified and accurate")

# 4. Check assignment progress
assignment = form_status.assignment
progress = assignment.verification_progress
print(f"Verified: {progress['verified_forms']}/{progress['total_forms']}")
```

### API Usage Examples

```bash
# Get forms pending verification
curl -X GET "/api/form-completion/?status=PENDING_VERIFICATION" \
  -H "Authorization: Bearer {token}"

# Get forms requiring revision
curl -X GET "/api/form-completion/?status=REVISION_REQUIRED" \
  -H "Authorization: Bearer {token}"

# Complete a form (Option A - using FormCompletionStatus ID)
curl -X POST "/api/form-completion/1/complete/" \
  -H "Authorization: Bearer {token}"

# Complete a form (Option B - user-friendly with form/assignment IDs)
curl -X POST "/api/form-completion/complete-by-ids/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"form_id": 3, "assignment_id": 1}'

# Verify a form (Option A - using FormCompletionStatus ID)
curl -X POST "/api/form-completion/1/verify/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"verification_notes": "All data looks good"}'

# Verify a form (Option B - user-friendly with form/assignment IDs)
curl -X POST "/api/form-completion/verify-by-ids/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"form_id": 3, "assignment_id": 1, "verification_notes": "All data looks good"}'

# Send form back (Option A - using FormCompletionStatus ID)
curl -X POST "/api/form-completion/1/send_back/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Please update Q3 data"}'

# Send form back (Option B - user-friendly with form/assignment IDs)
curl -X POST "/api/form-completion/send-back-by-ids/" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"form_id": 3, "assignment_id": 1, "reason": "Please update Q3 data"}'

# Get assignment verification overview
curl -X GET "/api/template-verification/1/verification_status/" \
  -H "Authorization: Bearer {token}"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. "Form cannot be marked as complete"
**Cause**: Form is already verified  
**Solution**: Check if form needs to be sent back for changes first

#### 2. "Only Baker Tilly admins can verify forms"
**Cause**: User doesn't have admin permissions  
**Solution**: Ensure user has `is_baker_tilly_admin=True` or is staff/superuser

#### 3. "Form cannot be verified - it must be completed first"
**Cause**: Trying to verify a form that hasn't been completed  
**Solution**: User must mark form as complete first

#### 4. FormCompletionStatus doesn't exist
**Cause**: No FormCompletionStatus record created for the form  
**Solution**: These are usually auto-created, but can be created manually:

```python
FormCompletionStatus.objects.get_or_create(
    form_selection=form_selection,
    assignment=assignment,
    layer=target_layer
)
```

### Debug Commands

```python
# Check form completion status
form_status = FormCompletionStatus.objects.get(id=1)
print(f"Status: {form_status.status}")
print(f"Can complete: {form_status.can_complete()}")
print(f"Can verify: {form_status.can_verify()}")

# Check assignment progress
assignment = TemplateAssignment.objects.get(id=1)
print(assignment.verification_progress)
```

### Logging

Enable detailed logging in `settings.py`:

```python
LOGGING = {
    'loggers': {
        'data_management.views.templates.form_completion': {
            'level': 'DEBUG',
            'handlers': ['console'],
        },
    },
}
```

## 🔄 Migration from Old System

If migrating from metric-level or template-level verification:

1. **Export existing verification data**
2. **Create FormCompletionStatus records** for all existing assignments
3. **Map verification status** appropriately
4. **Test the new workflow** thoroughly
5. **Deprecate old verification endpoints**

---

## 📞 Support

For questions or issues with the form completion and verification system:

1. Check this documentation
2. Review the [troubleshooting section](#troubleshooting)
3. Check Django admin for data integrity
4. Contact the development team

**Last Updated**: January 2024  
**Version**: 1.0.0 