import { z } from 'zod';
import { ALLOWED_SPECIAL_CHARS } from '@shared/ui/constants/validation.constants';

export const passwordSchema = z
  .string()
  .min(8, 'Passphrase must be at least 8 characters long')
  .max(32, 'Passphrase must not exceed 32 characters')
  .regex(
    new RegExp(
      `^[a-zA-Z0-9${ALLOWED_SPECIAL_CHARS.replace(/[-\]\\]/g, '\\$&')}]+$`,
    ),
    'Passphrase contains invalid characters',
  )
  .regex(/[a-z]/, 'Passphrase must contain at least one lowercase letter')
  .regex(/[A-Z]/, 'Passphrase must contain at least one uppercase letter')
  .regex(/[0-9]/, 'Passphrase must contain at least one number')
  .regex(
    new RegExp(`[${ALLOWED_SPECIAL_CHARS.replace(/[-\]\\]/g, '\\$&')}]`),
    'Passphrase must contain at least one special character',
  );

export const setupVaultValidator = z
  .object({
    password: passwordSchema,
  })
  .required();

export const updateVaultPasswordValidator = z
  .object({
    oldPassword: passwordSchema,
    newPassword: passwordSchema,
  })
  .required()
  .refine((data) => data.oldPassword !== data.newPassword, {
    message: 'New password must be different from current password',
    path: ['newPassword'],
  });

export type SetupVaultSchema = z.infer<typeof setupVaultValidator>;

export type UpdateVaultPasswordSchema = z.infer<
  typeof updateVaultPasswordValidator
>;
