import {
  FeedbackIssueSchema,
  feedbackIssueValidator,
} from '@/validators/beta-reports.validator';

describe('feedbackIssueValidator', () => {
  describe('Valid Input', () => {
    it('should validate a valid feedback issue with all fields', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'This is a valid comment',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validInput);
      }
    });

    it('should validate when comments field is omitted', () => {
      const validInput = {
        accepted: false,
        id: 'ISSUE-456',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validInput);
      }
    });

    it('should validate when comments is an empty string', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-789',
        comments: '',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should validate with accepted as false', () => {
      const validInput = {
        accepted: false,
        id: 'ISSUE-001',
        comments: 'Rejected issue',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should validate id at minimum length (1 character)', () => {
      const validInput = {
        accepted: true,
        id: 'A',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should validate id at maximum length (100 characters)', () => {
      const validInput = {
        accepted: true,
        id: 'A'.repeat(100),
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should validate comments at maximum length (250 characters)', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'A'.repeat(250),
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should trim whitespace from id', () => {
      const validInput = {
        accepted: true,
        id: '  ISSUE-123  ',
        comments: 'Test comment',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.id).toBe('ISSUE-123');
      }
    });

    it('should trim whitespace from comments', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: '  Test comment  ',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.comments).toBe('Test comment');
      }
    });
  });

  describe('Invalid Input - Missing Required Fields', () => {
    it('should fail when accepted field is missing', () => {
      const invalidInput = {
        id: 'ISSUE-123',
        comments: 'Test comment',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues).toHaveLength(1);
        expect(result.error.issues[0].path).toEqual(['accepted']);
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('should fail when id field is missing', () => {
      const invalidInput = {
        accepted: true,
        comments: 'Test comment',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues).toHaveLength(1);
        expect(result.error.issues[0].path).toEqual(['id']);
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('should fail when all required fields are missing', () => {
      const invalidInput = {};

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.length).toBeGreaterThanOrEqual(2);
      }
    });
  });

  describe('Invalid Input - Wrong Types', () => {
    it('should fail when accepted is not a boolean', () => {
      const invalidInput = {
        accepted: 'true',
        id: 'ISSUE-123',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['accepted']);
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].message).toContain('boolean');
      }
    });

    it('should fail when id is not a string', () => {
      const invalidInput = {
        accepted: true,
        id: 123,
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['id']);
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('should fail when comments is not a string', () => {
      const invalidInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 123,
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['comments']);
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('should fail when accepted is null', () => {
      const invalidInput = {
        accepted: null,
        id: 'ISSUE-123',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
    });
  });

  describe('Invalid Input - String Length Constraints', () => {
    it('should fail when id is empty string after trim', () => {
      const invalidInput = {
        accepted: true,
        id: '   ',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['id']);
        expect(result.error.issues[0].code).toBe('too_small');
      }
    });

    it('should fail when id is empty string', () => {
      const invalidInput = {
        accepted: true,
        id: '',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['id']);
        expect(result.error.issues[0].code).toBe('too_small');
      }
    });

    it('should fail when id exceeds 100 characters', () => {
      const invalidInput = {
        accepted: true,
        id: 'A'.repeat(101),
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['id']);
        expect(result.error.issues[0].code).toBe('too_big');
      }
    });

    it('should fail when comments exceeds 250 characters', () => {
      const invalidInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'A'.repeat(251),
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].path).toEqual(['comments']);
        expect(result.error.issues[0].code).toBe('too_big');
      }
    });

    it('should fail when id is only whitespace', () => {
      const invalidInput = {
        accepted: true,
        id: '     ',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
    });
  });

  describe('Invalid Input - Strict Mode (Extra Fields)', () => {
    it('should fail when extra fields are present', () => {
      const invalidInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Test comment',
        extraField: 'This should not be here',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
        expect(result.error.issues[0].message).toContain('extraField');
      }
    });

    it('should fail when multiple extra fields are present', () => {
      const invalidInput = {
        accepted: true,
        id: 'ISSUE-123',
        extraField1: 'Extra 1',
        extraField2: 'Extra 2',
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
      }
    });
  });

  describe('Edge Cases', () => {
    it('should fail when input is null', () => {
      const result = feedbackIssueValidator.safeParse(null);

      expect(result.success).toBe(false);
    });

    it('should fail when input is undefined', () => {
      const result = feedbackIssueValidator.safeParse(undefined);

      expect(result.success).toBe(false);
    });

    it('should fail when input is an array', () => {
      const result = feedbackIssueValidator.safeParse([]);

      expect(result.success).toBe(false);
    });

    it('should fail when input is a string', () => {
      const result = feedbackIssueValidator.safeParse('invalid');

      expect(result.success).toBe(false);
    });

    it('should handle special characters in id', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123_ABC@#$',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should handle special characters in comments', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Comment with special chars: @#$%^&*()',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should handle unicode characters in comments', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Comment with unicode: 你好 🎉 café',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });

    it('should handle newlines in comments', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Line 1\nLine 2\nLine 3',
      };

      const result = feedbackIssueValidator.safeParse(validInput);

      expect(result.success).toBe(true);
    });
  });

  describe('TypeScript Type Inference', () => {
    it('should correctly infer the FeedbackIssueSchema type', () => {
      const validData: FeedbackIssueSchema = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Test comment',
      };

      const result = feedbackIssueValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });

    it('should allow optional comments in type', () => {
      const validData: FeedbackIssueSchema = {
        accepted: true,
        id: 'ISSUE-123',
      };

      const result = feedbackIssueValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });
  });

  describe('Parse vs SafeParse', () => {
    it('should throw error when using parse with invalid data', () => {
      const invalidInput = {
        accepted: 'not a boolean',
        id: 'ISSUE-123',
      };

      expect(() => {
        feedbackIssueValidator.parse(invalidInput);
      }).toThrow();
    });

    it('should not throw error when using safeParse with invalid data', () => {
      const invalidInput = {
        accepted: 'not a boolean',
        id: 'ISSUE-123',
      };

      expect(() => {
        feedbackIssueValidator.safeParse(invalidInput);
      }).not.toThrow();
    });

    it('should return parsed data when using parse with valid data', () => {
      const validInput = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Test comment',
      };

      const result = feedbackIssueValidator.parse(validInput);

      expect(result).toEqual(validInput);
    });
  });

  describe('Multiple Validation Errors', () => {
    it('should return multiple errors when multiple fields are invalid', () => {
      const invalidInput = {
        accepted: 'not a boolean',
        id: '',
        comments: 'A'.repeat(251),
      };

      const result = feedbackIssueValidator.safeParse(invalidInput);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues.length).toBeGreaterThanOrEqual(2);
      }
    });
  });
});
