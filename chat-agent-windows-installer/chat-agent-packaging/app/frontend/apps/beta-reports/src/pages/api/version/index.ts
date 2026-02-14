import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== 'GET') {
    return res.status(400).json({ error: 'This method is not allowed' });
  }
  res.status(200).json({ version: process.env.NEXT_PUBLIC_APP_VERSION });
}
