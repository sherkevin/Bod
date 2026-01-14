# Task: Frontend Framework

## Overview

Set up the Next.js 14 frontend framework with TypeScript, Tailwind CSS, shadcn/ui components, and proper project structure.

## Dependencies

- Requires `project-setup` to be completed

## Deliverables

### 1. Project Structure

```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Home page
│   │   ├── globals.css        # Global styles
│   │   ├── (auth)/            # Auth group
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── (main)/            # Main app group
│   │   │   ├── workout/
│   │   │   ├── plan/
│   │   │   ├── equipment/
│   │   │   └── profile/
│   │   └── api/               # API routes (if needed)
│   │
│   ├── components/            # React components
│   │   ├── ui/               # shadcn/ui components
│   │   ├── layout/           # Layout components
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── Sidebar.tsx
│   │   ├── workout/          # Workout components
│   │   ├── plan/             # Plan components
│   │   └── common/           # Shared components
│   │
│   ├── lib/                   # Utilities
│   │   ├── api.ts            # API client
│   │   ├── query.ts          # React Query setup
│   │   ├── auth.ts           # Auth utilities
│   │   └── utils.ts          # General utilities
│   │
│   ├── stores/                # Zustand stores
│   │   ├── auth.ts           # Auth store
│   │   ├── workout.ts        # Workout store
│   │   └── user.ts           # User store
│   │
│   ├── types/                 # TypeScript types
│   │   ├── api.ts            # API response types
│   │   ├── models.ts         # Domain models
│   │   └── index.ts
│   │
│   └── styles/                # Additional styles
│
├── public/                    # Static assets
│   ├── icons/
│   └── images/
│
├── next.config.js            # Next.js config
├── tailwind.config.ts        # Tailwind config
├── tsconfig.json             # TypeScript config
├── components.json           # shadcn/ui config
└── package.json
```

### 2. Configuration Files

#### `next.config.js`
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['localhost'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL + '/api/:path*',
      },
    ];
  },
};
module.exports = nextConfig;
```

#### `tailwind.config.ts`
```typescript
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... more colors
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
export default config;
```

#### `components.json` (shadcn/ui)
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

### 3. Core Components to Set Up

#### Layout Components
- `Header.tsx` - App header with navigation
- `Footer.tsx` - App footer
- `Sidebar.tsx` - Navigation sidebar (mobile)
- `MainLayout.tsx` - Main layout wrapper

#### shadcn/ui Components to Include
- button
- input
- card
- dialog
- toast
- dropdown-menu
- select
- checkbox
- radio-group
- tabs
- badge
- avatar
- progress
- slider

### 4. State Management (Zustand)

#### `stores/auth.ts`
```typescript
import create from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  setAuth: (user, token) => set({ user, token }),
  clearAuth: () => set({ user: null, token: null }),
}));
```

#### `stores/workout.ts`
```typescript
interface WorkoutState {
  currentSession: Session | null;
  currentExercise: Exercise | null;
  setCurrentSession: (session: Session) => void;
  // ...
}

export const useWorkoutStore = create<WorkoutState>((set) => ({
  // ...
}));
```

### 5. API Client (`lib/api.ts`)

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
});

// Request interceptor
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 6. React Query Setup (`lib/query.ts`)

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});
```

### 7. TypeScript Types (`types/models.ts`)

```typescript
export interface User {
  id: string;
  nickname: string;
  gender: 'male' | 'female';
  birth_year: number;
  height: number;
  weight_history: WeightRecord[];
  fitness_level: 'beginner' | 'intermediate' | 'advanced';
  primary_goal: 'fat_loss' | 'muscle_gain' | 'tone' | 'strength' | 'health';
  workout_frequency: number;
  workout_duration: number;
}

export interface Equipment {
  id: string;
  user_id: string;
  name: string;
  category: 'free_weight' | 'machine' | 'cardio' | 'functional';
  weight_range?: string;
  quantity: number;
}

export interface WorkoutPlan {
  id: string;
  user_id: string;
  name: string;
  start_date: string;
  end_date: string;
  weeks_count: number;
  status: 'draft' | 'active' | 'completed' | 'paused';
}

export interface Session {
  id: string;
  plan_id: string;
  scheduled_date: string;
  theme: string;
  exercises: SessionExercise[];
  status: 'scheduled' | 'in_progress' | 'completed' | 'skipped';
}
```

### 8. Root Layout (`app/layout.tsx`)

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/Providers';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Bod - AI Fitness Coach',
  description: 'Your personal AI fitness assistant',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### 9. Environment Variables

`.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Technical Requirements

- Next.js 14 with App Router
- TypeScript 5+
- Tailwind CSS 3+
- shadcn/ui components
- Zustand for state
- React Query for server state
- Axios for API calls

## Acceptance Criteria

- [ ] `pnpm dev` starts successfully on port 3000
- [ ] TypeScript compilation without errors
- [ ] Tailwind CSS styles loading correctly
- [ ] At least 10 shadcn/ui components installed
- [ ] API client configured with interceptors
- [ ] Zustand stores for auth and workout
- [ ] Responsive layout with header
- [ ] Dark mode support
- [ ] Proper 404 page

## Pages to Create

| Path | Description |
|------|-------------|
| `/` | Landing page / Home |
| `/login` | Login page |
| `/register` | Registration page |
| `/workout` | Workout execution page |
| `/plan` | Workout plan view |
| `/equipment` | Equipment management |
| `/profile` | User profile settings |

## Notes

- Use App Router (not Pages Router)
- Implement proper error boundaries
- Add loading states with React Suspense
- Configure proper SEO metadata
- Set up ESLint and Prettier
