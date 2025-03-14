# ESG Platform Frontend Development Guide

## Overview

This guide outlines the requirements and specifications for developing the frontend application for the ESG Platform. The platform enables Baker Tilly to manage client companies' ESG reporting processes through a hierarchical company structure and role-based access control system.

## Technical Requirements

### Stack
- Framework: Next.js (latest stable version)
- Language: TypeScript
- UI Framework: shadcn/ui (based on Radix UI and Tailwind CSS)
- State Management: Your choice (Redux/Zustand/React Query recommended)
- API Integration: REST with JWT authentication
- CSV Import/Export Support

### UI Component Library Setup
```bash
# 1. Install shadcn/ui CLI
npm install shadcn-ui@latest

# 2. Initialize shadcn/ui with Next.js
npx shadcn-ui@latest init

# 3. Follow the CLI prompts:
# - Would you like to use TypeScript? Yes
# - Which style would you like to use? Default
# - Which color would you like to use as base color? Slate
# - Where is your global CSS file? app/globals.css
# - Would you like to use CSS variables? Yes
# - Where is your tailwind.config.js located? tailwind.config.js
# - Configure the import alias for components? @/components
# - Configure the import alias for utils? @/lib/utils
```

### Required shadcn/ui Components
```bash
# Authentication
npx shadcn-ui@latest add form
npx shadcn-ui@latest add input
npx shadcn-ui@latest add button
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add toast

# Company Management
npx shadcn-ui@latest add tree
npx shadcn-ui@latest add card
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add select
npx shadcn-ui@latest add badge

# User Management
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add avatar
npx shadcn-ui@latest add sheet

# Common Components
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add breadcrumb
npx shadcn-ui@latest add progress
npx shadcn-ui@latest add separator
```

### Authentication

#### Login Flow
```typescript
// 1. Login Request
POST /api/login/
Body: {
    email: string,
    password: string
}

// 2. Login Response
{
    refresh: string,  // JWT refresh token
    access: string,   // JWT access token
    user: {
        id: number,
        email: string,
        role: "CREATOR" | "MANAGEMENT" | "OPERATION",
        is_superuser: boolean,
        is_baker_tilly_admin: boolean,
        must_change_password: boolean,
        requires_otp: boolean
    }
}

// 3. OTP Verification (if required)
POST /api/verify-otp/
Body: {
    email: string,
    otp: string
}

// 4. OTP Resend
POST /api/resend-otp/
Body: {
    email: string
}
```

#### Security Features
- JWT-based authentication
- Two-factor authentication (OTP)
- Password complexity rules
- Email verification system
- Password reset functionality
- Session management
- Token refresh mechanism

#### Token Management
- Store tokens securely (e.g., HTTP-only cookies)
- Include in requests: `Authorization: Bearer <token>`
- Handle token refresh on 401 responses
- Token expiry: 1 hour
- Implement refresh token rotation

## Core Features

### 1. Company Hierarchy Management

#### Data Structure
```typescript
interface Layer {
    id: number;
    company_name: string;
    company_industry: string;
    shareholding_ratio: number;
    layer_type: "GROUP" | "SUBSIDIARY" | "BRANCH";
    company_location: string;
    created_at: string;
    app_users: AppUser[];
    user_count: number;
    parent_id?: number;
}
```

#### API Endpoints
```typescript
// Get Layers
GET /api/layers/

// Create Layer
POST /api/layers/
Body: {
    layer_type: "SUBSIDIARY" | "BRANCH",
    company_name: string,
    company_industry: string,
    company_location: string,
    shareholding_ratio: number,
    group_id?: number,      // Required for SUBSIDIARY
    subsidiary_id?: number  // Required for BRANCH
}

// Delete Layer
DELETE /api/layers/{id}/

// Import Companies
POST /api/layers/import-csv/
Content-Type: multipart/form-data
Body: FormData

// Download CSV Template
GET /api/layers/download-example/
```

### 2. User Management

#### Data Structure
```typescript
interface AppUser {
    id: number;
    user: {
        id: number;
        email: string;
        role: "CREATOR" | "MANAGEMENT" | "OPERATION";
        is_superuser: boolean;
        must_change_password: boolean;
    };
    name: string;
    title: string;
    layer_id: number;
}
```

