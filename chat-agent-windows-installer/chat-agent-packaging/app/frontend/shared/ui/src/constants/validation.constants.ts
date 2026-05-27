export const MAX_FILE_SIZE = 20 * 1024 * 1024;

export const ALLOWED_IMAGES_MIME_TYPES = {
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/png': ['.png'],
  'image/gif': ['.gif'],
  'image/webp': ['.webp'],
} as const;

export const ALLOWED_DOCUMENTS_MIME_TYPES = {
  'text/plain': ['.txt'],
  'application/pdf': ['.pdf'],
  'application/msword': ['.doc'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
    '.docx',
  ],
} as const;

export const ALLOWED_FILES_MIME_TYPES = [
  ...Object.values(ALLOWED_IMAGES_MIME_TYPES).flat(),
  ...Object.values(ALLOWED_DOCUMENTS_MIME_TYPES).flat(),
] as const;

export const ALLOWED_FILES_MIME_TYPES_STRING =
  ALLOWED_FILES_MIME_TYPES.join(',');

export const MAX_IMAGE_COUNT = 20;

export const MAX_DOCUMENT_COUNT = 20;

export const ALLOWED_SPECIAL_CHARS = '!"#$%&\'()*+,-./:;<=>?@[]^_`{|}~';

export const MAX_CHATS = 200;

export const MAX_CHATS_GROUPS = 20;
