# Emission Factors API Documentation

This document describes the REST API endpoints for managing GHG Emission Factors. These endpoints are **restricted to Baker Tilly administrators only**.

## Base URL
All endpoints are under: `/api/emission-factors/`

## Authentication
- All endpoints require authentication
- Only users with `is_baker_tilly_admin = True` can access these endpoints
- Include JWT token in Authorization header: `Authorization: Bearer <token>`

## Endpoints Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/emission-factors/` | List all emission factors (with filtering/search) |
| POST | `/api/emission-factors/` | Create a new emission factor |
| GET | `/api/emission-factors/{id}/` | Get specific emission factor |
| PUT | `/api/emission-factors/{id}/` | Update specific emission factor |
| PATCH | `/api/emission-factors/{id}/` | Partially update emission factor |
| DELETE | `/api/emission-factors/{id}/` | Delete specific emission factor |
| POST | `/api/emission-factors/bulk_create/` | Bulk create emission factors |
| DELETE | `/api/emission-factors/bulk_delete/` | Bulk delete emission factors |
| GET | `/api/emission-factors/categories/` | Get categories and subcategories |
| GET | `/api/emission-factors/search_factors/` | Advanced search |
| GET | `/api/emission-factors/export_template/` | Download CSV template |

---

## 1. List Emission Factors

**GET** `/api/emission-factors/`

Returns a paginated list of emission factors with filtering and search capabilities.

### Query Parameters

#### Filtering
- `category` - Filter by category (exact match or contains)
- `category__icontains` - Case-insensitive partial match for category
- `sub_category` - Filter by subcategory (exact match or contains)  
- `sub_category__icontains` - Case-insensitive partial match for subcategory
- `year` - Filter by exact year
- `year__gte` - Filter by year greater than or equal to
- `year__lte` - Filter by year less than or equal to
- `region` - Filter by region (exact match or contains)
- `region__icontains` - Case-insensitive partial match for region
- `scope` - Filter by emission scope (exact match)
- `activity_unit` - Filter by activity unit (exact match or contains)
- `activity_unit__icontains` - Case-insensitive partial match for activity unit

#### Search
- `search` - Text search across name, category, sub_category, and source fields

#### Ordering
- `ordering` - Order by field(s). Available fields: `year`, `category`, `sub_category`, `value`, `name`
- Default ordering: `-year,category,sub_category`
- Use `-` prefix for descending order (e.g., `-year`)

### Example Requests

```bash
# Get all emission factors
GET /api/emission-factors/

# Get transport emission factors for 2025
GET /api/emission-factors/?category=transport&year=2025

# Search for diesel factors
GET /api/emission-factors/?search=diesel

# Get electricity factors ordered by value
GET /api/emission-factors/?category=electricity&ordering=value
```

