import {
  updateMessageValidator,
  createMessageVersionValidator,
  changeMessageVersionValidator,
} from '@shared/ui/validators/messages.validators';

describe('Message Validators', () => {
  describe('updateMessageValidator', () => {
    describe('should accept valid data', () => {
      it('accepts complete valid message', () => {
        const input = {
          content: 'Hello world',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: '550e8400-e29b-41d4-a716-446655440000',
              filename: 'document.pdf',
              media_type: 'application/pdf',
              owner_id: 'user-001',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts message with reasoning enabled', () => {
        const input = {
          content: 'Test message',
          message_config: {
            reasoning: true,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts message with empty attachments array', () => {
        const input = {
          content: 'Message without attachments',
          message_config: {
            reasoning: false,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts message with multiple attachments', () => {
        const input = {
          content: 'Message with files',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: '550e8400-e29b-41d4-a716-446655440000',
              filename: 'file1.pdf',
              media_type: 'application/pdf',
              owner_id: 'user-001',
            },
            {
              attachment_id: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
              filename: 'file2.jpg',
              media_type: 'image/jpeg',
              owner_id: 'user-002',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('trims whitespace from content', () => {
        const input = {
          content: '  Hello world  ',
          message_config: {
            reasoning: false,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.content).toBe('Hello world');
        }
      });

      it('applies default reasoning value when not provided', () => {
        const input = {
          content: 'Test',
          message_config: {},
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.message_config.reasoning).toBe(false);
        }
      });
    });

    describe('should reject invalid data', () => {
      it('rejects empty content', () => {
        const input = {
          content: '',
          message_config: {
            reasoning: false,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects whitespace-only content', () => {
        const input = {
          content: '   ',
          message_config: {
            reasoning: false,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects missing content field', () => {
        const input = {
          message_config: {
            reasoning: false,
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects missing message_config field', () => {
        const input = {
          content: 'Hello',
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects missing attachments field', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects invalid uuid in attachment_id', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: 'not-a-uuid',
              filename: 'file.pdf',
              media_type: 'application/pdf',
              owner_id: 'user-001',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects empty filename in attachment', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: '550e8400-e29b-41d4-a716-446655440000',
              filename: '',
              media_type: 'application/pdf',
              owner_id: 'user-001',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects empty media_type in attachment', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: '550e8400-e29b-41d4-a716-446655440000',
              filename: 'file.pdf',
              media_type: '',
              owner_id: 'user-001',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects empty owner_id in attachment', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
          attachments: [
            {
              attachment_id: '550e8400-e29b-41d4-a716-446655440000',
              filename: 'file.pdf',
              media_type: 'application/pdf',
              owner_id: '',
            },
          ],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects non-boolean reasoning value', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: 'true',
          },
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects non-object message_config', () => {
        const input = {
          content: 'Hello',
          message_config: 'invalid',
          attachments: [],
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects extra fields due to strict mode', () => {
        const input = {
          content: 'Hello',
          message_config: {
            reasoning: false,
          },
          attachments: [],
          extraField: 'not allowed',
        };

        const result = updateMessageValidator.safeParse(input);

        expect(result.success).toBe(false);
      });
    });
  });

  describe('createMessageVersionValidator', () => {
    describe('should accept valid data', () => {
      it('accepts valid content', () => {
        const input = {
          content: 'New version content',
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('trims whitespace from content', () => {
        const input = {
          content: '  New version  ',
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
        if (result.success) {
          expect(result.data.content).toBe('New version');
        }
      });

      it('accepts long content', () => {
        const input = {
          content: 'A'.repeat(10000),
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });
    });

    describe('should reject invalid data', () => {
      it('rejects empty content', () => {
        const input = {
          content: '',
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects whitespace-only content', () => {
        const input = {
          content: '   ',
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects missing content field', () => {
        const input = {};

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects non-string content', () => {
        const input = {
          content: 12345,
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects null content', () => {
        const input = {
          content: null,
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects extra fields due to strict mode', () => {
        const input = {
          content: 'Valid content',
          extraField: 'not allowed',
        };

        const result = createMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });
    });
  });

  describe('changeMessageVersionValidator', () => {
    describe('should accept valid data', () => {
      it('accepts version_index of 0', () => {
        const input = {
          version_index: 0,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts positive version_index', () => {
        const input = {
          version_index: 5,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts large version_index', () => {
        const input = {
          version_index: 999999,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });

      it('accepts decimal version_index', () => {
        const input = {
          version_index: 2.5,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(true);
      });
    });

    describe('should reject invalid data', () => {
      it('rejects negative version_index', () => {
        const input = {
          version_index: -1,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects negative decimal version_index', () => {
        const input = {
          version_index: -0.5,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects missing version_index field', () => {
        const input = {};

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects string version_index', () => {
        const input = {
          version_index: '5',
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects null version_index', () => {
        const input = {
          version_index: null,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects boolean version_index', () => {
        const input = {
          version_index: true,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects NaN version_index', () => {
        const input = {
          version_index: NaN,
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });

      it('rejects extra fields due to strict mode', () => {
        const input = {
          version_index: 1,
          extraField: 'not allowed',
        };

        const result = changeMessageVersionValidator.safeParse(input);

        expect(result.success).toBe(false);
      });
    });
  });
});
