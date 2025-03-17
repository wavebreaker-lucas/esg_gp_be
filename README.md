# ESG Platform - GreenPoint

A Django-based platform for managing company hierarchies and user access control with a focus on ESG (Environmental, Social, and Governance) reporting.

## Overview

The ESG Platform enables Baker Tilly to manage and oversee their client companies' ESG reporting processes. The platform follows a hierarchical structure where:

1. Baker Tilly admins oversee all client companies
2. Each client company has its own hierarchy (Group → Subsidiary → Branch)
3. Users within companies have different roles (Creator, Management, Operation)

## Important Notes

### User Management
1. **Creator Role Inheritance**
   - When a subsidiary is created, the CREATOR of the parent company is automatically added as a CREATOR of the subsidiary
   - The same user (identified by email) can have different display names in different layers
   - Example: admin@example.com can be "John Doe" in Group layer and "admin" in Subsidiary layer

2. **User Limits**
   - Maximum 5 non-creator users per layer
   - CREATOR users are not counted in this limit
   - Users can be added via API or Django admin interface

3. **Email System**
   - Email notifications are sent for:
     - New user creation (with login credentials)
     - Password resets
     - OTP verification
   - Development: Emails are printed to console (using console backend)
   - Production: Configure proper email backend in settings.py

### Company Hierarchy
1. **Layer Types**
   - GROUP: Top-level company (can only be created by Baker Tilly admins)
   - SUBSIDIARY: Mid-level company, must have a parent GROUP (can be created by CREATOR role)
   - BRANCH: Bottom-level company, must have a parent SUBSIDIARY (can be created by CREATOR role)

2. **Access Control**
   - CREATOR users get automatic access to child layers
   - Users can have different roles in different layers
   - Layer access is enforced through AppUser associations
   - Only Baker Tilly admins can create GROUP layers
   - CREATOR role users can only create SUBSIDIARY and BRANCH layers under their existing GROUP

3. **Layer Relationships**
   - When creating layers:
     - Use `group_id` when creating SUBSIDIARY layers
     - Use `subsidiary_id` when creating BRANCH layers
   - When retrieving layers (`GET /api/layers/`):
     - `parent_id` field shows the parent layer's ID:
       - For SUBSIDIARY layers: `parent_id` is the GROUP's ID (same as `group_id`)
       - For BRANCH layers: `parent_id` is the SUBSIDIARY's ID (same as `subsidiary_id`)
       - For GROUP layers: `parent_id` is null
     - Child layers can be found by filtering layers where their `parent_id` matches the current layer's ID
   - These relationship fields are only in the API response and don't affect how you create or manage layers

## Basic Workflow

1. **Company Onboarding**
   - Baker Tilly admin creates a new client company
   - Sets up the initial company structure
   - Creates the company admin account

2. **Company Management**
   - Company admin can manage their structure and users
   - Baker Tilly admin can oversee and assist at any time
   - Users can be added at different levels with appropriate roles

3. **ESG Reporting**
   - Users input ESG data based on their role
   - Baker Tilly admins verify and approve submissions
   - Reports and analytics are generated

## Quick Start
1. Clone and setup
   ```bash
   git clone [repository-url]
   cd esg_platform_greenpoint
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure and run
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py runserver
   ```

3. Email Configuration (Development)
   ```python
   # settings.py
   EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
   DEFAULT_FROM_EMAIL = 'noreply@esgplatform.com'
   ```

## API Examples

### Statistics and Analytics

1. Get Overall Client Statistics:
```http
GET /api/clients/statistics/

# Response Example:
{
    "total_groups": 5,
    "total_subsidiaries": 12,
    "total_branches": 25,
    "total_users": 150,
    "groups": [
        {
            "group_id": 1,
            "group_name": "Example Corp",
            "statistics": {
                "subsidiaries": 3,
                "branches": 8,
                "users": {
                    "group": {
                        "total": 10,
                        "by_role": {
                            "creator": 2,
                            "management": 3,
                            "operation": 5
                        }
                    },
                    "subsidiaries": {
                        "total": 15,
                        "by_role": {
                            "creator": 3,
                            "management": 5,
                            "operation": 7
                        }
                    },
                    "branches": {
                        "total": 20,
                        "by_role": {
                            "creator": 4,
                            "management": 8,
                            "operation": 8
                        }
                    },
                    "total": 45
                }
            }
        }
    ]
}
```

2. Get Single Client Statistics:
```http
GET /api/clients/{group_id}/statistics/

# Response Example:
{
    "group_id": 1,
    "group_name": "Example Corp",
    "statistics": {
        "subsidiaries": 3,
        "branches": 8,
        "users": {
            "group": {
                "total": 10,
                "by_role": {
                    "creator": 2,
                    "management": 3,
                    "operation": 5
                }
            },
            "subsidiaries": {
                "total": 15,
                "by_role": {
                    "creator": 3,
                    "management": 5,
                    "operation": 7
                }
            },
            "branches": {
                "total": 20,
                "by_role": {
                    "creator": 4,
                    "management": 8,
                    "operation": 8
                }
            },
            "total": 45
        }
    }
}
```

