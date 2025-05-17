# Authentication System Documentation

This document outlines the authentication system for the ESG Platform, including login, password management, and user verification flows.

## Authentication Endpoints

| Endpoint | Method | Description | Authentication Required |
|----------|--------|-------------|------------------------|
| `/api/login/` | POST | User login with email and password | No |
| `/api/logout/` | POST | User logout | Yes |
| `/api/token/refresh/` | POST | Refresh JWT token | No (requires refresh token) |
| `/api/request-password-reset/` | POST | Request password reset link (forgotten password) | No |
| `/api/reset-password/<reset_token>/` | POST | Reset password using token (forgotten password) | No |
| `/api/change-password/` | POST | Change password when user knows current password | Yes |

## User Creation and Account Setup

When new users are created in the system, either as initial admin users for a new client or as additional users for an existing client, the system automatically:

1. Generates a secure random password
2. Emails the login credentials to the user's email address
3. Sets the `must_change_password` flag to `true`

This automated email-based approach provides several benefits:
- Enhanced security through system-generated strong passwords
- Improved user experience with immediate credential delivery
- Reduced administrative overhead for user setup

### API Endpoints for User Creation

#### Create Client Setup (Initial Client and Admin User)

**Endpoint:** `/api/clients/setup/`  
**Method:** POST  
**Authentication:** Required (Baker Tilly Admin)

##### Request
```json
{
  "company_name": "Example Corp",
  "industry": "Manufacturing",
  "location": "Singapore",
  "admin_email": "admin@example.com",
  "admin_name": "John Smith",
  "admin_title": "ESG Administrator"
}
```
Note: The admin password is now automatically generated and emailed to the user.

##### Successful Response
```json
{
  "message": "Client setup complete. Login credentials have been emailed to the user.",
  "group": {
    "id": 1,
    "company_name": "Example Corp",
    "company_industry": "Manufacturing",
    "company_location": "Singapore",
    "layer_type": "GROUP",
    "shareholding_ratio": 100.00
  },
  "admin_user": {
    "id": 1,
    "name": "John Smith",
    "title": "ESG Administrator",
    "user": {
      "id": 1,
      "email": "admin@example.com",
      "role": "CREATOR"
    }
  }
}
```

##### Response when Email Delivery Fails
```json
{
  "message": "Client setup complete but email delivery failed. Please provide this password to the user manually.",
  "group": {
    "id": 1,
    "company_name": "Example Corp",
    "company_industry": "Manufacturing",
    "company_location": "Singapore",
    "layer_type": "GROUP",
    "shareholding_ratio": 100.00
  },
  "admin_user": {
    "id": 1,
    "name": "John Smith",
    "title": "ESG Administrator",
    "user": {
      "id": 1,
      "email": "admin@example.com",
      "role": "CREATOR"
    }
  },
  "admin_password": "generated_random_password"
}
```

#### Add User to Client

**Endpoint:** `/api/clients/<group_id>/users/`  
**Method:** POST  
**Authentication:** Required (Baker Tilly Admin)

##### Request
```json
{
  "email": "user@example.com",
  "name": "Jane Doe",
  "title": "ESG Manager",
  "role": "MANAGEMENT"
}
```
Note: The user password is now automatically generated and emailed to the user.

##### Successful Response
```json
{
  "message": "User added successfully. Login credentials have been emailed to the user.",
  "user": {
    "id": 2,
    "name": "Jane Doe",
    "title": "ESG Manager",
    "user": {
      "id": 2,
      "email": "user@example.com",
      "role": "MANAGEMENT"
    }
  }
}
```

##### Response when Email Delivery Fails
```json
{
  "message": "User added successfully but email delivery failed. Please provide this password to the user manually.",
  "user": {
    "id": 2,
    "name": "Jane Doe",
    "title": "ESG Manager",
    "user": {
      "id": 2,
      "email": "user@example.com",
      "role": "MANAGEMENT"
    }
  },
  "user_password": "generated_random_password"
}
```

### Email Delivery

Credentials are sent using Azure Communication Services email, providing reliable delivery and monitoring capabilities. The email includes:
- The user's email address (username)
- The generated password
- Instructions to change the password upon first login

If email delivery fails for any reason, the system includes the generated password in the API response to administrators, ensuring credentials can still be securely provided to users through alternative channels.

## Login Flow

1. User submits email and password to `/api/login/`
2. System validates credentials
3. If valid, returns JWT tokens (access and refresh) and user data
4. User data includes the `must_change_password` flag
5. If `must_change_password` is true, frontend should redirect to password change screen

### Request
```json
{
  "email": "user@example.com",
  "password": "current-password"
}
```

### Response
```json
{
  "access": "jwt-access-token",
  "refresh": "jwt-refresh-token",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "OPERATION",
    "is_superuser": false,
    "is_baker_tilly_admin": false,
    "must_change_password": true
  }
}
```

## Password Management

There are two distinct ways to update a user's password in the system:

1. **Password Change** - For authenticated users who know their current password
2. **Password Reset** - For users who have forgotten their password and need to reset it

Both methods will set the `must_change_password` flag to `false` when completed successfully.

### 1. Change Password (for authenticated users)

Used when:
- A user knows their current password but wants to change it
- A user has logged in and sees `must_change_password: true` in their user data
- Security policies require a password change

**Endpoint:** `/api/change-password/`  
**Method:** POST  
**Authentication:** Required (JWT token)

#### Request
```json
{
  "old_password": "current-password",
  "new_password": "new-password"
}
```

#### Response
```json
{
  "message": "Password changed successfully."
}
```

When a user successfully changes their password:
- The `must_change_password` flag is set to `false`
- The `password_updated_at` timestamp is updated
- The user remains logged in (session is maintained)

### 2. Password Reset (for forgotten passwords)

Used when:
- A user has forgotten their password and cannot log in
- A user needs to regain access to their account

This is a two-step process:

#### Step 1: Request Reset Link

**Endpoint:** `/api/request-password-reset/`  
**Method:** POST  
**Authentication:** Not required

##### Request
```json
{
  "email": "user@example.com"
}
```

##### Response
```json
{
  "message": "Password reset link sent to your email."
}
```

The system will:
1. Generate a unique reset token
2. Send an email with a reset link containing the token
3. The link will direct the user to a password reset page in the frontend

#### Step 2: Reset Password with Token

**Endpoint:** `/api/reset-password/<reset_token>/`  
**Method:** POST  
**Authentication:** Not required (uses reset token instead)

##### Request
```json
{
  "new_password": "new-password"
}
```

##### Response
```json
{
  "message": "Password reset successfully."
}
```

When a user successfully resets their password:
- The `must_change_password` flag is set to `false`
- The `password_updated_at` timestamp is updated
- The reset token is invalidated
- The user will need to log in with the new password

## Must Change Password Feature

The `must_change_password` flag is used to enforce password changes in certain situations:

1. **New User Creation**: When a new user is created, this flag is set to `true` by default
2. **Admin Reset**: When an admin resets a user's password
3. **Security Policy**: May be set to `true` based on security policies (e.g., password expiration)

### Frontend Implementation

When a user logs in and the response includes `must_change_password: true`, the frontend should:

1. Redirect the user to a password change screen
2. Not allow access to other parts of the application until the password is changed
3. Use the `/api/change-password/` endpoint to update the password
4. After successful password change, allow normal application access

### Backend Implementation

The `must_change_password` flag is:
- Stored in the `CustomUser` model as a boolean field
- Set to `true` by default for new users
- Set to `false` when a user successfully changes their password (via either method)
- Included in the login response for frontend handling 