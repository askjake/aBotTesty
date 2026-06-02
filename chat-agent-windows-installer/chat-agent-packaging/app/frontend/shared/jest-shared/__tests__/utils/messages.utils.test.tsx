import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { TextAreaRef } from 'antd/es/input/TextArea';

import {
  renderUserInputInMessage,
  renderUserMessage,
  renderAttachmentMessages,
  renderAIMessage,
  transformToMessages,
  transformMessagesToObject,
} from '@shared/ui/utils/messages.utils';
import { AttachmentStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { BACKEND_URL } from '@shared/ui/constants/env.constants';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Mock nanoid to return predictable IDs for testing
jest.mock('nanoid', () => ({
  nanoid: jest.fn(() => 'test-id'),
}));

// Mock ALLOWED_IMAGES_MIME_TYPES constant
jest.mock('@shared/ui/constants/validation.constants', () => ({
  ALLOWED_IMAGES_MIME_TYPES: {
    'image/jpeg': true,
    'image/png': true,
    'image/gif': true,
    'image/webp': true,
  },
}));

describe('Message Utilities', () => {
  describe('renderUserInputInMessage', () => {
    it('should render text area when edit is true', () => {
      const refInput = createRef<TextAreaRef>();
      render(
        renderUserInputInMessage({
          content: 'Test content',
          refInput,
          edit: true,
        }),
      );

      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
      expect(textarea).toHaveValue('Test content');
    });

    it('should render plain text when edit is false', () => {
      const refInput = createRef<TextAreaRef>();
      const { container } = render(
        renderUserInputInMessage({
          content: 'Test content',
          refInput,
          edit: false,
        }),
      );

      expect(container).toHaveTextContent('Test content');
      expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    });

    it('should configure TextArea with correct autoSize props', () => {
      const refInput = createRef<TextAreaRef>();
      render(
        renderUserInputInMessage({
          content: 'Test content',
          refInput,
          edit: true,
        }),
      );

      const textarea = screen.getByRole('textbox');
      expect(textarea).toBeInTheDocument();
    });
  });

  describe('renderUserMessage', () => {
    it('should return a properly formatted user message object', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const result = renderUserMessage({
        key: 'msg-1',
        role: 'user',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello world',
          },
        },
        version_count: 2,
        version_index: 1,
        edit: true,
        refInput,
        onChangeVersion,
        onToggleEdit,
        onSaveEdit,
        onCancelEdit,
        showEditBtn: true,
        readyOnlyChat: false,
      });

      expect(result).toEqual({
        key: 'msg-1',
        role: RoleEnum.USER,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello world',
          },
        },
        version_count: 2,
        version_index: 1,
        edit: true,
        refInput,
        onChangeVersion,
        onToggleEdit,
        onSaveEdit,
        onCancelEdit,
        showEditBtn: true,
        readyOnlyChat: false,
      });
    });

    it('should handle default values correctly', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const result = renderUserMessage({
        key: 'msg-1',
        role: 'user',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello world',
          },
        },
        version_count: 1,
        version_index: 0,
        refInput,
        onChangeVersion,
        onToggleEdit,
        onSaveEdit,
        onCancelEdit,
        showEditBtn: false,
      });

      expect(result.edit).toBe(false);
      expect(result.readyOnlyChat).toBe(false);
    });
  });

  describe('renderAttachmentMessages', () => {
    it('should render image attachments correctly', () => {
      const attachments = [
        {
          attachment_id: 'att-1',
          filename: 'image.jpg',
          media_type: 'image/jpeg',
          size: 1024,
          vault_mode: false,
          version_index: 0,
          version_count: 0,
          status: AttachmentStatusEnum.READY,
          owner_id: 'test',
          created_at: Date.now().toString(),
          updated_at: Date.now().toString(),
        },
      ];

      const result = renderAttachmentMessages({
        attachments,
        version_index: 0,
        version_count: 1,
      });

      expect(result).toEqual({
        key: 'test-id',
        role: 'fileUser',
        version_count: 1,
        version_index: 0,
        content: [
          {
            uid: 'att-1',
            name: 'image.jpg',
            thumbUrl: `${BACKEND_URL}/attachments/att-1`,
            url: `${BACKEND_URL}/attachments/att-1`,
          },
        ],
      });
    });

    it('should render document attachments correctly', () => {
      const attachments = [
        {
          attachment_id: 'att-2',
          filename: 'document.pdf',
          media_type: 'application/pdf',
          size: 2048,
          vault_mode: false,
          version_index: 0,
          version_count: 0,
          status: AttachmentStatusEnum.READY,
          owner_id: 'test',
          created_at: Date.now().toString(),
          updated_at: Date.now().toString(),
        },
      ];

      const result = renderAttachmentMessages({
        attachments,
        version_index: 1,
        version_count: 2,
      });

      expect(result).toEqual({
        key: 'test-id',
        role: 'fileUser',
        version_count: 2,
        version_index: 1,
        content: [
          {
            uid: 'att-2',
            name: 'document.pdf',
          },
        ],
      });
    });

    it('should handle empty attachments with default values', () => {
      // @ts-expect-error - testing with missing params
      const result = renderAttachmentMessages({});

      expect(result).toEqual({
        key: 'test-id',
        role: 'fileUser',
        version_count: 1,
        version_index: 0,
        content: [],
      });
    });

    it('should handle multiple attachments', () => {
      const attachments = [
        {
          attachment_id: 'att-1',
          filename: 'image.jpg',
          media_type: 'image/jpeg',
          size: 1024,
          vault_mode: false,
          version_index: 0,
          version_count: 0,
          status: AttachmentStatusEnum.READY,
          owner_id: 'test',
          created_at: Date.now().toString(),
          updated_at: Date.now().toString(),
        },
        {
          attachment_id: 'att-2',
          filename: 'document.pdf',
          media_type: 'application/pdf',
          size: 2048,
          vault_mode: false,
          version_index: 0,
          version_count: 0,
          status: AttachmentStatusEnum.READY,
          owner_id: 'test',
          created_at: Date.now().toString(),
          updated_at: Date.now().toString(),
        },
      ];

      const result = renderAttachmentMessages({
        attachments,
        version_index: 0,
        version_count: 1,
      });

      expect(result.content).toHaveLength(2);
      expect(result.content[0]).toMatchObject({
        uid: 'att-1',
        name: 'image.jpg',
        thumbUrl: expect.stringContaining('att-1'),
        url: expect.stringContaining('att-1'),
      });
      expect(result.content[1]).toMatchObject({
        uid: 'att-2',
        name: 'document.pdf',
      });
    });
  });

  describe('renderAIMessage', () => {
    it('should return a properly formatted AI message object', () => {
      const result = renderAIMessage({
        key: 'msg-2',
        role: 'assistant',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'AI response',
          },
        },
        version_count: 1,
        version_index: 0,
        loading: false,
      });

      expect(result).toEqual({
        key: 'msg-2',
        role: RoleEnum.ASSISTANT,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'AI response',
          },
        },
        version_count: 1,
        version_index: 0,
        loading: false,
      });
    });

    it('should handle loading state', () => {
      const result = renderAIMessage({
        key: 'msg-2',
        role: 'assistant',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'AI response',
          },
        },
        version_count: 1,
        version_index: 0,
        loading: true,
      });

      expect(result.loading).toBe(true);
    });

    it('should use default loading value', () => {
      const result = renderAIMessage({
        key: 'msg-2',
        role: 'assistant',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'AI response',
          },
        },
        version_count: 1,
        version_index: 0,
      });

      expect(result.loading).toBe(false);
    });
  });

  describe('transformToMessages', () => {
    it('should transform raw messages to formatted message list', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const messages = {
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'User message',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
          edit: false,
          loading: false,
        },
        'msg-2': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'AI response',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          attachments: [],
          edit: false,
          loading: false,
        },
        'msg-3': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'User with attachment',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [
            {
              attachment_id: 'att-1',
              filename: 'image.jpg',
              media_type: 'image/jpeg',
              size: 1024,
              vault_mode: false,
              version_index: 0,
              version_count: 0,
              status: AttachmentStatusEnum.READY,
              owner_id: 'test',
              created_at: Date.now().toString(),
              updated_at: Date.now().toString(),
            },
          ],
          edit: false,
          loading: false,
        },
      };

      const result = transformToMessages({
        messages,
        onChangeVersion,
        onToggleEdit,
        refInput,
        onSaveEdit,
        onCancelEdit,
        readyOnlyChat: false,
      });

      expect(result).toHaveLength(4);

      expect(result[0]).toMatchObject({
        key: 'msg-1',
        role: RoleEnum.USER,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'User message',
          },
        },
        showEditBtn: true,
      });

      expect(result[1]).toMatchObject({
        key: 'msg-2',
        role: RoleEnum.ASSISTANT,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'AI response',
          },
        },
      });

      expect(result[2]).toMatchObject({
        role: 'fileUser',
        content: [
          {
            uid: 'att-1',
            name: 'image.jpg',
            thumbUrl: expect.any(String),
            url: expect.any(String),
          },
        ],
      });

      expect(result[3]).toMatchObject({
        key: 'msg-3',
        role: RoleEnum.USER,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'User with attachment',
          },
        },
        showEditBtn: false,
      });
    });

    it('should handle empty messages object', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const result = transformToMessages({
        messages: {},
        onChangeVersion,
        onToggleEdit,
        refInput,
        onSaveEdit,
        onCancelEdit,
        readyOnlyChat: false,
      });

      expect(result).toEqual([]);
    });

    it('should add error message when readyOnlyChat is true', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const messages = {
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'User message',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
          edit: false,
          loading: false,
        },
      };

      const result = transformToMessages({
        messages,
        onChangeVersion,
        onToggleEdit,
        refInput,
        onSaveEdit,
        onCancelEdit,
        readyOnlyChat: true,
        statusMessage: 'This chat is read-only',
      });

      expect(result).toHaveLength(2);

      expect(result[1]).toMatchObject({
        key: 'error',
        role: 'error',
        content: 'This chat is read-only',
        version_count: 0,
        version_index: 0,
      });
    });

    it('should handle messages with default values', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const messages = {
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'User message',
            },
          },
        },
      };

      const result = transformToMessages({
        messages: messages as any,
        onChangeVersion,
        onToggleEdit,
        refInput,
        onSaveEdit,
        onCancelEdit,
        readyOnlyChat: false,
      });

      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({
        key: 'msg-1',
        role: RoleEnum.USER,
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'User message',
          },
        },
        version_count: 0,
        version_index: 0,
        showEditBtn: true,
      });
    });

    it('should pass readyOnlyChat to user messages', () => {
      const refInput = createRef<TextAreaRef>();
      const onChangeVersion = jest.fn();
      const onToggleEdit = jest.fn();
      const onSaveEdit = jest.fn();
      const onCancelEdit = jest.fn();

      const messages = {
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'User message',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
          edit: false,
          loading: false,
        },
      };

      const result = transformToMessages({
        messages,
        onChangeVersion,
        onToggleEdit,
        refInput,
        onSaveEdit,
        onCancelEdit,
        readyOnlyChat: true,
      });

      expect(result[0]).toMatchObject({
        readyOnlyChat: true,
      });
    });
  });

  describe('transformMessagesToObject', () => {
    it('should transform array of messages to object keyed by message_id', () => {
      const messages = [
        {
          message_id: 'msg-1',
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Message 1',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
        {
          message_id: 'msg-2',
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Message 2',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
      ];

      const result = transformMessagesToObject(messages);

      expect(result).toEqual({
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Message 1',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
        'msg-2': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Message 2',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
      });
    });

    it('should handle empty array', () => {
      const result = transformMessagesToObject([]);
      expect(result).toEqual({});
    });

    it('should handle undefined input', () => {
      const result = transformMessagesToObject(undefined);
      expect(result).toEqual({});
    });

    it('should handle non-array input', () => {
      const result = transformMessagesToObject({} as any);
      expect(result).toEqual({});
    });
  });
});
