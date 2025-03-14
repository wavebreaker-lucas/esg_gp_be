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
?group_id=1           # Filter by group layer
?subsidiary_id=2      # Filter by subsidiary layer
?branch_id=3         # Filter by branch layer
?role=MANAGEMENT     # Filter by role

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
- Hierarchy information is included when relevant
- User status includes:
  - Account activation status
  - Baker Tilly admin privileges
  - Password change requirements
- Response is not cached for real-time accuracy
- Supports filtering by layer type and role

2. Add User to Layer:

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

#### Template Categories
- **General Disclosure**: Basic company information
- **Environmental**: Environmental impact metrics
- **Social**: Social responsibility measures
- **Governance**: Corporate governance practices

#### Template Components
1. **Templates**
   - Versioned disclosure forms
   - Category-based organization
   - Active/inactive status tracking
   - Created and managed by Baker Tilly admins

2. **Questions**
   - Multiple question types:
     - Text responses
     - Numeric inputs
     - Single/multiple choice
     - Date fields
     - File uploads
   - Section organization
   - Required/optional settings
   - Scoring system
   - Custom validation rules

3. **Question Choices**
   - Predefined answer options
   - Point-based scoring
   - Ordered presentation
   - Value storage

4. **Template Assignments**
   - Company-specific assignments
   - Progress tracking
   - Due date management
   - Score calculation
   - Completion status

#### Template Usage
1. **During Client Setup**
   ```json
   POST /api/clients/setup/
   {
       "company_name": "Example Corp",
       "template_id": 1,
       // ... other fields ...
   }
   ```

2. **Template Selection**
   - Baker Tilly admins select appropriate templates
   - Templates can be filtered by category
   - Only active templates are available
   - Version control ensures consistency

3. **Assignment Management**
   - Templates assigned to specific companies
   - Progress tracking and scoring
   - Due date monitoring
   - Completion verification

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

#### List Layers
```http
GET /api/layers/
```

Returns a list of layers (companies) that the user has access to. Supports filtering by layer type.

**Query Parameters:**
- `layer_type` (optional): Filter by layer type. Values: GROUP, SUBSIDIARY, BRANCH. Can be comma-separated for multiple types.
  Example: `/api/layers/?layer_type=GROUP` or `/api/layers/?layer_type=GROUP,SUBSIDIARY`

**Response:**
```json
[
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
    "created_at": "2024-03-15 10:30HKT by John Doe",
    "parent_id": null
  }
]
```

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
- `created_at`: Creation timestamp in HKT with creator info
- `parent_id`: ID of parent layer (null for GROUP, group_id for SUBSIDIARY, subsidiary_id for BRANCH)

**Notes:**
- Response is cached for 5 minutes for performance
- Baker Tilly admins see all layers
- Regular users only see layers they have access to based on their role:
  - CREATOR: Access to their layer and all child layers
  - MANAGEMENT: Access to their layer and lower layers
  - OPERATION: Access only to their assigned layer
- For non-GROUP layers, CREATOR users are excluded from app_users list

**Example Usage:**
1. Get all group layers:
```http
GET /api/layers/?layer_type=GROUP
```

2. Get subsidiaries and branches:
```http
GET /api/layers/?layer_type=SUBSIDIARY,BRANCH
```

3. Get all layers (no filter):
```http
GET /api/layers/
```

- `POST /api/layers/` - Create new company (CREATOR role required)
- `GET /api/layers/<id>/` - Get detailed company information
- `PUT /api/layers/<id>/` - Update company details (CREATOR role required)
- `DELETE /api/layers/<id>/` - Remove company (CREATOR role required)
- `POST /api/layers/import-csv/` - Bulk import companies from CSV
- `GET /api/layers/download-example/` - Get CSV template for bulk import

### User Management Endpoints
These endpoints handle user operations within companies:

- `GET /api/app_users/` - List users in accessible companies
- `POST /api/app_users/` - Create new user account
- `GET /api/app_users/<id>/` - Get user profile details
- `PUT /api/app_users/<id>/` - Update user information
- `DELETE /api/app_users/<id>/` - Remove user from company
- `POST /api/app_users/<id>/add-user/` - Add existing user to company
- `POST /api/app_users/<id>/import-csv/` - Bulk import users from CSV
- `GET /api/app_users/<id>/export-csv/` - Export user list to CSV

### Template Assignment

The platform provides endpoints to manage ESG disclosure templates and their assignments to client companies. Only Baker Tilly admins can assign templates to companies.

#### List Available Templates
```http
GET /api/templates/

# Response Example:
{
    "templates": [
        {
            "id": 1,
            "name": "Environmental Disclosure 2024",
            "description": "Standard environmental disclosure template",
            "category": "ENVIRONMENTAL",
            "is_active": true,
            "version": 1,
            "created_at": "2024-01-01T00:00:00Z",
            "created_by": {
                "id": 1,
                "email": "admin@bakertilly.com"
            }
        }
    ]
}
```

#### Get Client's Template Assignments
```http
GET /api/clients/{group_id}/templates/

# Response Example:
{
    "assignments": [
        {
            "id": 1,
            "template": {
                "id": 1,
                "name": "Environmental Disclosure 2024",
                "category": "ENVIRONMENTAL"
            },
            "assigned_to": {
                "id": 1,
                "email": "client@example.com",
                "name": "John Doe"
            },
            "due_date": "2024-12-31",
            "completed_at": null,
            "total_score": 0,
            "max_possible_score": 100
        }
    ]
}
```

#### Assign Template to Client
```http
POST /api/clients/{group_id}/templates/
{
    "template_id": 1,
    "due_date": "2024-12-31"  # Optional
}

# Response Example:
{
    "message": "Template assigned successfully",
    "assignment": {
        "id": 1,
        "template": {
            "id": 1,
            "name": "Environmental Disclosure 2024"
        },
        "assigned_to": {
            "id": 1,
            "email": "client@example.com"
        },
        "due_date": "2024-12-31",
        "max_possible_score": 100
    }
}
```

#### Remove Template Assignment
```http
DELETE /api/clients/{group_id}/templates/
{
    "assignment_id": 1
}

# Response: 204 No Content
```

**Important Notes:**
1. Only Baker Tilly admins can:
   - View all available templates
   - Assign templates to clients
   - Remove template assignments
2. When assigning a template:
   - The template must be active (`is_active=True`)
   - The template will be assigned to the company's CREATOR user
   - Maximum possible score is automatically calculated
3. Template assignments track:
   - Completion status
   - Due dates
   - Scores achieved
   - Assignment history

**Example Workflow:**
1. Baker Tilly admin lists available templates:
   ```bash
   curl -X GET "http://localhost:8000/api/templates/" \
   -H "Authorization: Bearer {token}"
   ```

2. Assigns template to client company:
   ```bash
   curl -X POST "http://localhost:8000/api/clients/1/templates/" \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer {token}" \
   -d '{
       "template_id": 1,
       "due_date": "2024-12-31"
   }'
   ```

3. Client company can view their assignments:
   ```bash
   curl -X GET "http://localhost:8000/api/clients/1/templates/" \
   -H "Authorization: Bearer {token}"
   ```

4. Baker Tilly admin can remove assignment if needed:
   ```bash
   curl -X DELETE "http://localhost:8000/api/clients/1/templates/" \
   -H "Content-Type: application/json" \
   -H "Authorization: Bearer {token}" \
   -d '{
       "assignment_id": 1
   }'
   ```

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
- `admin_email`: Email for the admin user
- `admin_password`: Password for the admin user
- `admin_name`: Full name of the admin user

Optional fields:
- `location`: Company's location
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