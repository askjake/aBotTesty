import { z } from 'zod';

export const updateChatValidator = z
  .object({
    title: z
      .string()
      .trim()
      .min(1, {
        message: 'The "title" field length must has at least 1 symbol',
      })
      .max(50, { message: 'The "title" field length must has max 50 symbols' }),
    active: z.boolean().default(false),
    favorite: z.boolean().default(false),
    group_id: z.string().nullable().default(null),
  })
  .strict();

export const chatsUsageByRangeValidator = z.object({
  start_date: z.date(),
  end_date: z.date(),
});

export type UpdateChatSchema = z.infer<typeof updateChatValidator>;

export type ChatsUsageByRangeValidator = z.infer<
  typeof chatsUsageByRangeValidator
>;
