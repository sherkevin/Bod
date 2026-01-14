# Task: Auth System

## Overview

Implement JWT-based authentication system with registration, login, token refresh, and password reset functionality.

## Dependencies

- Requires `backend-framework` to be completed
- Requires `database-schema` to be completed

## Deliverables

### 1. Backend Implementation

#### `services/auth_service.py`
```python
from datetime import timedelta
from sqlalchemy.orm import Session
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, data: UserRegister) -> TokenResponse:
        # Check if user exists
        if self.db.query(User).filter(User.email == data.email).first():
            raise BadRequestException("Email already registered")

        # Create user
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            nickname=data.nickname,
            # ... other fields
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Generate token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=7)
        )

        return TokenResponse(access_token=access_token, user=user)

    def login(self, data: UserLogin) -> TokenResponse:
        user = self.db.query(User).filter(User.email == data.email).first()

        if not user or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedException("Invalid credentials")

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=7)
        )

        return TokenResponse(access_token=access_token, user=user)

    def get_current_user(self, user_id: str) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UnauthorizedException("User not found")
        return user
```

#### `api/v1/auth.py`
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.auth import get_current_user
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.register(data)

@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.login(data)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout():
    # Client-side token deletion
    return {"message": "Logged out successfully"}
```

#### `core/auth.py`
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import settings
from app.services.auth_service import AuthService

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    service = AuthService(db)
    return service.get_current_user(user_id)
```

### 2. Pydantic Schemas

#### `schemas/auth.py`
```python
from pydantic import BaseModel, EmailStr
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str  # Min 8 chars
    nickname: str
    gender: str  # male | female
    birth_year: int
    height: int
    fitness_level: str
    primary_goal: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserResponse(BaseModel):
    id: str
    email: str
    nickname: str
    fitness_level: str
    primary_goal: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### 3. Frontend Implementation

#### `stores/auth.ts`
```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  nickname: string;
  fitness_level: string;
  primary_goal: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) =>
        set({ user, token, isAuthenticated: true }),
      clearAuth: () =>
        set({ user: null, token: null, isAuthenticated: false }),
    }),
    { name: 'bod-auth' }
  )
);
```

#### `lib/api/auth.ts`
```typescript
import api from '@/lib/api';
import type { User, LoginRequest, RegisterRequest } from '@/types';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authApi = {
  register: async (data: RegisterRequest): Promise<AuthResponse> => {
    const response = await api.post('/api/v1/auth/register', data);
    return response.data;
  },

  login: async (data: LoginRequest): Promise<AuthResponse> => {
    const response = await api.post('/api/v1/auth/login', data);
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/api/v1/auth/logout');
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },
};
```

#### `app/(auth)/login/page.tsx`
```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authApi } from '@/lib/api/auth';
import { useAuthStore } from '@/stores/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await authApi.login({ email, password });
      setAuth(response.user, response.access_token);
      router.push('/');
    } catch (error) {
      console.error('Login failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleSubmit} className="w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Login to Bod</h1>
        <Input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <Button type="submit" disabled={loading} className="w-full">
          {loading ? 'Loading...' : 'Login'}
        </Button>
      </form>
    </div>
  );
}
```

### 4. Middleware

#### Route protection component
```typescript
// components/ProtectedRoute.tsx
'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/v1/auth/register` | Register new user | No |
| POST | `/api/v1/auth/login` | Login user | No |
| GET | `/api/v1/auth/me` | Get current user | Yes |
| POST | `/api/v1/auth/logout` | Logout user | Yes |
| POST | `/api/v1/auth/refresh` | Refresh token | No |
| POST | `/api/v1/auth/reset-password` | Request password reset | No |

## Technical Requirements

- JWT tokens with HS256
- Token expiration: 7 days
- Password hashing with bcrypt
- Email validation
- Password strength validation (min 8 chars)

## Acceptance Criteria

- [ ] User can register with email/password
- [ ] User can login with valid credentials
- [ ] Invalid credentials return 401
- [ ] Protected routes require valid token
- [ ] Token expires after 7 days
- [ ] Logout clears client-side state
- [ ] User persists across page reloads
- [ ] Auto-redirect to login for unauthenticated users

## Security Considerations

- Passwords hashed with bcrypt (cost factor 12)
- JWT signed with secret key from environment
- HTTPS required in production
- CORS restricted to frontend domain
- Rate limiting on auth endpoints