#### Role-Based Access Control
1. **CREATOR Role**:
   - Can manage company structure (create SUBSIDIARY and BRANCH layers only)
   - Can add/remove users in their layers and child layers
   - Gets automatic access to child layers when created
   - Not counted in the 5-user limit per layer
   - Automatically inherits CREATOR role in child layers
   - Can have different display names in different layers

2. **MANAGEMENT Role**:
   - Can manage users within their assigned layer only
   - Can view and manage layer data
   - Counted in the 5-user limit
   - Cannot create or modify company structure

3. **OPERATION Role**:
   - Basic access for viewing and personal updates
   - Access limited to their assigned layer
   - Counted in the 5-user limit
   - No user management permissions

#### User Management API
```typescript
// Get users in a layer
GET /api/layers/{layer_id}/users/

// Get specific AppUser details
GET /api/app_users/{app_user_id}/

// Add User to Layer
POST /api/app_users/{layer_id}/add-user/
Body: {
    user: {
        email: string  // Must be wrapped in user object
    },
    name: string,
    title: string,
    role: "MANAGEMENT" | "OPERATION"  // CREATOR role can only be assigned by Baker Tilly admins
}

// Delete User
DELETE /api/app_users/{app_user_id}/

// Import Users (CSV)
POST /api/app_users/{layer_id}/import-csv/
Content-Type: multipart/form-data
Body: FormData

// Export Users (CSV)
GET /api/app_users/{layer_id}/export-csv/

// Resend login credentials
POST /api/app_users/{layer_id}/resend-email/
Body: {
    email: string
}
```

Note: The `app_user_id` in the URLs refers to the ID of a specific AppUser record, while `layer_id` refers to the ID of the layer you want to manage users for.

#### Implementation Guidelines

1. **User Creation**:
   ```typescript
   async function addUserToLayer(layerId: number, userData: {
       email: string;
       name: string;
       title: string;
       role: "MANAGEMENT" | "OPERATION";
   }) {
       const response = await fetch(`/api/app_users/${layerId}/add-user/`, {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json',
               'Authorization': `Bearer ${accessToken}`
           },
           body: JSON.stringify({
               user: { email: userData.email },
               name: userData.name,
               title: userData.title,
               role: userData.role
           })
       });

       if (!response.ok) {
           const error = await response.json();
           throw new Error(error.message || 'Failed to add user');
       }

       return response.json();
   }
   ```

2. **User Limits**:
   ```typescript
   function validateUserLimit(currentUsers: AppUser[], role: string): boolean {
       const nonCreatorCount = currentUsers.filter(
           user => user.user.role !== "CREATOR"
       ).length;
       return role === "CREATOR" || nonCreatorCount < 5;
   }
   ```

3. **Permission Checks**:
   ```typescript
   function canManageUsers(currentUser: AppUser, targetLayer: Layer): boolean {
       return (
           currentUser.user.role === "CREATOR" ||
           (currentUser.user.role === "MANAGEMENT" && 
            currentUser.layer_id === targetLayer.id)
       );
   }
   ```

4. **Error Handling**:
   - 201: User successfully created
   - 204: User successfully deleted
   - 400: Invalid data (e.g., email format)
   - 403: Permission denied
   - 409: User limit exceeded
   - 422: Email already exists

#### UI Components

1. **User List**:
```typescript
interface UserListProps {
    layerId: number;
    currentUserRole: "CREATOR" | "MANAGEMENT" | "OPERATION";
}

function UserList({ layerId, currentUserRole }: UserListProps) {
    const canManage = currentUserRole === "CREATOR" || currentUserRole === "MANAGEMENT";
    
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Title</TableHead>
                    {canManage && <TableHead>Actions</TableHead>}
                </TableRow>
            </TableHeader>
            {/* Table body implementation */}
        </Table>
    );
}
```

