import crypto from 'crypto';
import {
  ALLOWED_DOCUMENTS_MIME_TYPES,
  ALLOWED_IMAGES_MIME_TYPES,
} from '@shared/ui/constants/validation.constants';

export const isImageType = (mimeType: string) =>
  mimeType in ALLOWED_IMAGES_MIME_TYPES;

export const isDocumentType = (mimeType: string) =>
  mimeType in ALLOWED_DOCUMENTS_MIME_TYPES;

export const categorizeFiles = (files: File[]) => {
  return files.reduce(
    (acc, file) => {
      if (isImageType(file.type)) {
        acc.images.push(file);
      } else if (isDocumentType(file.type)) {
        acc.documents.push(file);
      }
      return acc;
    },
    { images: [] as File[], documents: [] as File[] },
  );
};

export const createSignedToken = ({
  secret,
  data,
}: {
  secret: string;
  data: { [key: string]: any };
}) => {
  const payload = JSON.stringify(data);
  const signature = crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('hex');
  return Buffer.from(JSON.stringify({ payload, sig: signature })).toString(
    'base64',
  );
};

export const verifySignedToken = ({
  token,
  secret,
}: {
  token: string;
  secret: string;
}) => {
  try {
    const decoded = JSON.parse(Buffer.from(token, 'base64').toString());
    const { payload, sig } = decoded;
    const expectedSig = crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex');
    if (expectedSig !== sig) return null;
    return JSON.parse(payload);
  } catch (e) {
    return null;
  }
};
