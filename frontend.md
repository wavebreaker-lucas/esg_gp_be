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
        email: string,
        role: "CREATOR" | "MANAGEMENT" | "OPERATION",
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
    role: string;
    layer_id: number;
}
```

#### API Endpoints
```typescript
// Add User
POST /api/app_users/{layer_id}/add-user/
Body: {
    user: {
        email: string
    },
    name: string,
    title: string,
    role: "MANAGEMENT" | "OPERATION"
}

// Delete User
DELETE /api/app_users/{id}/

// Import Users
POST /api/app_users/{layer_id}/import-csv/
Content-Type: multipart/form-data
Body: FormData

// Export Users
GET /api/app_users/{layer_id}/export-csv/
```

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