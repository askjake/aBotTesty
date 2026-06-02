import { NextRequest, NextResponse } from 'next/server';

import { APP_ENV, NODE_ENV } from '@shared/ui/constants/env.constants';

export async function proxy(req: NextRequest) {
  const userEmail =
    APP_ENV === 'local' && NODE_ENV !== 'production'
      ? 'test.test@dish.com'
      : req.headers.get('X-Auth-Request-Email') ||
        req.cookies.get('userEmail')?.value;

  if (!userEmail) {
    return NextResponse.redirect(new URL('/403', req.url));
  }

  const res = NextResponse.next();

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
  matcher: ['/((?!403|404|500|_next/static|_next/image|img|favicon.ico).*)'],
};
