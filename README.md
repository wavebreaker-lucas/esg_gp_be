# ESG Platform - GreenPoint

A Django-based platform for managing company hierarchies and user access control with a focus on ESG (Environmental, Social, and Governance) reporting.

## Features

### Company Layer Management
- Three-tier company hierarchy:
  - Group Layer (Top level)
  - Subsidiary Layer (Mid level)
  - Branch Layer (Bottom level)
- Company profile management
- Shareholding ratio tracking
- Location and industry tracking

### User Management
- Role-based access control (CREATOR, MANAGEMENT, OPERATION)
- Email-based authentication
- Two-factor authentication with OTP
- Password management with security policies
- Bulk user import/export via CSV
- User profile management within layers

### Security Features
- JWT-based authentication
- Email verification system
- Password reset functionality
- Role-based permissions
- Layer-based access control
- OTP system for verification
- Session management

### Data Management
- CSV import/export functionality
- Bulk operations support
- Caching for performance
- Transaction management
- Error handling and logging

## Technical Architecture

### Core Components

#### Core Django Files
```
accounts/
├── admin.py       # Django admin interface customization
├── apps.py        # App configuration
├── models.py      # Database models and relationships
├── permissions.py # Custom permission classes
├── services.py    # Business logic and utilities
├── urls.py        # URL routing
├── views/         # View modules
└── serializers/   # Serializer modules
```

#### Models
- `CustomUser`: Extended user model with role management
- `LayerProfile`: Base model for company hierarchy
  - `GroupLayer`: Top-level company representation
  - `SubsidiaryLayer`: Mid-level companies
  - `BranchLayer`: Branch offices
- `AppUser`: Links users to company layers

#### Core Files Description

##### admin.py
- Custom admin interface for all models
- Enhanced display and filtering options
- Optimized queries for admin views
- Custom actions and inline models

##### permissions.py
- `IsManagement`: Permission class for management role
- `IsOperation`: Permission class for operation role
- `IsCreator`: Permission class for creator role
- `CanManageAppUsers`: Permission class for user management

##### services.py
- Email services
- OTP generation and validation
- Password management
- Layer access validation
- User management utilities

##### urls.py
- API endpoint routing
- JWT authentication endpoints
- Layer management routes
- User management routes

#### Views Organization
```
views/
├── auth.py         # Authentication views
├── registration.py # Registration handling
├── layer_management.py # Layer CRUD operations
├── user_management.py  # User management
└── mixins.py      # Shared view functionality
```

#### Serializers Organization
```
serializers/
├── auth.py    # Authentication serializers
└── models.py  # Model serializers
```

### API Endpoints

#### Authentication
- `POST /api/register-layer-profile/` - Register company and creator
- `POST /api/login/` - User login
- `POST /api/logout/` - User logout
- `POST /api/verify-otp/` - Verify OTP code
- `POST /api/resend-otp/` - Resend OTP code
- `POST /api/token/refresh/` - Refresh JWT token
- `POST /api/request-password-reset/` - Request password reset
- `POST /api/reset-password/<token>/` - Reset password

#### Layer Management
- `GET /api/layers/` - List accessible layers
- `POST /api/layers/` - Create new layer
- `GET /api/layers/<id>/` - Get layer details
- `PUT /api/layers/<id>/` - Update layer
- `DELETE /api/layers/<id>/` - Delete layer
- `POST /api/layers/import-csv/` - Import layers from CSV
- `GET /api/layers/download-example/` - Download CSV template

#### User Management
- `GET /api/app_users/` - List users
- `POST /api/app_users/` - Create user
- `GET /api/app_users/<id>/` - Get user details
- `PUT /api/app_users/<id>/` - Update user
- `DELETE /api/app_users/<id>/` - Delete user
- `POST /api/app_users/<id>/add-user/` - Add user to layer
- `POST /api/app_users/<id>/import-csv/` - Import users from CSV
- `GET /api/app_users/<id>/export-csv/` - Export users to CSV

## Setup and Installation

1. Clone the repository
```bash
git clone [repository-url]
cd esg_platform_greenpoint
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run migrations
```bash
python manage.py migrate
```

6. Create superuser
```bash
python manage.py createsuperuser
```

7. Run the development server
```bash
python manage.py runserver
```

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

1. Add User to Layer:
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