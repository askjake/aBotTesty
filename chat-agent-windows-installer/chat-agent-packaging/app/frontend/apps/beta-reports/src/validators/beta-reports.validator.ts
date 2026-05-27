import { z } from 'zod';

export const feedbackIssueValidator = z
  .object({
    accepted: z.boolean(),
    id: z.string().trim().min(1).max(100),
    comments: z.string().trim().max(250).optional(),
  })
  .strict();

export type FeedbackIssueSchema = z.infer<typeof feedbackIssueValidator>;
