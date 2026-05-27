import { NextApiRequest, NextApiResponse } from 'next';
import axiosLibs from '@shared/ui/libs/axios.libs';
import axios from 'axios';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  const { id } = req.query;

  if (req.method !== 'GET') {
    return res.status(400).json({ error: 'This method is not allowed' });
  }

  if (!id || typeof id !== 'string') {
    return res.status(400).json({ error: 'ID parameter is required' });
  }

  try {
    const userEmail = req.cookies['userEmail'] || '';
    const headers = req.headers;
    const response = await axiosLibs.get(`/attachments/${id}`, {
      responseType: 'stream',
      timeout: 30000,
      headers: {
        ...headers,
        'X-Auth-Request-Email': userEmail,
      },
    });

    const contentType = response.headers['content-type'] || 'image/jpeg';
    const contentLength = response.headers['content-length'];

    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'public, max-age=3600');

    if (contentLength) {
      res.setHeader('Content-Length', contentLength);
    }

    response.data.pipe(res);
  } catch (error) {
    console.error('Error fetching image from backend:', error);

    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500;
      const message =
        error.response?.data?.message || 'Failed to fetch image from backend';
      return res.status(status).json({ error: message });
    }

    res.status(500).json({ error: 'Internal server error' });
  }
}
