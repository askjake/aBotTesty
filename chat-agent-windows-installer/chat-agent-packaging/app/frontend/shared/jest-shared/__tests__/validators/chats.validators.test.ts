import { updateChatValidator } from '@shared/ui/validators/chats.validators';

describe('updateChatValidator', () => {
  it('validates a chat with a valid title, active, and favorite', () => {
    const validChat = {
      title: 'Valid Chat Title',
      active: true,
      favorite: false,
    };

    const result = updateChatValidator.safeParse(validChat);
    expect(result.success).toBe(true);
    expect(result.data).toEqual({
      ...validChat,
      group_id: null,
    });
  });

  it('validates a chat with a valid title and default values', () => {
    const validChat = {
      title: 'Valid Chat Title',
    };

    const result = updateChatValidator.safeParse(validChat);
    expect(result.success).toBe(true);
    expect(result.data).toEqual({
      title: 'Valid Chat Title',
      active: false,
      favorite: false,
      group_id: null,
    });
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
    expect(result.data).toEqual(validChat);
  });

  it('validates a chat with null group_id', () => {
    const validChat = {
      title: 'Valid Chat Title',
      group_id: null,
    };

    const result = updateChatValidator.safeParse(validChat);
    expect(result.success).toBe(true);
    expect(result.data).toEqual({
      title: 'Valid Chat Title',
      active: false,
      favorite: false,
      group_id: null,
    });
  });

  it('rejects a chat with an empty title', () => {
    const invalidChat = {
      title: '',
      active: true,
      favorite: false,
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'The "title" field length must has at least 1 symbol',
    );
  });

  it('rejects a chat with a title exceeding 50 characters', () => {
    const invalidChat = {
      title: 'a'.repeat(51),
      active: true,
      favorite: false,
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'The "title" field length must has max 50 symbols',
    );
  });

  it('rejects a chat with a title containing only whitespace', () => {
    const invalidChat = {
      title: '   ',
      active: true,
      favorite: false,
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    expect(result?.error?.issues[0]?.message).toBe(
      'The "title" field length must has at least 1 symbol',
    );
  });

  it('trims whitespace from title', () => {
    const chatWithWhitespace = {
      title: '  Valid Chat Title  ',
    };

    const result = updateChatValidator.safeParse(chatWithWhitespace);
    expect(result.success).toBe(true);
    expect(result.data?.title).toBe('Valid Chat Title');
  });

  it('rejects a chat without the title field', () => {
    const invalidChat = {
      active: true,
      favorite: false,
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    if (!result.success) {
      // Zod may return different messages for missing required fields
      expect(result.error.issues[0].message).toMatch(
        /Required|Invalid input: expected string, received undefined/,
      );
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
      // Check for either format to be version-agnostic
      expect(result.error.issues[0].message).toMatch(
        /Expected boolean, received string|Invalid input: expected boolean, received string/,
      );
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
      expect(result.error.issues[0].message).toMatch(
        /Expected boolean, received string|Invalid input: expected boolean, received string/,
      );
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
      expect(result.error.issues[0].message).toMatch(
        /Expected string, received number|Invalid input: expected string, received number/,
      );
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
      expect(result.error.issues[0].message).toMatch(
        /Expected string, received number|Invalid input: expected string, received number/,
      );
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
    expect(result.data).toEqual({
      ...validChat,
      group_id: null,
    });
  });

  it('accepts a chat title at maximum length (50 characters)', () => {
    const validChat = {
      title: 'a'.repeat(50),
    };

    const result = updateChatValidator.safeParse(validChat);
    expect(result.success).toBe(true);
    expect(result.data?.title).toBe('a'.repeat(50));
  });

  it('accepts a chat title at minimum length (1 character)', () => {
    const validChat = {
      title: 'a',
    };

    const result = updateChatValidator.safeParse(validChat);
    expect(result.success).toBe(true);
    expect(result.data?.title).toBe('a');
  });

  it('rejects extra fields due to strict mode', () => {
    const invalidChat = {
      title: 'Valid Chat Title',
      extraField: 'not allowed',
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0].code).toBe('unrecognized_keys');
    }
  });

  it('handles multiple validation errors', () => {
    const invalidChat = {
      title: '',
      active: 'not-boolean',
      favorite: 123,
    };

    const result = updateChatValidator.safeParse(invalidChat);
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.length).toBeGreaterThan(0);
    }
  });
});
