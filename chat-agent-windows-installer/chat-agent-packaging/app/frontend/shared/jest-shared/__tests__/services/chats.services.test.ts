import { updateChatValidator } from '@shared/ui/validators/chats.validators';

describe('updateChatValidator', () => {
  describe('Valid inputs', () => {
    it('validates a chat with a valid title, active, and favorite', () => {
      const validChat = {
        title: 'Valid Chat Title',
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({
          ...validChat,
          group_id: null,
        });
      }
    });

    it('validates a chat with a valid title and default values', () => {
      const validChat = {
        title: 'Valid Chat Title',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({
          title: 'Valid Chat Title',
          active: false,
          favorite: false,
          group_id: null,
        });
      }
    });

    it('validates a chat with all fields including group_id', () => {
      const validChat = {
        title: 'Valid Chat Title',
        active: true,
        favorite: true,
        group_id: 'group-123',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual(validChat);
      }
    });

    it('validates a chat with null group_id', () => {
      const validChat = {
        title: 'Valid Chat Title',
        group_id: null,
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({
          title: 'Valid Chat Title',
          active: false,
          favorite: false,
          group_id: null,
        });
      }
    });

    it('trims whitespace from title', () => {
      const chatWithWhitespace = {
        title: '  Valid Chat Title  ',
      };

      const result = updateChatValidator.safeParse(chatWithWhitespace);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe('Valid Chat Title');
      }
    });

    it('accepts a chat title with special characters', () => {
      const validChat = {
        title: '!@#$%^&*()',
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({
          ...validChat,
          group_id: null,
        });
      }
    });

    it('accepts a chat title at maximum length (50 characters)', () => {
      const validChat = {
        title: 'a'.repeat(50),
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe('a'.repeat(50));
      }
    });

    it('accepts a chat title at minimum length (1 character)', () => {
      const validChat = {
        title: 'a',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.title).toBe('a');
      }
    });

    it('validates empty group_id string', () => {
      const validChat = {
        title: 'Valid Chat Title',
        group_id: '',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.group_id).toBe('');
      }
    });

    it('validates group_id with special characters', () => {
      const validChat = {
        title: 'Valid Chat Title',
        group_id: 'group-123_test!@#',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.group_id).toBe('group-123_test!@#');
      }
    });

    it('validates with all boolean combinations', () => {
      const testCases = [
        { active: true, favorite: true },
        { active: true, favorite: false },
        { active: false, favorite: true },
        { active: false, favorite: false },
      ];

      testCases.forEach(({ active, favorite }) => {
        const validChat = {
          title: 'Valid Chat Title',
          active,
          favorite,
        };

        const result = updateChatValidator.safeParse(validChat);
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data).toEqual({
            ...validChat,
            group_id: null,
          });
        }
      });
    });

    it('handles complex whitespace trimming scenarios', () => {
      const testCases = [
        { input: '\t\nValid Chat Title\t\n', expected: 'Valid Chat Title' },
        {
          input: '   Valid   Chat   Title   ',
          expected: 'Valid   Chat   Title',
        },
        { input: '\r\nTest\r\n', expected: 'Test' },
      ];

      testCases.forEach(({ input, expected }) => {
        const validChat = {
          title: input,
        };

        const result = updateChatValidator.safeParse(validChat);
        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.title).toBe(expected);
        }
      });
    });
  });

  describe('Invalid inputs', () => {
    it('rejects a chat with an empty title', () => {
      const invalidChat = {
        title: '',
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe(
          'The "title" field length must has at least 1 symbol',
        );
      }
    });

    it('rejects a chat with a title exceeding 50 characters', () => {
      const invalidChat = {
        title: 'a'.repeat(51),
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe(
          'The "title" field length must has max 50 symbols',
        );
      }
    });

    it('rejects a chat with a title containing only whitespace', () => {
      const invalidChat = {
        title: '   ',
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].message).toBe(
          'The "title" field length must has at least 1 symbol',
        );
      }
    });

    it('rejects a chat without the title field', () => {
      const invalidChat = {
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['title']);
      }
    });

    it('rejects a chat with an invalid active field', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        active: 'true',
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['active']);
      }
    });

    it('rejects a chat with an invalid favorite field', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        active: true,
        favorite: 'false',
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['favorite']);
      }
    });

    it('rejects a chat with an invalid title field type', () => {
      const invalidChat = {
        title: 123,
        active: true,
        favorite: false,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['title']);
      }
    });

    it('rejects a chat with an invalid group_id field type', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        group_id: 123,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['group_id']);
      }
    });

    it('handles boolean-like strings correctly (should fail)', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        active: 'false',
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
      }
    });

    it('handles null values for non-nullable fields', () => {
      const invalidChat = {
        title: null,
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('invalid_type');
        expect(result.error.issues[0].path).toEqual(['title']);
      }
    });
  });

  describe('Strict mode', () => {
    it('rejects additional unknown fields', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        active: true,
        favorite: false,
        unknownField: 'this will cause rejection',
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
      }
    });

    it('rejects multiple unknown fields', () => {
      const invalidChat = {
        title: 'Valid Chat Title',
        unknownField1: 'ignored',
        unknownField2: 123,
        unknownField3: { nested: 'object' },
      };

      const result = updateChatValidator.safeParse(invalidChat);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error.issues[0].code).toBe('unrecognized_keys');
      }
    });
  });

  describe('Default values', () => {
    it('validates with only required field', () => {
      const validChat = {
        title: 'Only Title',
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data).toEqual({
          title: 'Only Title',
          active: false,
          favorite: false,
          group_id: null,
        });
      }
    });

    it('handles undefined group_id (should default to null)', () => {
      const validChat = {
        title: 'Valid Chat Title',
        group_id: undefined,
      };

      const result = updateChatValidator.safeParse(validChat);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.group_id).toBe(null);
      }
    });
  });
});