### Response Format

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/emission-factors/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Diesel - Passenger Car",
      "category": "transport",
      "sub_category": "transport_cars_diesel",
      "activity_unit": "liters",
      "value": "2.6460000",
      "factor_unit": "kgCO2e/liter",
      "year": 2025,
      "region": "ALL",
      "scope": "1"
    }
  ]
}
```

---

## 2. Create Emission Factor

**POST** `/api/emission-factors/`

Creates a new emission factor.

### Request Body

```json
{
  "name": "New Emission Factor",
  "category": "transport",
  "sub_category": "transport_new_category",
  "activity_unit": "liters",
  "value": "2.5000",
  "factor_unit": "kgCO2e/liter",
  "year": 2025,
  "region": "ALL",
  "scope": "1",
  "source": "Source Document",
  "source_url": "https://example.com/source"
}
```

### Required Fields
- `name`, `category`, `sub_category`, `activity_unit`, `value`, `factor_unit`, `year`

### Optional Fields
- `region` (defaults to "ALL"), `scope`, `source`, `source_url`

### Response

```json
{
  "id": 151,
  "name": "New Emission Factor",
  "category": "transport",
  "sub_category": "transport_new_category",
  "activity_unit": "liters",
  "value": "2.5000000",
  "factor_unit": "kgCO2e/liter",
  "year": 2025,
  "region": "ALL",
  "scope": "1",
  "source": "Source Document",
  "source_url": "https://example.com/source"
}
```

---

## 3. Update Emission Factor

**PUT** `/api/emission-factors/{id}/` - Full update
**PATCH** `/api/emission-factors/{id}/` - Partial update

### Request Body (PUT - all fields required)

```json
{
  "name": "Updated Emission Factor",
  "category": "transport",
  "sub_category": "transport_updated_category",
  "activity_unit": "liters",
  "value": "2.7000",
  "factor_unit": "kgCO2e/liter",
  "year": 2025,
  "region": "ALL",
  "scope": "1",
  "source": "Updated Source",
  "source_url": "https://example.com/updated"
}
```

### Request Body (PATCH - only changed fields)

```json
{
  "value": "2.7000",
  "source": "Updated Source"
}
```

---

## 4. Delete Emission Factor

**DELETE** `/api/emission-factors/{id}/`

Deletes a specific emission factor.

### Response
- **204 No Content** - Success
- **404 Not Found** - Factor doesn't exist
- **403 Forbidden** - Not authorized

---

## 5. Bulk Create Emission Factors

**POST** `/api/emission-factors/bulk_create/`

Creates multiple emission factors at once. Uses `update_or_create` logic to handle duplicates.

### Request Body

```json
{
  "factors": [
    {
      "name": "Factor 1",
      "category": "transport",
      "sub_category": "transport_category_1",
      "activity_unit": "liters",
      "value": "2.6460",
      "factor_unit": "kgCO2e/liter",
      "year": 2025,
      "region": "ALL",
      "scope": "1",
      "source": "Source 1",
      "source_url": "https://example1.com"
    },
    {
      "name": "Factor 2",
      "category": "electricity",
      "sub_category": "grid_electricity",
      "activity_unit": "kWh",
      "value": "0.5000",
      "factor_unit": "kgCO2e/kWh",
      "year": 2025,
      "region": "ALL",
      "scope": "2",
      "source": "Source 2",
      "source_url": "https://example2.com"
    }
  ]
}
```

### Response

```json
{
  "message": "Successfully created/updated 2 emission factors",
  "factors": [
    {
      "id": 152,
      "name": "Factor 1",
      // ... full factor data
    },
    {
      "id": 153,
      "name": "Factor 2",
      // ... full factor data
    }
  ]
}
```

---

## 6. Bulk Delete Emission Factors

**DELETE** `/api/emission-factors/bulk_delete/`

Deletes multiple emission factors by their IDs.

### Request Body

```json
{
  "ids": [1, 2, 3, 15, 25]
}
```

### Response

```json
{
  "message": "Successfully deleted 5 emission factors"
}
```

---

## 7. Get Categories and Subcategories

**GET** `/api/emission-factors/categories/`

Returns a hierarchical structure of all available categories and their subcategories.

### Response

```json
{
  "electricity": {
    "name": "electricity",
    "subcategories": [
      "hk_clp",
      "hk_hke",
      "prc_eastern"
    ]
  },
  "transport": {
    "name": "transport",
    "subcategories": [
      "transport_cars_diesel",
      "transport_cars_petrol",
      "transport_vans_diesel"
    ]
  }
}
```

---

## 8. Advanced Search

**GET** `/api/emission-factors/search_factors/`

Provides advanced search with multiple filter criteria.

### Query Parameters
- `category` - Filter by category (contains)
- `sub_category` - Filter by subcategory (contains)
- `activity_unit` - Filter by activity unit (contains)
- `year` - Filter by exact year
- `region` - Filter by region (contains)
- `scope` - Filter by scope (exact)
- `search` - Text search across multiple fields

### Example

```bash
GET /api/emission-factors/search_factors/?category=transport&activity_unit=liters&scope=1&search=diesel
```

---

## 9. Export CSV Template

**GET** `/api/emission-factors/export_template/`

Downloads a CSV template file for bulk uploading emission factors.

### Response
- **Content-Type**: `text/csv`
- **Content-Disposition**: `attachment; filename="emission_factors_template.csv"`

The CSV includes:
- Header row with all field names
- Two example rows showing proper format

---

## Data Model

### GHGEmissionFactor Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | Integer | Auto | Primary key |
| `name` | String(255) | Yes | Descriptive name |
| `category` | String(100) | Yes | Broad category (e.g., "transport", "electricity") |
| `sub_category` | String(255) | Yes | Specific subcategory |
| `activity_unit` | String(50) | Yes | Unit of activity data (e.g., "liters", "kWh") |
| `value` | Decimal(15,7) | Yes | Emission factor value |
| `factor_unit` | String(50) | Yes | Unit of the factor (e.g., "kgCO2e/liter") |
| `year` | Integer | Yes | Applicable year |
| `region` | String(100) | No | Geographic region (default: "ALL") |
| `scope` | String(10) | No | Emission scope ("1", "2", "3") |
| `source` | String(255) | No | Source document name |
| `source_url` | URL | No | URL to source document |

### Validation Rules

1. **Value**: Must be positive (> 0)
2. **Year**: Must be between 2000 and 2050
3. **Uniqueness**: Combination of `year`, `category`, `sub_category`, `activity_unit`, `factor_unit`, `region`, `scope` must be unique

---

## Error Responses

### 400 Bad Request
```json
{
  "value": ["Emission factor value must be positive"],
  "year": ["Year must be between 2000 and 2050"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

---

## Usage Examples

### Complete Workflow Example

```bash
# 1. Get authentication token
POST /api/token/
{
  "email": "admin@bakertilly.com",
  "password": "password"
}

# 2. List existing factors
GET /api/emission-factors/
Authorization: Bearer <token>

# 3. Create a new factor
POST /api/emission-factors/
Authorization: Bearer <token>
{
  "name": "New Diesel Factor",
  "category": "transport",
  "sub_category": "transport_new_diesel",
  "activity_unit": "liters",
  "value": "2.8000",
  "factor_unit": "kgCO2e/liter",
  "year": 2025,
  "scope": "1"
}

# 4. Update the factor
PATCH /api/emission-factors/152/
Authorization: Bearer <token>
{
  "value": "2.9000"
}

# 5. Bulk create factors
POST /api/emission-factors/bulk_create/
Authorization: Bearer <token>
{
  "factors": [
    {
      "name": "Factor A",
      "category": "electricity",
      "sub_category": "new_grid",
      "activity_unit": "kWh",
      "value": "0.4500",
      "factor_unit": "kgCO2e/kWh",
      "year": 2025,
      "scope": "2"
    }
  ]
}
```

---

## Integration Notes

### How Emission Factors Are Used

1. **Factor Lookup**: The system uses `find_matching_emission_factor()` function to find appropriate factors based on:
   - Activity category/subcategory
   - Activity unit
   - Year (with fallback to earlier years)
   - Region (with fallback to "ALL")
   - Scope

2. **Fallback Logic**: The system implements sophisticated fallback:
   - Exact match → Universal region → Earlier year → Remove unit constraint

3. **Emissions Calculation**: Found factors are used in `calculate_emissions_for_activity_value()` to convert activity data to CO2 equivalent emissions.

### Best Practices

1. **Naming Convention**: Use descriptive names that include fuel type, vehicle category, and source
2. **Categorization**: Follow existing category/subcategory patterns for consistency
3. **Regional Settings**: Use "ALL" for universal factors, specific codes for regional factors
4. **Year Management**: Keep factors up-to-date and maintain historical versions
5. **Source Documentation**: Always include source and source_url for traceability

### Data Import/Export

- Use the CSV template endpoint for bulk uploads
- Export existing data before making major changes
- Test with small batches before bulk operations
- Validate data consistency after imports 