**Key Features:**
- Available only to Baker Tilly admins
- Provides comprehensive statistics at both global and per-client levels
- Breaks down user counts by role (creator, management, operation)
- Shows detailed hierarchy information (subsidiaries and branches)
- Efficiently aggregates data across all layers

**Use Cases:**
1. Dashboard Overview:
   - Quick view of total companies and users
   - Monitor company structure growth
   - Track user distribution across roles
2. Client Analysis:
   - Detailed view of client's organizational structure
   - User distribution across different layers
   - Role-based access patterns
3. Resource Planning:
   - Identify clients with complex structures
   - Monitor user allocation across layers
   - Plan capacity based on user distribution

### User Management

1. Get User Table Data:
```bash
GET /api/app_users/table/

# Optional Query Parameters:
?group_id=1           # Filter by group layer (includes users in subsidiaries and branches under this group)
?subsidiary_id=2      # Filter by subsidiary layer (includes users in branches under this subsidiary)
?branch_id=3          # Filter by branch layer
?role=MANAGEMENT      # Filter by role

# Response Example:
{
    "users": [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "CREATOR",
            "title": "CEO",
            "is_active": true,
            "is_baker_tilly_admin": false,
            "must_change_password": false,
            "layer": {
                "id": 1,
                "name": "Example Corp",
                "type": "GROUP"
            }
        },
        {
            "id": 2,
            "name": "Jane Smith",
            "email": "jane@bakertilly.com",
            "role": "CREATOR",
            "title": "ESG Advisor",
            "is_active": true,
            "is_baker_tilly_admin": true,
            "must_change_password": false,
            "layer": {
                "id": 3,
                "name": "Asia Branch",
                "type": "BRANCH",
                "parent": {
                    "id": 2,
                    "name": "Asia Division",
                    "type": "SUBSIDIARY"
                },
                "group": {
                    "id": 1,
                    "name": "Example Corp",
                    "type": "GROUP"
                }
            }
        }
    ],
    "total": 2
}
```

**Key Features:**
- Efficient database queries with optimized joins
- Flexible filtering options
- Flattened data structure for easy consumption
- Complete hierarchy information
- User status and permission details including Baker Tilly admin status
- Lightweight response format

**Important Notes:**
- Returns all accessible users based on requester's permissions
- Hierarchical filtering:
  - When filtering by `group_id`, returns users from the group AND all its subsidiaries AND all branches under those subsidiaries
  - When filtering by `subsidiary_id`, returns users from the subsidiary AND all its branches
  - When filtering by `branch_id`, returns only users from that specific branch
- Hierarchy information is included when relevant
- User status includes:
  - Account activation status
  - Baker Tilly admin privileges
  - Password change requirements
- Response is not cached for real-time accuracy
- Supports filtering by layer type and role

2. Get User's Group Information:
```bash
GET /api/app_users/my-groups/

# Response Example:
{
    "groups": [
        {
            "id": 1,
            "name": "Example Corp",
            "direct_access": false,
            "subsidiary_id": 3,
            "subsidiary_name": "Tech Division",
            "branch_id": 7,
            "branch_name": "R&D Department",
            "app_user_id": 12,
            "role": "MANAGEMENT"
        }
    ],
    "total": 1
}
```

**Key Features:**
- Returns the top-level group layer the authenticated user has access to
- Automatically traverses the hierarchy to find parent group
- Includes contextual information about the user's position in the hierarchy
- Deduplicates groups to avoid redundancy

**Important Notes:**
- Always returns the highest level (group) information, even if the user is only associated with a subsidiary or branch
- For users directly in a group layer, includes `direct_access: true`
- For users in a subsidiary, includes the parent group and subsidiary information
- For users in a branch, includes the parent group, subsidiary, and branch information
- Useful for initializing the frontend after login to determine which group(s) the user belongs to
- No query parameters required - automatically uses the authenticated user's context
- Returns unique groups even if the user has multiple roles within the same group hierarchy

3. Add User to Layer:

#### Windows (PowerShell/Command Prompt):
```bash
# Using curl.exe (recommended)
curl.exe -X POST "http://localhost:8000/api/app_users/{layer_id}/add-user/" ^
-H "Content-Type: application/json" ^
-H "Authorization: Bearer {token}" ^
-d "{\"user\": {\"email\":\"user@example.com\"}, \"name\":\"User Name\", \"title\":\"Manager\", \"role\":\"MANAGEMENT\"}"
```

#### Unix-like Systems (Linux/macOS):
```bash
curl -X POST "http://localhost:8000/api/app_users/{layer_id}/add-user/" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer {token}" \
-d '{
    "user": {
        "email": "user@example.com"
    },
    "name": "User Name",
    "title": "Manager",
    "role": "MANAGEMENT"
}'
```

**Important Notes for Adding Users:**
- The email MUST be wrapped in a "user" object in the JSON payload
- Available roles: CREATOR, MANAGEMENT, OPERATION
- For branches: Use MANAGEMENT role for users who will report emissions
- For subsidiaries without branches: Use MANAGEMENT role for emission reporting
- A successful creation returns HTTP 201 with the created user details
- The user will receive an email with login credentials
- Users must change their password on first login

