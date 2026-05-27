import { NextApiRequest, NextApiResponse } from 'next';

import {
  createSignedToken,
  verifySignedToken,
} from '@shared/ui/utils/validation.utils';
import { APP_ENV } from '@shared/ui/constants/env.constants';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  const userEmail = req.cookies['userEmail'] || '';

  if (req.method === 'POST') {
    const { password } = req.body;

    if (!password) {
      return res.status(400).json({ description: 'Password is required' });
    }

    if (password !== process.env.BETA_REPORTS_PASSWORD) {
      return res.status(401).json({ description: 'Password does not match' });
    }

    try {
      const token = createSignedToken({
        secret: process.env.BETA_REPORTS_SECRET_KEY as string,
        data: {
          email: userEmail,
          createdAt: new Date().getTime(),
        },
      });

      // Build cookie string manually
      const cookieOptions = [
        `beta_reports_token=${token}`,
        'Path=/',
        'HttpOnly',
        APP_ENV !== 'local' ? 'Secure' : '',
        'SameSite=Lax',
        `Max-Age=${60 * 60 * 24 * 30}`, // 30 days
      ]
        .filter(Boolean)
        .join('; ');

      res.setHeader('Set-Cookie', cookieOptions);
      return res.status(200).json({ ok: true });
    } catch (error) {
      console.error('Error in signed in to the beta reports page:', error);
      return res.status(500).json({ description: 'Internal server error' });
    }
  } else if (req.method === 'GET') {
    const token = req.cookies['beta_reports_token'] || '';

    if (!token) {
      return res
        .status(200)
        .json({ description: 'Token is required', valid: false });
    }

    if (
      !verifySignedToken({
        secret: process.env.BETA_REPORTS_SECRET_KEY as string,
        token,
      })
    ) {
      return res
        .status(200)
        .json({ description: 'Token is not correct', valid: false });
    }

    return res.status(200).json({ valid: true });
  } else {
    return res.status(400).json({ description: 'This method is not allowed' });
  }
}
