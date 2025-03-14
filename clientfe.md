# Baker Tilly Admin Dashboard

## Overview

The Baker Tilly Admin Dashboard provides a comprehensive interface for managing client companies, user access, and ESG reporting. This document outlines the frontend implementation details, including API integrations, component structure, and TypeScript interfaces.

## API Integration

### Authentication

```typescript
interface LoginResponse {
  access: string;
  refresh: string;
  user: {
    id: number;
    email: string;
    role: string;
    is_superuser: boolean;
    is_baker_tilly_admin: boolean;
    must_change_password: boolean;
  }
}
```

### Data Models

```typescript
interface Company {
  id: number;
  company_name: string;
  company_industry: string;
  company_location: string;
  shareholding_ratio: string;
  layer_type: 'GROUP' | 'SUBSIDIARY' | 'BRANCH';
  parent_id: number | null;
  created_at: string;
  app_users: AppUser[];
}

interface AppUser {
  id: number;
  name: string;
  role: 'CREATOR' | 'MANAGEMENT' | 'OPERATION';
  title: string;
  user: {
    id: number;
    email: string;
    role: string;
    is_superuser: boolean;
    is_baker_tilly_admin: boolean;
    must_change_password: boolean;
  };
}

interface CompanyStructure {
  group: Company;
  subsidiaries: Array<{
    subsidiary: Company;
    branches: Company[];
  }>;
}
```

## API Endpoints

### Client Management

1. **List All Clients**
```typescript
// GET /api/layers/?layer_type=GROUP
async function getClientList(): Promise<Company[]> {
  const response = await api.get('/api/layers/', {
    params: { layer_type: 'GROUP' }
  });
  return response.data;
}
```

2. **Get Client Structure**
```typescript
// GET /api/clients/{group_id}/structure/
async function getClientStructure(groupId: number): Promise<CompanyStructure> {
  const response = await api.get(`/api/clients/${groupId}/structure/`);
  return response.data;
}
```

3. **Create New Client**
```typescript
interface ClientSetupData {
  company_name: string;
  industry: string;
  location: string;
  admin_email: string;
  admin_name: string;
  admin_title: string;
  template_id?: number;
}

async function setupNewClient(data: ClientSetupData): Promise<Company> {
  const response = await api.post('/api/clients/setup/', data);
  return response.data;
}
```

### User Management

1. **List Users**
```typescript
// GET /api/clients/{group_id}/users/
async function getClientUsers(groupId: number): Promise<AppUser[]> {
  const response = await api.get(`/api/clients/${groupId}/users/`);
  return response.data;
}
```

2. **Add User**
```typescript
interface NewUserData {
  email: string;
  name: string;
  title: string;
  role: 'CREATOR' | 'MANAGEMENT' | 'OPERATION';
}

async function addUser(groupId: number, data: NewUserData): Promise<AppUser> {
  const response = await api.post(`/api/clients/${groupId}/users/`, data);
  return response.data;
}
```

## Component Structure

### Dashboard Layout

```typescript
// components/dashboard/DashboardLayout.tsx
interface DashboardLayoutProps {
  children: React.ReactNode;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children }) => {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <div className="dashboard-content">
        <TopBar />
        <main>{children}</main>
      </div>
    </div>
  );
};
```

### Client Overview

```typescript
// components/clients/ClientOverview.tsx
interface ClientOverviewProps {
  clients: Company[];
  onAddClient: () => void;
  onExportData: () => void;
}

const ClientOverview: React.FC<ClientOverviewProps> = ({
  clients,
  onAddClient,
  onExportData
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [industryFilter, setIndustryFilter] = useState<string | null>(null);

  const filteredClients = useMemo(() => {
    return clients.filter(client => {
      const matchesSearch = client.company_name
        .toLowerCase()
        .includes(searchTerm.toLowerCase());
      const matchesIndustry = !industryFilter || client.company_industry === industryFilter;
      return matchesSearch && matchesIndustry;
    });
  }, [clients, searchTerm, industryFilter]);

  return (
    <div className="client-overview">
      <header className="overview-header">
        <h1>Client Companies</h1>
        <div className="actions">
          <Button onClick={onAddClient}>Add New Client</Button>
          <Button onClick={onExportData}>Export Data</Button>
        </div>
      </header>
      
      <div className="filters">
        <SearchInput
          value={searchTerm}
          onChange={setSearchTerm}
          placeholder="Search clients..."
        />
        <IndustryFilter
          value={industryFilter}
          onChange={setIndustryFilter}
        />
      </div>

      <ClientList clients={filteredClients} />
    </div>
  );
};
```

### Company Structure