2. Delete User from Layer:

#### Windows (PowerShell/Command Prompt):
```bash
# Using curl.exe (recommended)
curl.exe -v -X DELETE "http://localhost:8000/api/app_users/{app_user_id}/" -H "Authorization: Bearer {token}" -H "Accept: application/json"

# Using PowerShell's Invoke-RestMethod
Invoke-RestMethod -Method DELETE -Uri "http://localhost:8000/api/app_users/{app_user_id}/" -Headers @{Authorization="Bearer {token}"; Accept="application/json"} -Verbose
```

#### Unix-like Systems (Linux/macOS):
```bash
curl -X DELETE "http://localhost:8000/api/app_users/{app_user_id}/" \
-H "Authorization: Bearer {token}" \
-H "Accept: application/json"
```

**Important Notes:**
- The trailing slash in the URL is required (`/{app_user_id}/`)
- A successful deletion returns HTTP 204 (No Content)
- The associated CustomUser will be automatically deleted if this was their only layer association
- Make sure your JWT token is complete and not truncated
- Use `-v` or `--verbose` flag to see detailed request/response information for debugging

### Company Structure

1. Create Subsidiary:
```bash
curl -X POST http://localhost:8000/api/layers/ \
-H "Content-Type: application/json" \
-H "Authorization: Bearer {token}" \
-d '{
    "layer_type": "SUBSIDIARY",
    "company_name": "Example Subsidiary",
    "company_industry": "Technology",
    "shareholding_ratio": 100.00,
    "company_location": "Singapore",
    "group_id": 1
}'
```

Note: The CREATOR of the parent GROUP will automatically become a CREATOR of the new SUBSIDIARY.

2. Create Branch:

#### Windows (PowerShell/Command Prompt):
```bash
# Using curl.exe (recommended)
curl.exe -v -X POST "http://localhost:8000/api/layers/" ^
-H "Content-Type: application/json" ^
-H "Authorization: Bearer {token}" ^
-H "Accept: application/json" ^
-d "{\"layer_type\":\"BRANCH\",\"company_name\":\"Example Branch\",\"company_industry\":\"Technology\",\"company_location\":\"Singapore\",\"shareholding_ratio\":100.00,\"subsidiary_id\":2}"
```

#### Unix-like Systems (Linux/macOS):
```bash
curl -X POST "http://localhost:8000/api/layers/" \
-H "Content-Type: application/json" \
-H "Authorization: Bearer {token}" \
-d '{
    "layer_type": "BRANCH",
    "company_name": "Example Branch",
    "company_industry": "Technology",
    "company_location": "Singapore",
    "shareholding_ratio": 100.00,
    "subsidiary_id": 2
}'
```

**Important Notes for Branch Creation:**
- The `subsidiary_id` field is required and must reference an existing subsidiary
- Only CREATOR role users can create branches
- The branch will be created under the specified subsidiary
- A successful creation returns HTTP 201 with the created branch details
- The CREATOR of the parent subsidiary automatically gets access to the new branch

## Glossary

- **ESG**: Environmental, Social, and Governance - A framework for evaluating organizations' sustainability and societal impact
- **JWT**: JSON Web Token - A secure way to handle user authentication and information exchange
- **OTP**: One-Time Password - A automatically generated code sent via email for additional security
- **API**: Application Programming Interface - A set of rules that allow different software applications to communicate
- **CRUD**: Create, Read, Update, Delete - Basic operations for managing data
- **Layer**: In this platform, refers to different levels of company hierarchy (Group, Subsidiary, Branch)
- **Role-based Access**: Access control system with three levels:
  - CREATOR: Full access to manage company structure and users
  - MANAGEMENT: Can manage users within their layer
  - OPERATION: Basic access for viewing and personal updates
- **Serializer**: Component that converts complex data types (like database models) to and from JSON
- **ViewSet**: Django REST Framework component that handles API operations for a model
- **Middleware**: Software that acts as a bridge between different applications or components

## Core Features

### 1. Role-Based Access Control

#### Baker Tilly Admin
- **Platform Administration**
  - Oversee all client companies
  - Manage company structures
  - Monitor ESG reporting progress
- **Client Setup**
  - Create new client companies
  - Set up company admins
  - Configure initial structure
- **ESG Oversight**
  - Verify submitted data
  - Generate reports
  - Track compliance

#### Company Roles
- **CREATOR (Company Admin)**
  - Manage company structure
  - Add/remove users
  - Oversee company ESG reporting
- **MANAGEMENT**
  - Manage their layer
  - Add/edit ESG data
  - View reports
- **OPERATION**
  - Input ESG data
  - View their layer
  - Update profile

### 2. Company Structure
- Three-tier hierarchy:
  - Group Layer (Parent company)
  - Subsidiary Layer (Child companies)
  - Branch Layer (Local offices)
- Profile management
- Shareholding tracking
- Location/industry data

### 3. Template System
The platform includes a comprehensive template system for ESG disclosure:

#### Template Types and Categories
1. **Template Types**
   - **Assessment Templates**: For maturity/quality evaluations with scoring
   - **Disclosure Templates**: For pure data collection without scoring
   - **Compliance Templates**: For compliance checks with optional scoring

