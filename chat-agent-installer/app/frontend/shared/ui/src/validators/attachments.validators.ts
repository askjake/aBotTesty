import { z } from 'zod';

import {
  ALLOWED_DOCUMENTS_MIME_TYPES,
  ALLOWED_IMAGES_MIME_TYPES,
  MAX_DOCUMENT_COUNT,
  MAX_FILE_SIZE,
  MAX_IMAGE_COUNT,
} from '@shared/ui/constants/validation.constants';
import { categorizeFiles } from '@shared/ui/utils/validation.utils';
import { isServer } from '@shared/ui/constants/common.constants';

export const checkAttachmentValidator = z.object({
  attachment: z
    .instanceof(File)
    .refine(
      (file) => {
        const allowedTypes: {
          [key: string]: boolean;
        } = {
          ...Object.keys(ALLOWED_IMAGES_MIME_TYPES).reduce(
            (acc, type) => ({ ...acc, [type]: true }),
            {},
          ),
          ...Object.keys(ALLOWED_DOCUMENTS_MIME_TYPES).reduce(
            (acc, type) => ({ ...acc, [type]: true }),
            {},
          ),
        };
        return allowedTypes[file.type];
      },
      {
        message:
          'Invalid file type. Allowed types: JPG, JPEG, PNG, GIF, WEBP, TXT, PDF, DOC, DOCX',
      },
    )
    .refine((file) => file.size <= MAX_FILE_SIZE, {
      message: `File size should not exceed ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
    }),
});

const validateFiles = (files: File[]) => {
  const { images, documents } = categorizeFiles(files);
  const allowedTypes = {
    ...ALLOWED_IMAGES_MIME_TYPES,
    ...ALLOWED_DOCUMENTS_MIME_TYPES,
  };

  const validations = [
    {
      condition: images.length > MAX_IMAGE_COUNT,
      error: {
        type: 'image_count',
        message: `Maximum ${MAX_IMAGE_COUNT} images allowed`,
        details: {
          current: images.length,
          maximum: MAX_IMAGE_COUNT,
          files: images.map((f) => ({ name: f.name, type: f.type })),
        },
      },
    },
    {
      condition: documents.length > MAX_DOCUMENT_COUNT,
      error: {
        type: 'document_count',
        message: `Maximum ${MAX_DOCUMENT_COUNT} documents allowed`,
        details: {
          current: documents.length,
          maximum: MAX_DOCUMENT_COUNT,
          files: documents.map((f) => ({ name: f.name, type: f.type })),
        },
      },
    },
    {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      condition: files.some((file) => !allowedTypes[file.type]),
      error: {
        type: 'invalid_type',
        message:
          'Invalid file type. Allowed types: JPG, JPEG, PNG, GIF, WEBP, TXT, PDF, DOC, DOCX',
        details: {
          files: files
            // eslint-disable-next-line @typescript-eslint/ban-ts-comment
            // @ts-expect-error
            .filter((file) => !allowedTypes[file.type])
            .map((f) => ({ name: f.name, type: f.type })),
        },
      },
    },
    {
      condition: files.some((file) => file.size > MAX_FILE_SIZE),
      error: {
        type: 'invalid_size',
        message: `File size should not exceed ${MAX_FILE_SIZE / (1024 * 1024)}MB`,
        details: {
          files: files
            .filter((file) => file.size > MAX_FILE_SIZE)
            .map((f) => ({ name: f.name, type: f.type, size: f.size })),
        },
      },
    },
  ];

  const failedValidation = validations.find((v) => v.condition);
  return failedValidation
    ? { isValid: false, error: failedValidation.error }
    : { isValid: true };
};

export const uploadAttachmentsValidator = z.object({
  attachments: isServer
    ? z.any()
    : z
        .instanceof(FileList)
        .refine((list) => list.length > 0, 'At least one file is required')
        .transform((list) => Array.from(list))
        .refine(
          (files) => validateFiles(files).isValid,
          // @ts-ignore
          (files) => ({ message: JSON.stringify(validateFiles(files).error) }),
        ),
});

export type UpdateAttachmentsSchema = z.infer<
  typeof uploadAttachmentsValidator
>;
