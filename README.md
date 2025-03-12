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
   - GROUP: Top-level company
   - SUBSIDIARY: Mid-level company, must have a parent GROUP
   - BRANCH: Bottom-level company, must have a parent SUBSIDIARY

2. **Access Control**
   - CREATOR users get automatic access to child layers
   - Users can have different roles in different layers
   - Layer access is enforced through AppUser associations

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

### User Management

1. Add User to Layer:

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

### 3. Security Features
- JWT-based authentication
- Email verification system
- Password reset functionality
- Role-based permissions
- Layer-based access control
- OTP system for verification
- Session management

### 4. Data Management
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

- `GET /api/clients/<id>/structure/` - View client company structure
- `POST /api/clients/<id>/structure/` - Add subsidiary or branch to client
  ```json
  {
    "layer_type": "SUBSIDIARY",
    "company_name": "Example Asia",
    "industry": "Technology",
    "location": "Singapore",
    "shareholding_ratio": 75.5
  }
  ```

- `GET /api/clients/<id>/users/` - List all users in client company
- `POST /api/clients/<id>/users/` - Add new user to client company
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password",
    "name": "Jane Smith",
    "title": "ESG Manager",
    "role": "MANAGEMENT"
  }
  ```

### Authentication Endpoints
These endpoints handle user authentication and account management:

- `POST /api/login/` - Authenticate user and get access token (No auth required)
- `POST /api/logout/` - Invalidate current access token
- `POST /api/verify-otp/` - Verify email using OTP code (No auth required)
- `POST /api/resend-otp/` - Request new OTP code (No auth required)
- `POST /api/token/refresh/` - Get new access token using refresh token
- `POST /api/request-password-reset/` - Start password reset process (No auth required)
- `POST /api/reset-password/<token>/` - Complete password reset (No auth required)

### Layer Management Endpoints
These endpoints manage the company hierarchy structure:

- `GET /api/layers/` - Get list of companies user has access to
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
POST /api/clients/<group_id>/structure/
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
GET /api/clients/<group_id>/structure/
```

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