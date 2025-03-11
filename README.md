# ESG Platform - GreenPoint

A Django-based platform for managing company hierarchies and user access control with a focus on ESG (Environmental, Social, and Governance) reporting.

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

## Core Features

### 1. Company Layer Management
- Three-tier company hierarchy:
  - Group Layer (Top level)
  - Subsidiary Layer (Mid level)
  - Branch Layer (Bottom level)
- Company profile management
- Shareholding ratio tracking
- Location and industry tracking

### 2. User Management
- Role-based access control:
  
  **CREATOR Role**
  - Highest level of access within their company structure
  - Can create and manage company layers (Group → Subsidiary → Branch)
  - Can add/remove users in their layers and child layers
  - Has access to all company data and management functions
  - Typically assigned to company administrators or top management
  - Example: CEO, Company Administrator

  **MANAGEMENT Role**
  - Mid-level access within their assigned layer
  - Can manage users within their assigned layer
  - Can view and edit company information
  - Cannot create new company layers
  - Cannot access parent layer data
  - Example: Regional Manager, Department Head

  **OPERATION Role**
  - Basic access level for day-to-day operations
  - Can view their layer's information
  - Can update their own profile
  - Cannot modify company structure
  - Cannot manage other users
  - Example: Staff Member, Regular Employee

- Email-based authentication
- Two-factor authentication with OTP
- Password management with security policies
- Bulk user import/export via CSV
- User profile management within layers

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
├── services.py    # Contains core business logic and reusable functions
├── urls.py        # Maps URLs to their corresponding views
├── views/         # Handles HTTP requests and business logic
└── serializers/   # Converts data between Python and JSON formats
```

### Components

#### 1. Models (Database Tables)
- `CustomUser`: Extended user model with role management
  - Handles user authentication and permissions
  - Stores user credentials and preferences
- `LayerProfile`: Base model for company hierarchy
  - Common fields for all company types
  - Handles shared functionality
  - `GroupLayer`: Top-level company representation (Parent company)
  - `SubsidiaryLayer`: Mid-level companies (Child companies)
  - `BranchLayer`: Branch offices (Local operations)
- `AppUser`: Links users to company layers
  - Manages user-company relationships
  - Stores user metadata like name and title

#### 2. Core Files
- **admin.py** (Django Admin Configuration)
  - Custom admin interface for all models
  - Enhanced display and filtering options
  - Optimized queries for admin views
  - Custom actions and inline models

- **permissions.py** (Access Control)
  - `IsManagement`: Allows access to management functions
  - `IsOperation`: Restricts access to operational tasks
  - `IsCreator`: Provides company creation privileges
  - `CanManageAppUsers`: Controls user management capabilities

- **services.py** (Business Logic)
  - Email services (Sending notifications, verifications)
  - OTP generation and validation (Security)
  - Password management (Reset, validation)
  - Layer access validation (Security checks)
  - User management utilities (Helper functions)

#### 3. Views and Serializers
```
views/                          serializers/
├── auth.py                     ├── auth.py
├── registration.py             └── models.py
├── layer_management.py
├── user_management.py
└── mixins.py
```

### Role-Based Access Control (RBAC)

The platform implements a hierarchical role-based access control system that ensures secure and organized data access:

#### Role Hierarchy
1. **CREATOR Role**
   - Highest level of access
   - Can create and manage all layer types (Group, Subsidiary, Branch)
   - Full user management capabilities
   - Access to all company data and analytics
   - Typically assigned to company administrators

2. **MANAGEMENT Role**
   - Mid-level access
   - Can manage users within their assigned layer
   - View and edit company information at their layer
   - Cannot create new layers or access parent layer data
   - Suitable for department heads and team leaders

3. **OPERATION Role**
   - Basic access level
   - Can view their layer's information
   - Update their own profile
   - Limited to operational tasks
   - Designed for regular staff members

#### Access Control Implementation
- Role verification happens through the `permissions.py` file
- Each API endpoint checks user roles using permission classes
- Layer access is validated using the `has_layer_access` service
- Role assignments are stored securely in the user model
- Changes to user roles are logged for audit purposes

#### Security Considerations
- Roles cannot be modified through regular API endpoints
- Users cannot escalate their own privileges
- All role-related actions require proper authentication
- Failed access attempts are logged for security monitoring

## API Reference
All API endpoints require authentication unless specified otherwise.

### Authentication Endpoints
These endpoints handle user authentication and account management:

- `POST /api/register-layer-profile/` - Create new company and admin account (No auth required)
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

1. Register a Group Layer:
```json
POST /api/register-layer-profile/
{
  "user": {
    "email": "creator@example.com",
    "password": "secure_password"
  },
  "group_layer": {
    "company_name": "Example Group",
    "company_industry": "Technology",
    "company_location": "Hong Kong"
  }
}
```

2. Add a Subsidiary:
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