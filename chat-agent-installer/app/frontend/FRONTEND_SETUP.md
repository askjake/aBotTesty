# Frontend Setup Guide

## Environment Configuration

The frontend requires environment variables to connect to the backend API.

### Required Files

1. **apps/chats/.env.local** (for local development)
2. **apps/beta-reports/.env.local** (for local development)

### Environment Variables

```bash
# Backend API URL (where FastAPI is running)
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# Disable Next.js telemetry
NEXT_TELEMETRY_DISABLED=1

# Environment (local, development, or production)
APP_ENV=local

# Frontend URL (where Next.js is running)
NEXT_PUBLIC_ROOT_FRONTEND_URL=http://localhost:3000
```

### Why These Are Needed

- **NEXT_PUBLIC_BACKEND_URL**: The frontend makes API calls to `${NEXT_PUBLIC_BACKEND_URL}/rest/api/v1/*`
- Without this, API calls go to `undefined/rest/api/v1/*` (404 errors)
- **APP_ENV**: Determines which environment configuration to use
- **NEXT_PUBLIC_ROOT_FRONTEND_URL**: Used for inter-app navigation

## Quick Start

1. **Create .env.local files** (if not exist):
   ```bash
   cd apps/chats
   cp .env.example .env.local
   # Edit .env.local and set NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```

2. **Install dependencies**:
   ```bash
   cd ../../  # Back to frontend root
   pnpm install
   ```

3. **Start development server**:
   ```bash
   pnpm dev
   ```

4. **Open browser**:
   ```
   http://localhost:3000
   ```

## Troubleshooting

### "undefined/rest/api/v1/health" 404 Error

**Cause**: Missing or empty `NEXT_PUBLIC_BACKEND_URL` in .env.local

**Fix**:
```bash
echo 'NEXT_PUBLIC_BACKEND_URL=http://localhost:8000' > apps/chats/.env.local
```

### Shared UI Component 404 Error

**Cause**: Monorepo workspace not properly configured

**Fix**:
```bash
# Verify pnpm-workspace.yaml exists at frontend root
# Should contain:
packages:
  - 'apps/*'
  - 'shared/*'

# Reinstall dependencies
pnpm install
```

### CORS Errors

**Cause**: Backend CORS not allowing frontend origin

**Fix**: Backend already configured to allow localhost:3000
- Check backend console for CORS_ALLOWED_ORIGINS
- Should include "http://localhost:3000"

## Project Structure

```
frontend/
├── apps/
│   ├── chats/           - Main chat application
│   │   ├── .env.local   - Local environment config
│   │   └── src/
│   └── beta-reports/    - Beta reports application
│       └── .env.local   - Local environment config
├── shared/
│   └── ui/              - Shared UI components
│       ├── src/
│       │   ├── libs/
│       │   │   └── axios.libs.ts  - Axios instance (uses BACKEND_URL)
│       │   ├── services/
│       │   │   └── health.services.ts  - Health check service
│       │   └── constants/
│       │       └── env.constants.ts  - Environment constants
│       └── ...
├── pnpm-workspace.yaml  - Monorepo configuration
└── package.json
```

## API Configuration Flow

1. Environment variable set in `.env.local`:
   ```
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```

2. Imported in `env.constants.ts`:
   ```typescript
   export const BACKEND_URL = `${process.env.NEXT_PUBLIC_BACKEND_URL}/rest/api/v1`;
   ```

3. Used in `axios.libs.ts`:
   ```typescript
   const axiosLibs = axios.create({
     baseURL: BACKEND_URL,  // http://localhost:8000/rest/api/v1
     withCredentials: true,
   });
   ```

4. API calls in services:
   ```typescript
   await axiosLibs.get('/health');  // → http://localhost:8000/rest/api/v1/health
   ```

## Development Workflow

1. **Start backend first**:
   ```bash
   cd ../backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Start frontend**:
   ```bash
   cd ../frontend
   pnpm dev
   ```

3. **Access application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Created Files (This Fix)

- ✅ `apps/chats/.env.local` - Chat app environment config
- ✅ `apps/beta-reports/.env.local` - Beta reports environment config
- ✅ `FRONTEND_SETUP.md` - This guide

## Next Steps

After pulling these changes:

1. **Verify .env.local files exist**
2. **Restart Next.js dev server** (Ctrl+C and `pnpm dev`)
3. **Check browser console** - Should see successful health check
4. **Test chat functionality** - Create a chat and send a message
