import React, { forwardRef } from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import ChatSender from '@shared/ui/components/molecules/Chat/ChatSender';
import { SenderHeaderBlockProps } from '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.props';
import { AttachmentButtonProps } from '@shared/ui/components/molecules/Chat/AttachmentButton/AttachmentButton.props';
import { AttachmentStatusEnum } from '@shared/ui/enums/chats.enums';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { uploadAttachments } from '@shared/ui/services/attachments.services';
import { ChatType } from '@shared/ui/types/chats.types';
import { dexieDb } from '@shared/ui/libs/dexie.libs';
import * as commonUtils from '@shared/ui/utils/common.utils';

// Suppress React 18 act warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes(
        'The current testing environment is not configured to support act',
      )
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

// Mock services
jest.mock('@shared/ui/services/attachments.services', () => ({
  uploadAttachments: jest.fn(),
}));

// Mock dexie
jest.mock('@shared/ui/libs/dexie.libs', () => ({
  dexieDb: {
    draftMessages: {
      get: jest.fn(),
      put: jest.fn(),
      delete: jest.fn(),
    },
  },
}));

// Mock common utils
jest.mock('@shared/ui/utils/common.utils', () => ({
  isIndexedDBSupported: jest.fn(),
}));

// Mock useHandleError hook
const mockHandleError = jest.fn();
jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: () => mockHandleError,
}));

// Mock usePrevious hook
let mockPreviousValue: string | undefined = undefined;
jest.mock('@shared/ui/hooks/usePrevious.hook', () => {
  return jest.fn(() => mockPreviousValue);
});

// Mock Sender component
jest.mock('@ant-design/x', () => ({
  Sender: ({
    value,
    onChange,
    onSubmit,
    header,
    footer,
    loading,
    disabled,
    className,
  }: any) => {
    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (value?.trim()) {
          onSubmit(value);
        }
      }
    };

    const handleSubmit = () => {
      if (value?.trim()) {
        onSubmit(value);
      }
    };

    return (
      <div
        data-testid='chat-sender'
        className={className}
        data-loading={loading}
        data-disabled={disabled}
      >
        {header}
        <textarea
          data-testid='message-input'
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          role='textbox'
        />
        <button
          data-testid='submit-button'
          onClick={handleSubmit}
          disabled={disabled}
        >
          Submit
        </button>
        {footer &&
          footer(null, {
            components: {
              SendButton: ({ disabled: btnDisabled, type }: any) => (
                <button
                  data-testid='send-button'
                  disabled={btnDisabled}
                  onClick={handleSubmit}
                  data-type={type}
                >
                  Send
                </button>
              ),
              LoadingButton: ({ type }: any) => (
                <button data-testid='loading-button' disabled data-type={type}>
                  Loading...
                </button>
              ),
            },
          })}
      </div>
    );
  },
}));

// Mock AttachmentButton
jest.mock(
  'next/dynamic',
  () => () =>
    // eslint-disable-next-line react/display-name
    forwardRef(
      (
        {
          setHeaderOpen,
          headerOpen,
          hasFiles,
          disabled,
        }: AttachmentButtonProps,
        ref,
      ) => (
        <button
          data-testid='attachment-button'
          onClick={() => setHeaderOpen(!headerOpen)}
          data-has-files={hasFiles}
          disabled={disabled}
        >
          Attachment
        </button>
      ),
    ),
);

// Mock SenderHeaderBlock
jest.mock('@shared/ui/components/molecules/Chat/SenderHeaderBlock', () => {
  return forwardRef(function Component(
    {
      onAddAttachment,
      open,
      onRemoveAttachment,
      setLoading,
    }: Pick<
      SenderHeaderBlockProps,
      | 'onAddAttachment'
      | 'open'
      | 'onOpenChange'
      | 'onRemoveAttachment'
      | 'setLoading'
      | 'componentRef'
    >,
    ref,
  ) {
    const resetAttachments = jest.fn();

    React.useImperativeHandle(ref, () => ({
      resetAttachments,
    }));

    return (
      <div data-testid='sender-header-block' data-open={open}>
        <button
          data-testid='add-attachment'
          onClick={() =>
            onAddAttachment([
              {
                uid: '1',
                name: 'test.jpg',
                type: 'image/jpeg',
                size: 1024,
              } as any,
            ])
          }
        >
          Add Attachment
        </button>
        <button
          data-testid='remove-attachment'
          onClick={() => onRemoveAttachment('1')}
        >
          Remove Attachment
        </button>
        <button data-testid='set-loading' onClick={() => setLoading(true)}>
          Set Loading
        </button>
      </div>
    );
  });
});