2. **Add User Form**:
```typescript
interface AddUserFormProps {
    layerId: number;
    onSuccess: () => void;
    currentUserCount: number;
}

function AddUserForm({ layerId, onSuccess, currentUserCount }: AddUserFormProps) {
    const canAddMore = currentUserCount < 5;
    
    return (
        <Form onSubmit={async (data) => {
            if (!canAddMore) {
                toast.error("Maximum user limit reached (5 non-creator users)");
                return;
            }
            try {
                await addUserToLayer(layerId, data);
                toast.success("User added successfully");
                onSuccess();
            } catch (error) {
                toast.error(error.message);
            }
        }}>
            {/* Form fields implementation */}
        </Form>
    );
}
```

3. **User Actions**:
```typescript
interface UserActionsProps {
    user: AppUser;
    currentUserRole: string;
    onDelete: () => Promise<void>;
}

function UserActions({ user, currentUserRole, onDelete }: UserActionsProps) {
    const canDelete = currentUserRole === "CREATOR" || 
                     (currentUserRole === "MANAGEMENT" && user.user.role === "OPERATION");
    
    return (
        <DropdownMenu>
            {canDelete && (
                <DropdownMenuItem onClick={onDelete}>
                    Delete User
                </DropdownMenuItem>
            )}
        </DropdownMenu>
    );
}
```

#### Best Practices

1. **User Management**:
   - Validate email format before submission
   - Show clear error messages for validation failures
   - Implement confirmation dialogs for deletions
   - Show loading states during API calls
   - Handle user limit gracefully in UI
   - Keep user list updated after changes
   - Show role-specific UI elements based on permissions

2. **Role Handling**:
   - Clearly display user roles and permissions
   - Disable actions based on user's role
   - Show helpful tooltips for disabled actions
   - Handle inherited permissions correctly
   - Update UI when permissions change

3. **Error Handling**:
   - Show user-friendly error messages
   - Handle network failures gracefully
   - Implement retry mechanisms
   - Log errors for debugging
   - Maintain consistent error UX

## Business Rules

### Company Structure
1. Three-tier hierarchy:
   ```
   GROUP
   └── SUBSIDIARY
       └── BRANCH
   ```
2. Access rules:
   - CREATOR has full access to their assigned layer and all child layers
   - MANAGEMENT has access to their assigned layer only
   - OPERATION has basic access to their assigned layer
   - Subsidiaries must have a parent group
   - Branches must have a parent subsidiary
   - Deleting a parent cascades to children

### User Management
1. Role assignment:
   - CREATOR: Company-level administration and full hierarchical access
   - MANAGEMENT: Layer-level administration and user management
   - OPERATION: Basic user access and data entry
2. Constraints:
   - Max 5 non-creator users per layer
   - Email must be unique across the platform
   - CREATOR of parent automatically gets access to child layers
   - Users receive email notifications for account creation
   - Password change required on first login

## UI Requirements

### 1. Company Management
- Hierarchical tree view using shadcn/ui Tree component
- Company details in Card components
- Add/Edit/Delete operations via Dialog components
- Layer type indicators using Badge components
- User count display with Progress component
- CSV import/export with Button and Alert feedback
- Shareholding ratio in formatted display

### 2. User Management
- User list using shadcn/ui Table component
- Add/Remove interface with Sheet component
- Role selection using Select component
- User avatars with Avatar component
- Action menus using DropdownMenu
- Status indicators with Badge component
- Form validation with Form component

### 3. Common Elements
- Toast notifications for actions
- Breadcrumb navigation
- Loading states with Progress
- Tab-based navigation where appropriate
- Consistent spacing using Separator
- Responsive dialog boxes
- Accessible form inputs
- Dark mode support

### 4. Theme Customization
```typescript
// lib/theme.ts
export const themeConfig = {
  colors: {
    primary: {
      DEFAULT: "hsl(var(--primary))",
      foreground: "hsl(var(--primary-foreground))",
    },
    // Add Baker Tilly brand colors
  },
  borderRadius: {
    lg: "var(--radius)",
    md: "calc(var(--radius) - 2px)",
    sm: "calc(var(--radius) - 4px)",
  }
}
```

## Development Guidelines