2. **Categories**
   - **Environmental**: Environmental impact and sustainability metrics
   - **Social**: Social responsibility and community impact
   - **Governance**: Corporate governance practices

#### Question Categories and Types
1. **Question Categories**
   - **Quantitative Data**: Numerical measurements (e.g., emissions, energy usage)
   - **Qualitative Assessment**: Evaluative questions (may include scoring)
   - **Documentation/Evidence**: Required documentation and proof

2. **Question Types**
   - Text responses
   - Numeric inputs (with units)
   - Single/multiple choice
   - Date fields
   - File uploads

3. **Question Properties**
   - Unit types (kWh, tCO2e, hours, etc.)
   - Custom units
   - Evidence requirements
   - Optional scoring (for assessment templates)
   - Validation rules

#### Template Creation Example
```http
POST /api/templates/
{
    "name": "Environmental Assessment 2024",
    "description": "Annual environmental performance assessment",
    "category": "ENVIRONMENTAL",
    "template_type": "ASSESSMENT",
    "reporting_period": "Annual 2024",
    "questions": [
        {
            "text": "What is your total energy consumption?",
            "help_text": "Include all energy sources",
            "question_type": "NUMBER",
            "question_category": "QUANTITATIVE",
            "unit_type": "kWh",
            "is_required": true,
            "order": 1,
            "requires_evidence": true
        },
        {
            "text": "Assess your energy management maturity",
            "help_text": "Choose the most appropriate level",
            "question_type": "CHOICE",
            "question_category": "QUALITATIVE",
            "is_required": true,
            "order": 2,
            "has_score": true,
            "max_score": 5,
            "choices": [
                {
                    "text": "No formal management",
                    "value": "level_1",
                    "order": 1,
                    "score": 1
                },
                {
                    "text": "Basic monitoring",
                    "value": "level_2",
                    "order": 2,
                    "score": 2
                },
                {
                    "text": "Systematic management",
                    "value": "level_3",
                    "order": 3,
                    "score": 3
                },
                {
                    "text": "Advanced optimization",
                    "value": "level_4",
                    "order": 4,
                    "score": 4
                },
                {
                    "text": "Industry leading",
                    "value": "level_5",
                    "order": 5,
                    "score": 5
                }
            ]
        }
    ]
}
```

**Important Notes:**
1. **Template Types**
   - Choose appropriate template type based on purpose
   - Scoring is only available in Assessment templates
   - Disclosure templates focus on data collection
   - Compliance templates can optionally use scoring

2. **Question Setup**
   - Match question category to data collection needs
   - Use appropriate units for quantitative data
   - Only use scoring for qualitative assessments
   - Include evidence requirements where needed

3. **Best Practices**
   - Group related questions into sections
   - Provide clear help text and instructions
   - Use consistent units within categories
   - Include validation rules for data quality

### 4. Security Features
- JWT-based authentication
- Email verification system
- Password reset functionality
- Role-based permissions
- Layer-based access control
- OTP system for verification
- Session management

### 5. Data Management
- CSV import/export functionality
- Bulk operations support
- Caching for performance
- Transaction management
- Error handling and logging

## Technical Details

### Project Structure
```
accounts/                       # Main application directory
├── admin.py       # Customizes the Django admin panel interface
├── apps.py        # Django app configuration and startup settings
├── models.py      # Defines database structure and relationships
├── permissions.py # Handles access control and security rules
├── services.py    # Contains business logic and external service interactions
├── utils.py       # General utility functions and helpers
├── urls.py        # Maps URLs to their corresponding views
│   ├── auth.py           # Authentication views
│   ├── client_management.py  # Baker Tilly admin operations
│   ├── layer_management.py   # Company hierarchy operations
│   ├── user_management.py    # User CRUD operations
│   └── mixins.py        # Reusable view mixins
└── serializers/   # Converts data between Python and JSON formats
    ├── auth.py    # Authentication serializers
    └── models.py  # Model serializers
```

### Components

#### 1. Core Files

- **utils.py** (General Utilities)
  - Password validation and security checks
  - OTP code generation
  - Layer hierarchy utilities (get_all_lower_layers, get_creator_layers, get_parent_layer)
  - Pure utility functions without business logic or external dependencies

- **services.py** (Business Logic)
  - Email services (notifications, verifications)
  - Layer access validation and management
  - User management utilities
  - Complex business logic (get_flat_sorted_layers)
  - Functions that interact with models or external services
  - Security constants (COMMON_PASSWORDS)

- **permissions.py** (Access Control)
  - `IsManagement`: Allows access to management functions
  - `IsOperation`: Restricts access to operational tasks
  - `IsCreator`: Provides company creation privileges
  - `CanManageAppUsers`: Controls user management capabilities

- **admin.py** (Django Admin Configuration)
  - Custom admin interface for all models
  - Enhanced display and filtering options
  - Optimized queries for admin views
  - Custom actions and inline models

#### 2. Models and Serializers

##### Database Models (`models.py`)
- **CustomUser**: Database schema for user authentication
  - Email-based authentication
  - Role management (Creator, Management, Operation)
  - Baker Tilly admin flags
  - Password and OTP fields