```typescript
// components/company/CompanyStructure.tsx
interface CompanyStructureProps {
  structure: CompanyStructure;
  onAddSubsidiary: (groupId: number) => void;
  onAddBranch: (subsidiaryId: number) => void;
}

const CompanyStructure: React.FC<CompanyStructureProps> = ({
  structure,
  onAddSubsidiary,
  onAddBranch
}) => {
  return (
    <div className="company-structure">
      <div className="group-layer">
        <CompanyCard company={structure.group} />
        <Button onClick={() => onAddSubsidiary(structure.group.id)}>
          Add Subsidiary
        </Button>
      </div>

      <div className="subsidiaries">
        {structure.subsidiaries.map(({ subsidiary, branches }) => (
          <div key={subsidiary.id} className="subsidiary-group">
            <CompanyCard company={subsidiary} />
            <Button onClick={() => onAddBranch(subsidiary.id)}>
              Add Branch
            </Button>
            <div className="branches">
              {branches.map(branch => (
                <CompanyCard key={branch.id} company={branch} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

## State Management

```typescript
// store/slices/clientSlice.ts
interface ClientState {
  clients: Company[];
  selectedClient: Company | null;
  clientStructure: CompanyStructure | null;
  loading: boolean;
  error: string | null;
}

const clientSlice = createSlice({
  name: 'clients',
  initialState: {
    clients: [],
    selectedClient: null,
    clientStructure: null,
    loading: false,
    error: null
  } as ClientState,
  reducers: {
    // ... reducer actions
  },
  extraReducers: (builder) => {
    // ... async thunk handlers
  }
});
```

## Utility Functions

```typescript
// utils/permissions.ts
export function checkUserPermissions(user: LoginResponse['user']) {
  return {
    canManageClients: user.is_baker_tilly_admin || user.is_superuser,
    canManageUsers: user.is_baker_tilly_admin || user.role === 'CREATOR',
    canVerifyData: user.is_baker_tilly_admin,
    canExportData: user.is_baker_tilly_admin || user.role === 'CREATOR'
  };
}

// utils/formatters.ts
export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-HK', {
    timeZone: 'Asia/Hong_Kong',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}
```

## Error Handling

```typescript
// components/common/ErrorBoundary.tsx
interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  { hasError: boolean }
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}
```

## Usage Examples

### Setting Up the Dashboard

```typescript
// pages/dashboard/index.tsx
const DashboardPage: NextPage = () => {
  const { data: clients, isLoading, error } = useQuery(
    'clients',
    getClientList
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <DashboardLayout>
      <ClientOverview
        clients={clients}
        onAddClient={() => {/* ... */}}
        onExportData={() => {/* ... */}}
      />
    </DashboardLayout>
  );
};

// pages/dashboard/clients/[id].tsx
const ClientDetailPage: NextPage = () => {
  const { id } = useRouter().query;
  const { data: structure } = useQuery(
    ['clientStructure', id],
    () => getClientStructure(Number(id))
  );

  return (
    <DashboardLayout>
      <CompanyStructure
        structure={structure}
        onAddSubsidiary={() => {/* ... */}}
        onAddBranch={() => {/* ... */}}
      />
    </DashboardLayout>
  );
};
```

## Styling

The dashboard uses a combination of Tailwind CSS and CSS modules for styling. Example:

```scss
// styles/components/Dashboard.module.scss
.dashboard-layout {
  @apply flex min-h-screen bg-gray-100;

  .dashboard-content {
    @apply flex-1 p-8;
  }

  .overview-header {
    @apply flex justify-between items-center mb-8;
  }

  .client-card {
    @apply bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow;
  }
}
```

## Best Practices

1. **Performance**
   - Use React.memo for expensive components
   - Implement virtualization for long lists
   - Cache API responses appropriately

2. **Security**
   - Validate all user input
   - Implement proper CSRF protection
   - Use secure HTTP-only cookies

3. **Accessibility**
   - Include proper ARIA labels
   - Ensure keyboard navigation
   - Maintain proper heading hierarchy

4. **Error Handling**
   - Implement proper error boundaries
   - Show user-friendly error messages
   - Log errors for debugging

5. **State Management**
   - Use React Query for server state
   - Implement proper loading states
   - Handle optimistic updates

## Getting Started

1. Install dependencies:
```bash
npm install @tanstack/react-query axios @reduxjs/toolkit react-hook-form
```

2. Set up environment variables:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

3. Initialize the dashboard:
```typescript
// pages/_app.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { store } from '../store';

const queryClient = new QueryClient();

function MyApp({ Component, pageProps }) {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <Component {...pageProps} />
      </QueryClientProvider>
    </Provider>
  );
}

export default MyApp;
``` 