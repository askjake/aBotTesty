// apps/chats/middleware.ts
import { NextRequest, NextResponse } from 'next/server';

import { APP_ENV, NODE_ENV } from '@shared/ui/constants/env.constants';

export function middleware(req: NextRequest) {
  const headers = new Headers(req.headers);

  // Determine user email from various sources
  const userEmail =
    APP_ENV === 'local' && NODE_ENV !== 'production'
      ? 'test.test@dish.com' // Local development default
      : req.headers.get('X-Auth-Request-Email') || // From auth proxy
        req.headers.get('x-auth-request-email') || // Lowercase variant
        req.cookies.get('userEmail')?.value || // From existing cookie
        'agent.user@dish.com'; // Fallback default

  // Set the header for downstream services
  headers.set('x-auth-request-email', userEmail);

  const res = NextResponse.next({
    request: { headers },
  });

  // Set cookie for persistence
  res.cookies.set({
    name: 'userEmail',
    value: userEmail,
    httpOnly: true,
    path: '/',
    secure: APP_ENV !== 'local',
    sameSite: 'lax',
  });

  return res;
}

export const config = {
  // Exclude static assets, images, and error pages
  matcher: ['/((?!403|404|500|_next/static|_next/image|img|favicon.ico).*)'],
};