### 1. Code Organization
```
src/
├── components/
│   ├── ui/         # shadcn/ui components
│   ├── auth/       # Authentication components
│   ├── company/    # Company management
│   ├── users/      # User management
│   └── common/     # Shared components
├── hooks/          # Custom hooks
├── services/       # API services
├── types/          # TypeScript definitions
├── lib/           # Utilities and configurations
│   ├── utils.ts   # shadcn/ui utilities
│   └── theme.ts   # Theme configuration
└── styles/        # Global styles and CSS variables
```

### 2. Best Practices
- Use shadcn/ui components consistently
- Follow Radix UI's accessibility guidelines
- Implement responsive design using Tailwind CSS
- Add loading states for all async operations
- Handle errors gracefully with Toast notifications
- Write clean, maintainable code
- Add comments for complex logic
- Implement unit and integration tests
- Use proper error boundaries
- Implement proper form validation using react-hook-form
- Handle file uploads securely

### 3. State Management
- Centralize API state management
- Implement proper caching strategies
- Handle loading and error states
- Optimize re-renders
- Manage form state efficiently
- Handle file upload progress
- Implement proper websocket handling if needed

## Getting Started

1. Clone the repository:
```bash
git clone [repository-url]
cd esg-platform-frontend
```

2. Install dependencies:
```bash
npm install
# or
yarn install
```