- **LayerProfile**: Company hierarchy database schema
  - Base model for all company types
  - Common fields (name, industry, location)
  - Relationship definitions
- **AppUser**: User-company relationship schema
  - Links users to company layers
  - Stores user metadata
  - Manages layer associations

##### Model Serializers (`serializers/models.py`)
- **CustomUserSerializer**: API representation of users
  - Handles password validation
  - Manages role assignments
  - Controls visible user fields
- **LayerProfileSerializer**: Company data formatting
  - Computes user counts
  - Formats timestamps
  - Handles nested user data
- **AppUserSerializer**: User profile API handling
  - Combines user and layer data
  - Validates user-layer relationships
  - Manages profile updates

#### 3. Views and Serializers
```
views/                          serializers/
├── auth.py                     ├── auth.py (Data validation)
├── client_management.py        └── models.py
├── layer_management.py
├── user_management.py
└── mixins.py
```

Each module pair handles specific functionality:
- **Authentication and Security**
  - `views/auth.py`: HTTP endpoints for:
    - JWT token-based login/logout
    - Two-factor authentication (OTP)
    - Password reset workflow
    - Email verification
    - OTP resending functionality
  - `serializers/auth.py`: Data handling for:
    - Login credential validation
    - Password validation
    - User data formatting
    - Reset token validation

- **Client Management**
  - `views/client_management.py`: Baker Tilly admin operations
  - Related serializers in `models.py`

- **Layer Management**
  - `views/layer_management.py`: Company hierarchy operations
  - Related serializers in `models.py`

- **User Management**
  - `views/user_management.py`: User CRUD operations
  - Related serializers in `models.py`

### Role-Based Access Control (RBAC)

The platform implements a hierarchical role-based access control system that ensures secure and organized data access:

#### Admin Types
1. **Baker Tilly Admin**
   - Platform-wide business administration
   - Access to all client company data
   - Management of ESG configurations
   - Oversight of all platform operations
   - Assigned to Baker Tilly team members

2. **System Superuser**
   - Technical system administration
   - Django admin interface access
   - System maintenance and configuration
   - Reserved for platform maintenance

#### Role Hierarchy
1. **CREATOR Role**
   - Company-level administration
   - Company structure management
   - User management within company
   - Company data access

2. **MANAGEMENT Role**
   - Layer-level administration
   - User management within layer
   - Layer data access
   - Operational oversight

3. **OPERATION Role**
   - Basic user access
   - Personal profile management
   - Layer data viewing
   - Data entry and updates

#### Access Control Implementation
- Role verification through permission classes
- Layer-based access control
- Admin privileges management
- Audit logging of admin actions
- Secure data access controls

#### Security Considerations
- Strict role separation
- Layer-based data isolation
- Admin action logging
- Access audit trails
- Secure permission checks

## User Management Process

1. **Initial Company Setup** (Baker Tilly Admin)
   - Creates client company via `/api/clients/setup/`
   - Sets up initial company admin account
   - Company admin receives login credentials

2. **Adding Users** (Company Admin/Management)
   - Company admin can add users via:
     - Single user: `/api/app_users/{layer_id}/add-user/`
     - Bulk import: `/api/app_users/{layer_id}/import-csv/`
   - Users receive email with login credentials
   - Must change password on first login

3. **User Management**
   - CREATOR: Can manage all company users
   - MANAGEMENT: Can manage users in their layer
   - Maximum 5 non-creator users per layer
   - User roles: MANAGEMENT, OPERATION

## API Reference
All API endpoints require authentication unless specified otherwise.

### Baker Tilly Admin Endpoints
These endpoints are exclusively for Baker Tilly staff:

- `POST /api/clients/setup/` - Set up new client company with initial admin
  ```json
  {
    "company_name": "Example Corp",
    "industry": "Technology",
    "location": "Hong Kong",
    "admin_email": "admin@example.com",
    "admin_password": "secure_password",
    "admin_name": "John Doe",
    "admin_title": "ESG Administrator",
    "template_id": 1
  }
  ```

- `GET /api/clients/{group_id}/structure/` - View client company structure (group_id must be a GroupLayer ID)
- `POST /api/clients/{group_id}/structure/` - Add subsidiary or branch to client company
  ```json
  {
    "layer_type": "SUBSIDIARY",
    "company_name": "Example Asia",
    "industry": "Technology",
    "location": "Singapore",
    "shareholding_ratio": 75.5
  }
  ```

- `GET /api/clients/{group_id}/users/` - List all users in client company (group_id must be a GroupLayer ID)
- `POST /api/clients/{group_id}/users/` - Add new user to client company
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password",
    "name": "Jane Smith",
    "title": "ESG Manager",
    "role": "MANAGEMENT"
  }
  ```

**Important Note**: The `group_id` parameter in these endpoints must be the ID of a GroupLayer (top-level company). These endpoints do not work with subsidiary or branch IDs.

### List All Groups
```http
GET /api/layers/?layer_type=GROUP
```

Returns a list of all group layers (top-level companies) in the system. This endpoint supports filtering and includes user counts.

**Query Parameters:**
- `layer_type` (optional): Filter by layer type. Values: GROUP, SUBSIDIARY, BRANCH. Can be comma-separated for multiple types.

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Company Name",
    "layer_type": "GROUP",
    "user_count": 5,
    "app_users": [
      {
        "id": "uuid",
        "user": {
          "id": "uuid",
          "email": "user@example.com",
          "role": "CREATOR"
        }
      }
    ]
  }
]
```

