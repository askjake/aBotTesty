import { updateOrCreateChatGroupValidator } from '@/validators/chatsGroups.validators';

describe('updateOrCreateChatGroupValidator', () => {
  describe('valid inputs', () => {
    test('should pass with valid title', () => {
      const validData = { title: 'Valid Chat Group' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe('Valid Chat Group');
      }
    });

    test('should pass with single character title', () => {
      const validData = { title: 'A' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });

    test('should pass with 40 character title', () => {
      const validData = { title: 'A'.repeat(40) };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });

    test('should trim whitespace from title', () => {
      const validData = { title: '  Valid Title  ' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe('Valid Title');
      }
    });
  });

  describe('invalid inputs', () => {
    test('should fail when title is missing', () => {
      const invalidData = {};
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues).toHaveLength(1);
        expect(result.error.issues[0]?.path).toEqual(['title']);
      }
    });

    test('should fail when title is empty string', () => {
      const invalidData = { title: '' };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBe(
          'The "title" field length must has at least 1 symbol',
        );
      }
    });

    test('should fail when title is only whitespace', () => {
      const invalidData = { title: '   ' };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBe(
          'The "title" field length must has at least 1 symbol', // Correct message
        );
      }
    });

    test('should fail when title exceeds 50 characters', () => {
      const invalidData = { title: 'A'.repeat(51) };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.message).toBe(
          'The "title" field length must has max 50 symbol',
        );
      }
    });

    test('should fail when title is not a string', () => {
      const invalidData = { title: 123 };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0]?.code).toBe('invalid_type');
      }
    });

    test('should fail when title is null', () => {
      const invalidData = { title: null };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
    });

    test('should fail when title is undefined', () => {
      const invalidData = { title: undefined };
      const result = updateOrCreateChatGroupValidator.safeParse(invalidData);

      expect(result.success).toBe(false);
    });
  });

  describe('edge cases', () => {
    test('should handle special characters in title', () => {
      const validData = { title: 'Chat-Group_123!@#' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });

    test('should handle unicode characters', () => {
      const validData = { title: 'チャット グループ 🚀' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      expect(result.success).toBe(true);
    });

    test('should accept valid title', () => {
      const validData = {
        title: 'Valid Title', // Use actual content, not just whitespace
      };

      const result = updateOrCreateChatGroupValidator.safeParse(validData);
      expect(result.success).toBe(true);
    });
  });

  describe('type inference', () => {
    test('should have correct TypeScript type', () => {
      // This is more of a compile-time test, but we can verify the structure
      const validData = { title: 'Test' };
      const result = updateOrCreateChatGroupValidator.safeParse(validData);

      if (result.success) {
        // TypeScript should infer this correctly
        const title: string = result.data.title;
        expect(typeof title).toBe('string');
      }
    });
  });
});