// Mock Ant Design components
jest.mock('antd', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    icon,
    color,
    variant,
    type,
    shape,
  }: any) => (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={`ant-button-${type || shape || 'default'}`}
      data-color={color}
      data-variant={variant}
      data-shape={shape}
    >
      {icon && <span data-testid='button-icon'>{icon}</span>}
      {children}
    </button>
  ),
  Dropdown: ({ children, menu, trigger }: any) => {
    return (
      <div data-testid='dropdown' data-trigger={trigger?.join(',')}>
        {children}
        <div data-testid='dropdown-menu'>
          {menu?.items?.map((item: any, index: number) => {
            if (item.type === 'divider') {
              return (
                <div key={`divider-${index}`} data-testid='menu-divider' />
              );
            }

            const isSelected = menu?.selectedKeys?.includes(item.key);
            return (
              <button
                key={item.key || `item-${index}`}
                data-testid={`menu-item-${item.key || index}`}
                data-selected={isSelected}
                onClick={() => {
                  if (!menu.disabled) {
                    menu.onClick?.({ key: item.key });
                  }
                }}
                disabled={item.disabled || menu.disabled}
              >
                {item.icon && (
                  <span data-testid={`menu-icon-${item.key}`}>{item.icon}</span>
                )}
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    );
  },
  Flex: ({ children, justify, align, gap }: any) => (
    <div
      data-testid='flex'
      data-justify={justify}
      data-align={align}
      data-gap={gap}
    >
      {children}
    </div>
  ),
}));

// Mock icons
jest.mock('react-icons/vsc', () => ({
  VscLightbulbSparkle: () => <span data-testid='lightbulb-icon'>💡</span>,
  VscSettings: () => <span data-testid='settings-icon'>⚙️</span>,
}));

jest.mock('@ant-design/icons', () => ({
  CloseOutlined: () => <span data-testid='close-icon'>✕</span>,
}));

// Mock styled components
jest.mock(
  '@shared/ui/components/molecules/Chat/ChatSender/ChatSender.styled',
  () => ({
    StyledChatSenderWrapper: ({ children }: any) => (
      <div data-testid='chat-sender-wrapper'>{children}</div>
    ),
  }),
);

describe('ChatSender Component', () => {
  let defaultStore: RootStore;
  let mockOnRequest: jest.Mock;
  let mockUploadAttachments: jest.MockedFunction<typeof uploadAttachments>;
  let mockIsIndexedDBSupported: jest.MockedFunction<
    typeof commonUtils.isIndexedDBSupported
  >;
  let mockDexieGet: jest.Mock;
  let mockDexiePut: jest.Mock;
  let mockDexieDelete: jest.Mock;

  const createMutableObject = (obj: any) => {
    return JSON.parse(JSON.stringify(obj));
  };

  const createMockChat = (overrides: Partial<ChatType> = {}): ChatType => ({
    chat_id: 'test-chat',
    messages: {},
    title: 'Test Chat',
    active: true,
    created_at: '2023-01-01T00:00:00Z',
    owner_id: 'user-123',
    last_message_at: '2023-01-01T00:00:00Z',
    vault_mode: false,
    status: ChatStatusEnum.NORMAL,
    favorite: false,
    status_msg: null,
    group_id: null,
    ...overrides,
  });

  beforeEach(async () => {
    mockUploadAttachments = uploadAttachments as jest.MockedFunction<
      typeof uploadAttachments
    >;
    mockIsIndexedDBSupported =
      commonUtils.isIndexedDBSupported as jest.MockedFunction<
        typeof commonUtils.isIndexedDBSupported
      >;
    mockDexieGet = dexieDb.draftMessages.get as jest.Mock;
    mockDexiePut = dexieDb.draftMessages.put as jest.Mock;
    mockDexieDelete = dexieDb.draftMessages.delete as jest.Mock;

    jest.clearAllMocks();
    mockPreviousValue = undefined;
    mockOnRequest = jest.fn();
    mockIsIndexedDBSupported.mockReturnValue(true);
    mockDexieGet.mockResolvedValue(null);
    mockDexiePut.mockResolvedValue(undefined);
    mockDexieDelete.mockResolvedValue(undefined);

    defaultStore = createMutableObject({
      chats: {
        totalChats: 5,
        chats: [],
        activeChat: null,
        aiTyping: false,
      },
      settings: {
        collapsedSidebar: false,
      },
    });

    mockUploadAttachments.mockResolvedValue({
      attachments: [
        {
          attachment_id: '1',
          filename: 'test.jpg',
          media_type: 'image/jpeg',
          status: AttachmentStatusEnum.READY,
          created_at: '2023-01-01T00:00:00Z',
          updated_at: '2023-01-01T00:00:00Z',
          vault_mode: false,
          owner_id: 'user-123',
        },
      ],
    });
  });

  describe('Basic Functionality', () => {
    it('renders component', () => {
      const store = mockStore(defaultStore);
      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      expect(screen.getByTestId('chat-sender')).toBeInTheDocument();
      expect(screen.getByTestId('message-input')).toBeInTheDocument();
      expect(screen.getByTestId('submit-button')).toBeInTheDocument();
    });

    it('updates input value when typing', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');

      expect(input).toHaveValue('Test message');
    });

    it('prevents empty message submission', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      await user.click(screen.getByTestId('submit-button'));

      expect(mockOnRequest).not.toHaveBeenCalled();
    });
  });

  describe('Draft Messages - IndexedDB', () => {
    it('loads draft message from IndexedDB on mount', async () => {
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      mockDexieGet.mockResolvedValue({
        chat_id: 'test-chat-1',
        message: 'Draft message',
        updated_at: new Date(),
      });

      const store = mockStore(defaultStore);
      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      await waitFor(() => {
        expect(mockDexieGet).toHaveBeenCalledWith('test-chat-1');
      });

      await waitFor(() => {
        const input = screen.getByTestId('message-input');
        expect(input).toHaveValue('Draft message');
      });
    });

    it('saves draft message to IndexedDB with debounce', async () => {
      jest.useFakeTimers();
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      const store = mockStore(defaultStore);
      const user = userEvent.setup({ delay: null });

      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Draft');

      expect(mockDexiePut).not.toHaveBeenCalled();

      jest.advanceTimersByTime(500);

      await waitFor(() => {
        expect(mockDexiePut).toHaveBeenCalledWith({
          chat_id: 'test-chat-1',
          message: 'Draft',
          updated_at: expect.any(Date),
        });
      });

      jest.useRealTimers();
    });

    it('deletes draft from IndexedDB after successful message send', async () => {
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockDexieDelete).toHaveBeenCalledWith('test-chat-1');
      });
    });

    it('deletes draft when message is cleared', async () => {
      jest.useFakeTimers();
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      const store = mockStore(defaultStore);
      const user = userEvent.setup({ delay: null });

      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Draft');

      jest.advanceTimersByTime(500);

      await waitFor(() => {
        expect(mockDexiePut).toHaveBeenCalled();
      });

      await user.clear(input);

      jest.advanceTimersByTime(500);

      await waitFor(() => {
        expect(mockDexieDelete).toHaveBeenCalledWith('test-chat-1');
      });

      jest.useRealTimers();
    });

    it('does not save draft when IndexedDB is not supported', async () => {
      mockIsIndexedDBSupported.mockReturnValue(false);
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Draft');

      await waitFor(() => {
        expect(mockDexiePut).not.toHaveBeenCalled();
      });
    });

    it('handles IndexedDB errors gracefully', async () => {
      const mockChat = createMockChat({ chat_id: 'test-chat-1' });
      mockDexieGet.mockRejectedValue(new Error('IndexedDB error'));

      const store = mockStore(defaultStore);
      renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={mockChat} />,
        { store },
      );

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(expect.any(Error));
      });
    });
  });

  describe('Message Creation', () => {
    it('calls onRequest with correct parameters', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalledWith({
          content: 'Test message',
          attachments: [],
          selectedKey: [],
        });
      });
    });

    it('clears input after submission', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });
  });

  describe('Attachments', () => {
    it('includes attachments in onRequest call', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      await user.click(screen.getByTestId('add-attachment'));

      await waitFor(() => {
        expect(mockUploadAttachments).toHaveBeenCalled();
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Message with attachment');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalledWith({
          content: 'Message with attachment',
          attachments: [
            {
              attachment_id: '1',
              filename: 'test.jpg',
              media_type: 'image/jpeg',
              status: AttachmentStatusEnum.READY,
              created_at: '2023-01-01T00:00:00Z',
              updated_at: '2023-01-01T00:00:00Z',
              vault_mode: false,
              owner_id: 'user-123',
            },
          ],
          selectedKey: [],
        });
      });
    });

    it('clears attachments after submission', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      await user.click(screen.getByTestId('add-attachment'));

      await waitFor(() => {
        expect(mockUploadAttachments).toHaveBeenCalled();
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'First message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalledWith({
          content: 'First message',
          attachments: expect.arrayContaining([
            expect.objectContaining({
              attachment_id: '1',
            }),
          ]),
          selectedKey: [],
        });
      });

      await user.type(input, 'Second message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalledWith({
          content: 'Second message',
          attachments: [],
          selectedKey: [],
        });
      });
    });
  });

  describe('Tools Integration', () => {
    it('includes reasoning in selectedKey when tool is selected', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const reasoningMenuItem = screen.getByTestId('menu-item-1');
      await user.click(reasoningMenuItem);

      await waitFor(() => {
        expect(reasoningMenuItem).toHaveAttribute('data-selected', 'true');
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test with reasoning');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalledWith({
          content: 'Test with reasoning',
          attachments: [],
          selectedKey: ['1'],
        });
      });
    });

    it('deselects reasoning when close button is clicked', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const reasoningMenuItem = screen.getByTestId('menu-item-1');
      await user.click(reasoningMenuItem);

      await waitFor(() => {
        expect(reasoningMenuItem).toHaveAttribute('data-selected', 'true');
      });

      const reasoningButton = await screen.findByText('Reasoning');
      await user.click(reasoningButton.closest('button')!);

      await waitFor(() => {
        expect(reasoningMenuItem).toHaveAttribute('data-selected', 'false');
        expect(screen.queryByText('Reasoning')).not.toBeInTheDocument();
      });
    });
  });

  describe('Keyboard Shortcuts', () => {
    it('submits message on Enter key', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(mockOnRequest).toHaveBeenCalled();
      });
    });

    it('does not submit on Shift+Enter', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.keyboard('{Shift>}{Enter}{/Shift}');

      expect(mockOnRequest).not.toHaveBeenCalled();
      expect(input).toHaveValue('Test message\n');
    });
  });

  describe('Disabled State', () => {
    it('disables input when chat is readonly', () => {
      const storeData = createMutableObject({
        ...defaultStore,
        chats: {
          ...defaultStore.chats,
          activeChat: createMockChat({
            status: ChatStatusEnum.READONLY,
          }),
        },
      });

      const store = mockStore(storeData);
      renderLayout(
        <ChatSender
          onRequest={mockOnRequest}
          activeChat={storeData.chats.activeChat}
        />,
        { store },
      );

      expect(screen.getByTestId('chat-sender')).toHaveAttribute(
        'data-disabled',
        'true',
      );
      expect(screen.getByTestId('message-input')).toBeDisabled();
    });

    it('shows loading button when aiTyping is true', () => {
      const storeData = createMutableObject({
        ...defaultStore,
        chats: {
          ...defaultStore.chats,
          aiTyping: true,
        },
      });

      const store = mockStore(storeData);
      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      expect(screen.getByTestId('loading-button')).toBeInTheDocument();
    });
  });

  describe('Chat Change', () => {
    it('resets input when active chat changes', async () => {
      const storeData = createMutableObject({
        ...defaultStore,
        chats: {
          ...defaultStore.chats,
          activeChat: createMockChat({
            chat_id: 'test-chat-1',
          }),
        },
      });

      const store = mockStore(storeData);
      const user = userEvent.setup();

      const { rerender } = renderLayout(
        <ChatSender
          onRequest={mockOnRequest}
          activeChat={storeData.chats.activeChat}
        />,
        { store },
      );

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');

      expect(input).toHaveValue('Test message');

      mockPreviousValue = 'test-chat-1';
      const newActiveChat = createMockChat({
        chat_id: 'test-chat-2',
      });

      rerender(
        <ChatSender onRequest={mockOnRequest} activeChat={newActiveChat} />,
      );

      await waitFor(() => {
        expect(input).toHaveValue('');
      });
    });

    it('loads new draft when switching chats', async () => {
      const chat1 = createMockChat({ chat_id: 'test-chat-1' });
      const chat2 = createMockChat({ chat_id: 'test-chat-2' });

      mockDexieGet.mockImplementation((chatId) => {
        if (chatId === 'test-chat-2') {
          return Promise.resolve({
            chat_id: 'test-chat-2',
            message: 'Draft for chat 2',
            updated_at: new Date(),
          });
        }
        return Promise.resolve(null);
      });

      const store = mockStore(defaultStore);
      const { rerender } = renderLayout(
        <ChatSender onRequest={mockOnRequest} activeChat={chat1} />,
        { store },
      );

      mockPreviousValue = 'test-chat-1';
      rerender(<ChatSender onRequest={mockOnRequest} activeChat={chat2} />);

      await waitFor(() => {
        expect(mockDexieGet).toHaveBeenCalledWith('test-chat-2');
      });

      await waitFor(() => {
        const input = screen.getByTestId('message-input');
        expect(input).toHaveValue('Draft for chat 2');
      });
    });
  });

  describe('Header State', () => {
    it('closes header after message submission', async () => {
      const store = mockStore(defaultStore);
      const user = userEvent.setup();

      renderLayout(<ChatSender onRequest={mockOnRequest} activeChat={null} />, {
        store,
      });

      await user.click(screen.getByTestId('attachment-button'));

      let header = screen.getByTestId('sender-header-block');
      expect(header).toHaveAttribute('data-open', 'true');

      const input = screen.getByTestId('message-input');
      await user.type(input, 'Test message');
      await user.click(screen.getByTestId('submit-button'));

      await waitFor(() => {
        header = screen.getByTestId('sender-header-block');
        expect(header).toHaveAttribute('data-open', 'false');
      });
    });
  });
});