**Notes:**
- Response is cached for 5 minutes for performance
- Includes user counts and associated users
- Baker Tilly admins see all groups
- Regular users only see groups they have access to

### Authentication Endpoints
These endpoints handle user authentication and account management:

- `POST /api/login/` - Authenticate user and get access token (No auth required)
  ```json
  // Request
  {
    "email": "user@example.com",
    "password": "secure_password"
  }

  // Response
  {
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "role": "CREATOR",
      "is_superuser": false,
      "is_baker_tilly_admin": true,
      "must_change_password": false
    }
  }
  ```

- `POST /api/logout/` - Invalidate current access token
- `POST /api/verify-otp/` - Verify email using OTP code (No auth required)
- `POST /api/resend-otp/` - Request new OTP code (No auth required)
- `POST /api/token/refresh/` - Get new access token using refresh token
- `POST /api/request-password-reset/` - Start password reset process (No auth required)
- `POST /api/reset-password/<token>/` - Complete password reset (No auth required)

**Important Notes:**
1. The `is_baker_tilly_admin` field in the response indicates whether the user has Baker Tilly administrator privileges
2. Baker Tilly admins have access to:
   - All client company data
   - Template management
   - User management across all companies
   - ESG data verification
3. Regular users (non-Baker Tilly admins) are restricted to their assigned layers and roles
4. The admin status can only be set through the Django admin interface, not through the API

### Layer Management Endpoints
These endpoints manage the company hierarchy structure:

#### Get All Layers

**Endpoint:** `/api/layers/`  
**Method:** GET  
**Authentication:** Required  
**Description:** Get all layers accessible to the authenticated user.

**Query Parameters:**
- `layer_type` (optional): Filter by layer type (GROUP, SUBSIDIARY, BRANCH)

**Response Fields:**
- `id`: Unique identifier for the layer
- `company_name`: Name of the company
- `company_industry`: Industry sector
- `shareholding_ratio`: Ownership percentage (0-100)
- `app_users`: Array of users associated with this layer
  - `user`: User account details including role and permissions
  - `name`: Display name in this layer
  - `title`: Job title in this layer
- `user_count`: Total number of users in this layer
- `layer_type`: Type of layer (GROUP, SUBSIDIARY, BRANCH)
- `company_location`: Physical location of the company
- `created_at`: Creation timestamp in HKT format (YYYY-MM-DD HH:MM)
- `created_by`: Email address of the user who created this layer
- `parent_id`: ID of parent layer (null for GROUP, group_id for SUBSIDIARY, subsidiary_id for BRANCH)

**Example Response:**
  ```json
  {
    "id": "uuid",
    "company_name": "Example Corp",
    "company_industry": "Technology",
    "shareholding_ratio": 100.00,
    "app_users": [
      {
        "id": "uuid",
        "user": {
          "id": "uuid",
          "email": "admin@example.com",
          "role": "CREATOR",
          "is_superuser": false,
          "is_baker_tilly_admin": false,
          "must_change_password": false
        },
        "name": "John Doe",
        "title": "CEO",
        "role": "CREATOR"
      }
    ],
    "user_count": 1,
    "layer_type": "GROUP",
    "company_location": "Hong Kong",
    "created_at": "2024-03-15 10:30",
    "created_by": "john.doe@bakertilly.com",
    "parent_id": null
  }
  ```

### Get Layer Detail

**Endpoint:** `/api/layers/{id}/`  
**Method:** GET  
**Authentication:** Required  
**Description:** Get details for a specific layer.

**Response:** Same as the Get All Layers endpoint.

### Create Layer

**Endpoint:** `/api/layers/`  
**Method:** POST  
**Authentication:** Required  
**Description:** Create a new layer (SUBSIDIARY or BRANCH).

**Request Body:**
- `layer_type`: Type of layer to create (SUBSIDIARY or BRANCH)
- `company_name`: Name of the company
- `company_industry`: Industry sector
- `company_location`: Physical location of the company
- `shareholding_ratio`: Ownership percentage (0-100)
- `group_id`: ID of parent group (required for SUBSIDIARY)
- `subsidiary_id`: ID of parent subsidiary (required for BRANCH)
- `app_users`: Array of users to add to this layer (optional)

**Response:** Same as the Get Layer Detail endpoint.

### Update Layer

**Endpoint:** `/api/layers/{id}/`  
**Method:** PATCH  
**Authentication:** Required  
**Description:** Update an existing layer.

**Request Body:**
- `company_name`: Name of the company (optional)
- `company_industry`: Industry sector (optional)
- `company_location`: Physical location of the company (optional)
- `shareholding_ratio`: Ownership percentage (0-100) (optional)

