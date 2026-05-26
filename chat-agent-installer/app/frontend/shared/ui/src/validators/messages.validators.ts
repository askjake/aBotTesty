import { z } from 'zod';

export const updateMessageValidator = z
  .object({
    message_config: z.object({
      reasoning: z.boolean().default(false),
    }),
    content: z.string().trim().min(1, {
      message: 'The "content" field length must has at least 1 symbol',
    }),
    attachments: z.array(
      z.object({
        attachment_id: z.string().uuid().nonempty(),
        filename: z.string().min(1),
        media_type: z.string().min(1),
        owner_id: z.string().min(1),
      }),
    ),
  })
  .strict();

export const createMessageVersionValidator = z
  .object({
    content: z.string().trim().min(1, {
      message: 'The "content" field length must has at least 1 symbol',
    }),
  })
  .strict();

export const changeMessageVersionValidator = z
  .object({
    version_index: z.number().min(0, {
      message: 'The "version_index" field  must has be at least 1',
    }),
  })
  .strict();

export type UpdateMessageSchema = z.infer<typeof updateMessageValidator>;

export type CreateMessageVersionSchema = z.infer<
  typeof createMessageVersionValidator
>;

export type ChangeMessageVersionSchema = z.infer<
  typeof changeMessageVersionValidator
>;