3. Set up environment variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_FILE_UPLOAD_MAX_SIZE=5242880
NEXT_PUBLIC_DEFAULT_THEME=light
```

4. Install additional dependencies:
```bash
# Install required dependencies
npm install @radix-ui/react-icons
npm install react-hook-form @hookform/resolvers zod
npm install tailwindcss-animate
npm install @tanstack/react-table
npm install clsx tailwind-merge
```

5. Start development server:
```bash
npm run dev
# or
yarn dev
```

## API Base URL
Development: http://localhost:8000/api/

## Additional Resources
- [Backend API Documentation](./README.md)
- [Company Structure Guide](./README.md#company-structure)
- [User Management Guide](./README.md#user-management)
- [Authentication Guide](./README.md#authentication-and-security)

## User Table API

### Get User Table Data
```typescript
GET /api/app_users/table/
```

This endpoint provides a simplified and efficient way to fetch user data for tables. It replaces the previous `/api/app_users/group-hierarchy/` endpoint with several improvements:

1. **Flexible Filtering**
   ```typescript
   // Query Parameters
   interface QueryParams {
     group_id?: string;      // Filter by group layer
     subsidiary_id?: string; // Filter by subsidiary layer
     branch_id?: string;    // Filter by branch layer
     role?: string;         // Filter by user role
   }
   ```

2. **Response Structure**
   ```typescript
   interface UserTableResponse {
     users: Array<{
       id: number;
       name: string;
       email: string;
       role: 'CREATOR' | 'MANAGEMENT' | 'OPERATION';
       title: string;
       is_active: boolean;
       must_change_password: boolean;
       layer: {
         id: number;
         name: string;
         type: 'GROUP' | 'SUBSIDIARY' | 'BRANCH';
         parent?: {
           id: number;
           name: string;
           type: string;
         };
         group?: {
           id: number;
           name: string;
           type: 'GROUP';
         };
       };
     }>;
     total: number;
   }
   ```

3. **React Component Example**
   ```tsx
   import React, { useEffect, useState } from 'react';
   import { Table, Tag, Space } from 'antd';

   interface UserTableProps {
     groupId?: number;
     subsidiaryId?: number;
     branchId?: number;
   }

   export const UserTable: React.FC<UserTableProps> = ({ 
     groupId,
     subsidiaryId,
     branchId 
   }) => {
     const [loading, setLoading] = useState(false);
     const [users, setUsers] = useState([]);
     const [total, setTotal] = useState(0);

     useEffect(() => {
       const fetchUsers = async () => {
         setLoading(true);
         try {
           const params = new URLSearchParams();
           if (groupId) params.append('group_id', groupId.toString());
           if (subsidiaryId) params.append('subsidiary_id', subsidiaryId.toString());
           if (branchId) params.append('branch_id', branchId.toString());

           const response = await fetch(`/api/app_users/table/?${params}`);
           const data = await response.json();
           setUsers(data.users);
           setTotal(data.total);
         } catch (error) {
           console.error('Failed to fetch users:', error);
         } finally {
           setLoading(false);
         }
       };

       fetchUsers();
     }, [groupId, subsidiaryId, branchId]);

     const columns = [
       {
         title: 'Name',
         dataIndex: 'name',
         key: 'name',
       },
       {
         title: 'Email',
         dataIndex: 'email',
         key: 'email',
       },
       {
         title: 'Role',
         dataIndex: 'role',
         key: 'role',
         render: (role: string) => (
           <Tag color={
             role === 'CREATOR' ? 'green' :
             role === 'MANAGEMENT' ? 'blue' : 'default'
           }>
             {role}
           </Tag>
         ),
       },
       {
         title: 'Company',
         key: 'company',
         render: (_, record) => (
           <Space direction="vertical" size="small">
             <Tag>{record.layer.name}</Tag>
             {record.layer.parent && (
               <Tag color="blue">{record.layer.parent.name}</Tag>
             )}
             {record.layer.group && record.layer.type !== 'GROUP' && (
               <Tag color="green">{record.layer.group.name}</Tag>
             )}
           </Space>
         ),
       },
       {
         title: 'Status',
         key: 'status',
         render: (_, record) => (
           <Space>
             {!record.is_active && <Tag color="red">Inactive</Tag>}
             {record.must_change_password && (
               <Tag color="orange">Password Change Required</Tag>
             )}
           </Space>
         ),
       }
     ];

     return (
       <Table
         loading={loading}
         dataSource={users}
         columns={columns}
         rowKey="id"
         pagination={{
           total,
           showSizeChanger: true,
           showTotal: (total) => `Total ${total} users`
         }}
       />
     );
   };
   ```

### Advantages Over Previous Implementation

1. **Simplified Data Structure**
   - Flattened user data for easier table rendering
   - Clear hierarchy information without nested arrays
   - Direct access to user status and permissions

2. **Flexible Filtering**
   - Filter by any layer type (group, subsidiary, branch)
   - Filter by user role
   - Easy to extend with additional filters

3. **Performance Optimizations**
   - Efficient database queries using select_related and prefetch_related
   - No redundant data in the response
   - Lighter payload size

4. **Better Frontend Integration**
   - Simpler state management
   - Easier to implement sorting and filtering
   - More intuitive data structure for table components

// ... existing content ... 

// TypeScript Interfaces

interface User {
    id: number;
    email: string;
    role: UserRole;
    is_superuser: boolean;
    is_baker_tilly_admin: boolean;
    must_change_password: boolean;
    requires_otp: boolean;
}

type UserRole = "CREATOR" | "MANAGEMENT" | "OPERATION";

interface LoginResponse {
    refresh: string;
    access: string;
    user: User;
}

// Example Usage:
const checkUserPermissions = (user: User) => {
    if (user.is_baker_tilly_admin) {
        // Show Baker Tilly admin features
        // - Template management
        // - All client access
        // - ESG verification tools
    } else if (user.role === "CREATOR") {
        // Show company admin features
        // - Company structure management
        // - User management for their layers
    }
    // ... handle other roles
};

// Layer Management Types
export type LayerType = 'GROUP' | 'SUBSIDIARY' | 'BRANCH';

export interface Layer {
  id: string;
  name: string;
  layer_type: LayerType;
  user_count: number;
  app_users: AppUser[];
}

export interface AppUser {
  id: string;
  user: {
    id: string;
    email: string;
    role: UserRole;
  };
}

// Example function to fetch groups
async function fetchGroups(): Promise<Layer[]> {
  const response = await fetch('/api/layers/?layer_type=GROUP', {
    headers: {
      'Authorization': `Bearer ${getAccessToken()}`,
    },
  });
  
  if (!response.ok) {
    throw new Error('Failed to fetch groups');
  }
  
  return response.json();
}

// Example usage in a dashboard component
function GroupDashboard() {
  const [groups, setGroups] = useState<Layer[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchGroups()
      .then(setGroups)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);
  
  return (
    <div>
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div>
          <h2>Groups Overview</h2>
          {groups.map(group => (
            <GroupCard 
              key={group.id}
              name={group.name}
              userCount={group.user_count}
              users={group.app_users}
            />
          ))}
        </div>
      )}
    </div>
  );
} 