**Response:**
  ```json
  {
    "id": "123",
    "company_name": "Updated Company Name",
    "company_industry": "Updated Industry",
    "shareholding_ratio": "100.00",
    "layer_type": "SUBSIDIARY",
    "company_location": "New Location",
    "created_at": "2024-03-15 10:30",
    "created_by": "john.doe@bakertilly.com",
    "parent_id": "456"
  }
  ```

### Delete Layer

**Endpoint:** `/api/layers/{id}/`  
**Method:** DELETE  
**Authentication:** Required  
**Description:** Delete a layer.

**Response:** HTTP 204 No Content

### User Management Endpoints
These endpoints handle user operations within companies:

- `GET /api/app_users/` - List users in accessible companies
- `POST /api/app_users/` - Create new user account
- `GET /api/app_users/<id>/` - Get user profile details
  ```bash
  GET /api/app_users/12/
  
  # Response Example:
  {
    "id": 12,
    "user": {
      "id": 5,
      "email": "john@example.com",
      "role": "MANAGEMENT",
      "is_active": true,
      "is_baker_tilly_admin": false,
      "must_change_password": false
    },
    "name": "John Smith",
    "title": "ESG Manager",
    "layer": {
      "id": 7,
      "name": "R&D Department",
      "type": "BRANCH",
      "parent": {
        "id": 3,
        "name": "Tech Division",
        "type": "SUBSIDIARY"
      },
      "group": {
        "id": 1,
        "name": "Example Corp",
        "type": "GROUP"
      }
    }
  }
  ```
  
  **Important Notes:**
  - Returns detailed information about a specific AppUser
  - Includes complete user profile information
  - Contains full hierarchy information (branch → subsidiary → group)
  - Requires appropriate permissions to access (must have access to the user's layer)
  - The `id` parameter is the AppUser ID, not the CustomUser ID
  - Returns HTTP 404 if the AppUser doesn't exist or the requester doesn't have access

- `PUT /api/app_users/<id>/` - Update user information
- `DELETE /api/app_users/<id>/` - Remove user from company
- `POST /api/app_users/<id>/add-user/` - Add existing user to company
- `POST /api/app_users/<id>/import-csv/` - Bulk import users from CSV
- `GET /api/app_users/<id>/export-csv/` - Export user list to CSV

### Template Management

The platform uses a form-based template system for HKEX ESG disclosures:

#### 1. ESG Forms
Forms are predefined HKEX disclosure requirements:

```http
GET /api/esg-forms/
# Response
{
    "forms": [
        {
            "id": 2,
            "code": "HKEX-B2",
            "name": "Social - Health and Safety",
            "description": "Workplace health and safety disclosures (HKEX B2)",
            "metrics": [
                {
                    "id": 1,
                    "name": "Number of work-related fatalities",
                    "description": "Number of deaths due to work injury",
                    "unit_type": "count",
                    "requires_evidence": true,
                    "location": "HK",
                    "is_required": false
                },
                {
                    "id": 2,
                    "name": "Number of work-related fatalities",
                    "description": "Number of deaths due to work injury",
                    "unit_type": "count",
                    "requires_evidence": true,
                    "location": "PRC",
                    "is_required": false
                },
                {
                    "id": 3,
                    "name": "Lost days due to work injury",
                    "description": "Number of lost days due to work injury",
                    "unit_type": "days",
                    "requires_evidence": true,
                    "location": "HK",
                    "is_required": false
                },
                {
                    "id": 4,
                    "name": "Lost days due to work injury",
                    "description": "Number of lost days due to work injury",
                    "unit_type": "days",
                    "requires_evidence": true,
                    "location": "PRC",
                    "is_required": false
                }
            ]
        }
    ]
}
```

**Important Notes:**
1. **Location-Based Metrics**
   - Each metric is specific to a location (Hong Kong or Mainland China)
   - All location-specific metrics are optional by default
   - Companies only need to report metrics for their operational locations
   - Companies with operations in both locations should report both sets of metrics

2. **Evidence Requirements**
   - All reported metrics require supporting evidence
   - Evidence can include documents, calculations, or data sources
   - The system tracks evidence attachments for audit purposes

3. **Reporting Period**
   - Templates are created for specific reporting periods (e.g., "Annual 2024")
   - This ensures consistent year-over-year comparison
   - Historical data is preserved for trend analysis

4. **Data Validation**
   - The system validates metric values based on their unit types
   - Prevents submission of invalid data (e.g., negative counts)
   - Flags significant variations from previous periods

#### 2. Creating Templates
Templates combine relevant HKEX forms for the reporting period:

```http
POST /api/templates/
{
    "name": "HKEX ESG Disclosure 2024",
    "description": "Annual ESG disclosure template for HKEX reporting",
    "reporting_period": "Annual 2024",
    "selected_forms": [
        {
            "form_id": 1,
            "order": 1
        },
        {
            "form_id": 2,
            "order": 2
        }
    ]
}
```

**Best Practices:**
1. **Location Handling**
   - Companies should only fill in metrics for their operational locations
   - Empty metrics for non-operational locations will be automatically excluded from reports
   - The system supports companies operating in:
     - Hong Kong only
     - Mainland China only
     - Both Hong Kong and Mainland China

2. **Data Collection**
   - Collect data separately for each operational location
   - Ensure evidence is location-specific and properly labeled
   - Use consistent units across all locations

3. **Reporting**
   - Reports will automatically adapt to show only the relevant location data
   - Combined reports for companies operating in both locations
   - Location-specific breakdowns available when needed

## Usage Examples

### Creating a New Company Structure

There are two ways to manage company structure:

#### 1. Using Baker Tilly Admin Endpoints (Recommended)
Baker Tilly admins can manage the complete company structure using dedicated endpoints:

1. Create Initial Company:
```json
POST /api/clients/setup/
{
    "company_name": "Example Corp",
    "industry": "Technology",
    "location": "Hong Kong",
    "admin_email": "admin@example.com",
    "admin_password": "secure_password",
    "admin_name": "John Doe",
    "admin_title": "ESG Administrator"
}
```

2. Add Subsidiary or Branch:
```json
POST /api/clients/{group_id}/structure/
{
    "layer_type": "SUBSIDIARY",
    "company_name": "Example Subsidiary",
    "industry": "Software",
    "location": "Singapore",
    "shareholding_ratio": 75.5
}
```

3. View Complete Structure:
```
GET /api/clients/{group_id}/structure/
```

Note: The `group_id` parameter must be the ID of a GroupLayer (top-level company).

#### 2. Using General Layer Management Endpoints
Company Admins (and Baker Tilly admins) can also use these endpoints:

1. Add Subsidiary:
```json
POST /api/layers/
{
    "layer_type": "SUBSIDIARY",
    "company_name": "Example Subsidiary",
    "company_industry": "Software",
    "shareholding_ratio": 100.00,
    "company_location": "Singapore",
    "group_id": 1
}
```

Note: Baker Tilly admins have access to both sets of endpoints and can manage company structure at any time.

### Managing Users

Add User to Layer:
```json
POST /api/app_users/1/add-user/
{
  "email": "user@example.com",
  "name": "John Doe",
  "title": "Manager",
  "role": "MANAGEMENT"
}
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Your License Here] 

### Authentication and Security

The platform implements a robust authentication system with multiple security features:

#### 1. Password Management
- **Validation** (`utils.py`)
  - Minimum length requirements (8 chars, 12 for admins)
  - Complexity rules (uppercase, lowercase, numbers)
  - Common password prevention
  - Staff-specific requirements

#### 2. Two-Factor Authentication
- **OTP Generation** (`utils.py`)
  - 6-digit numeric codes
  - Time-based expiration (10 minutes)
- **Email Delivery** (`services.py`)
  - Secure email transmission
  - Clear instructions
  - Expiration notification

#### 3. User Authentication Flow
- **Login Process**
  - Email/password validation
  - JWT token generation
  - Optional 2FA verification
- **Session Management**
  - Token refresh mechanism
  - Secure logout process
  - Session timeout handling

#### 4. Security Features
- **Password Security**
  - Secure hashing (Django's default hasher)
  - Forced password changes
  - Password history tracking
- **Access Control**
  - Role-based permissions
  - Layer-based access
  - Token-based API security

#### 5. Email Communications
- **User Notifications** (`services.py`)
  - Welcome emails with credentials
  - Password reset instructions
  - OTP verification codes
- **Security Alerts**
  - Login notifications
  - Password change confirmations
  - Security-related updates 

## API Documentation

### Client Setup

#### POST /api/clients/setup/
Sets up a new client company with initial admin user.

Required fields:
- `company_name`: Name of the company
- `industry`: Company's industry
- `location`: Company's location
- `admin_email`: Email for the admin user
- `admin_password`: Password for the admin user
- `admin_name`: Full name of the admin user

Optional fields:
- `admin_title`: Title for the admin user (defaults to "ESG Administrator")

### Template Management

#### GET /api/templates/
Returns a list of all available templates that can be assigned to companies.

Response:
```json
[
  {
    "id": 1,
    "name": "Template Name",
    "description": "Template Description",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### GET /api/clients/{group_id}/templates/
Returns all template assignments for a specific client company.

Response:
```json
[
  {
    "id": 1,
    "template": {
      "id": 1,
      "name": "Template Name"
    },
    "assigned_to": {
      "id": 1,
      "email": "admin@company.com"
    },
    "due_date": "2024-12-31",
    "max_possible_score": 100,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /api/clients/{group_id}/templates/
Assigns a template to a client company.

Required fields:
- `template_id`: ID of the template to assign

Optional fields:
- `due_date`: Due date for template completion (ISO format)

Response:
```json
{
  "message": "Template assigned successfully",
  "assignment": {
    "id": 1,
    "template": {
      "id": 1,
      "name": "Template Name"
    },
    "assigned_to": {
      "id": 1,
      "email": "admin@company.com"
    },
    "due_date": "2024-12-31",
    "max_possible_score": 100
  }
}
```

#### DELETE /api/clients/{group_id}/templates/
Removes a template assignment from a client company.

Required fields:
- `assignment_id`: ID of the template assignment to remove

Response: 204 No Content 