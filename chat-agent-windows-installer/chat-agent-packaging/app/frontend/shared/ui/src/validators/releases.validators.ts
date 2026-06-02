import { z } from 'zod';

export const updateLastReleaseDateValidator = z
  .object({
    date: z.date(),
  })
  .strict();

export type UpdateLastReleaseDateSchema = z.infer<
  typeof updateLastReleaseDateValidator
>;
