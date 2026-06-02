import { z } from 'zod';

export const updateOrCreateChatGroupValidator = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, {
        message: 'The "title" field length must has at least 1 symbol',
      })
      .max(50, { message: 'The "title" field length must has max 50 symbol' }),
  })
  .strict();

export type UpdateOrCreateChatGroupSchema = z.infer<
  typeof updateOrCreateChatGroupValidator
>;
