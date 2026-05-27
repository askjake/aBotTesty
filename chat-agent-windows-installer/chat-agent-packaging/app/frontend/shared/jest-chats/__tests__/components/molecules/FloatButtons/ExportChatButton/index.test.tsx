import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ExportChatButton from '@/components/molecules/FloatButtons/ExportChatButton';
import { ChatType } from '@shared/ui/types/chats.types';
import {
  mockStore,
  RootState,
} from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { RoleEnum, ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Mock external dependencies
jest.mock('export-from-json', () => jest.fn());

const mockHandleError = jest.fn();
jest.mock('@shared/ui/hooks/useHandleError.hook', () =>
  jest.fn(() => mockHandleError),
);

jest.mock('@shared/ui/libs/dayjs.libs', () => ({
  __esModule: true,
  default: () => ({
    format: jest.fn(() => '01.01.2024'),
  }),
}));

// Mock getChat service
const mockGetChat = jest.fn();
jest.mock('@shared/ui/services/chats.services', () => ({
  getChat: jest.fn((...args) => mockGetChat(...args)),
}));

// Mock Ant Design components
const mockMessageLoading = jest.fn();
const mockMessageSuccess = jest.fn();

jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  App: {
    useApp: jest.fn(() => ({
      message: {
        loading: mockMessageLoading,
        success: mockMessageSuccess,
      },
    })),
  },
  FloatButton: function MockFloatButton({
    onClick,
    icon,
    'data-testid': customTestId,
    ...props
  }: any) {
    return (
      <button
        onClick={onClick}
        data-testid={customTestId || 'float-button'}
        {...props}
      >
        {icon}
      </button>
    );
  },
}));

describe('ExportChatButton', () => {
  // Get the mocked function
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mockExportFromJSON = require('export-from-json');

  // Helper function to create mock chat
  const createMockChat = (overrides: Partial<ChatType> = {}): ChatType => ({
    chat_id: 'chat1',
    group_id: null,
    title: 'Test Chat',
    created_at: '2024-01-01T09:00:00Z',
    owner_id: 'user1',
    last_message_at: '2024-01-01T10:00:00Z',
    vault_mode: false,
    status: ChatStatusEnum.NORMAL,
    status_msg: null,
    messages: {
      msg1: {
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        created_at: '2024-01-01T10:00:00Z',
        attachments: [],
      },
    },
    active: true,
    favorite: false,
    ...overrides,
  });

  // Helper function to create initial state
  const createInitialState = (
    overrides: Partial<RootState> = {},
  ): Partial<RootState> => ({
    // @ts-ignore
    settings: {
      themeMode: 'light' as const,
      collapsedSidebar: false,
      releases: [],
      showReleaseModal: false,
      hasMoreReleases: false,
      ...overrides.settings,
    },
    chats: {
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: false,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      totalChats: 0,
      hasMoreMessages: false,
      ...overrides.chats,
    },
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockExportFromJSON.mockImplementation(() => {});
    mockGetChat.mockResolvedValue({
      messages: {
        msg1: {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Hello',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:00:00Z',
          attachments: [],
        },
      },
    });
  });

  describe('Basic Rendering', () => {
    it('should render export chat button', () => {
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      expect(screen.getByTestId('float-button')).toBeInTheDocument();

      // Check for SVG element
      const button = screen.getByTestId('float-button');
      const svgElement = button.querySelector('svg');
      expect(svgElement).toBeInTheDocument();
    });

    it('should render with custom props', () => {
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(
        <ExportChatButton
          data-testid='custom-export-button'
          className='custom-class'
        />,
        { store },
      );

      const button = screen.getByTestId('custom-export-button');
      expect(button).toHaveClass('custom-class');
    });
  });

  describe('Button State', () => {
    it('should be enabled when active chat exists and AI is not typing', () => {
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      expect(button).toBeInTheDocument();
    });

    it('should render when no active chat exists', () => {
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: null,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      expect(button).toBeInTheDocument();
    });

    it('should render when AI is typing', () => {
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: true,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      expect(button).toBeInTheDocument();
    });
  });

  describe('Export Functionality', () => {
    it('should fetch chat data and export when clicked', async () => {
      const user = userEvent.setup();
      const mockMessages = {
        msg1: {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Hello',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:00:00Z',
          attachments: [],
        },
        msg2: {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Hi there',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:01:00Z',
          attachments: [],
        },
      };

      mockGetChat.mockResolvedValue({
        messages: mockMessages,
      });

      const mockChat = createMockChat({
        chat_id: 'chat123',
        title: 'Test Chat Export',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockGetChat).toHaveBeenCalledWith({ id: 'chat123' });
      });

      expect(mockMessageLoading).toHaveBeenCalledWith(
        'The chat history exporting in progress...',
        1,
      );

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: [
            {
              message_id: 'msg1',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'Hello',
                },
              },
              role: RoleEnum.USER,
              version_count: 1,
              version_index: 0,
              created_at: '2024-01-01T10:00:00Z',
              attachments: [],
            },
            {
              message_id: 'msg2',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'Hi there',
                },
              },
              role: RoleEnum.ASSISTANT,
              version_count: 1,
              version_index: 0,
              created_at: '2024-01-01T10:01:00Z',
              attachments: [],
            },
          ],
          fileName: 'Chat history "Test Chat Export" 01.01.2024',
          exportType: 'json',
        });
      });

      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalledWith(
          'The chat history has been exported successfully.',
        );
      });
    });

    it('should not export when no active chat', async () => {
      const user = userEvent.setup();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: null,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      expect(mockGetChat).not.toHaveBeenCalled();
      expect(mockExportFromJSON).not.toHaveBeenCalled();
      expect(mockMessageLoading).not.toHaveBeenCalled();
    });

    it('should not export when AI is typing', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: true,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      expect(mockGetChat).not.toHaveBeenCalled();
      expect(mockExportFromJSON).not.toHaveBeenCalled();
      expect(mockMessageLoading).not.toHaveBeenCalled();
    });

    it('should handle empty messages from API', async () => {
      const user = userEvent.setup();
      mockGetChat.mockResolvedValue({
        messages: {},
      });

      const mockChat = createMockChat({
        chat_id: 'chat123',
        title: 'Empty Chat',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: [],
          fileName: 'Chat history "Empty Chat" 01.01.2024',
          exportType: 'json',
        });
      });

      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalled();
      });
    });

    it('should handle messages with missing properties', async () => {
      const user = userEvent.setup();
      mockGetChat.mockResolvedValue({
        messages: {
          msg1: {} as any,
          msg2: { content: 'Hello' } as any,
        },
      });

      const mockChat = createMockChat({
        chat_id: 'chat123',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: [
            {
              message_id: 'msg1',
              content: '',
              role: '',
              version_count: undefined,
              version_index: undefined,
              created_at: undefined,
              attachments: undefined,
            },
            {
              message_id: 'msg2',
              content: 'Hello',
              role: '',
              version_count: undefined,
              version_index: undefined,
              created_at: undefined,
              attachments: undefined,
            },
          ],
          fileName: expect.any(String),
          exportType: 'json',
        });
      });
    });

    it('should handle undefined messages from API', async () => {
      const user = userEvent.setup();
      mockGetChat.mockResolvedValue({});

      const mockChat = createMockChat({
        chat_id: 'chat123',
        title: 'No Messages',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: [],
          fileName: 'Chat history "No Messages" 01.01.2024',
          exportType: 'json',
        });
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle getChat API errors', async () => {
      const user = userEvent.setup();
      const error = new Error('API failed');
      mockGetChat.mockRejectedValue(error);

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      expect(mockExportFromJSON).not.toHaveBeenCalled();
      expect(mockMessageSuccess).not.toHaveBeenCalled();
    });

    it('should handle export errors', async () => {
      const user = userEvent.setup();
      const error = new Error('Export failed');
      mockExportFromJSON.mockImplementation(() => {
        throw error;
      });

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      expect(mockMessageSuccess).not.toHaveBeenCalled();
    });

    it('should reset loading state after error', async () => {
      const user = userEvent.setup();
      const error = new Error('API failed');
      mockGetChat.mockRejectedValueOnce(error);

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');

      // First click fails
      await user.click(button);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      // Reset mock for second attempt
      mockGetChat.mockResolvedValue({ messages: {} });
      jest.clearAllMocks();

      // Second click should work
      await user.click(button);

      await waitFor(() => {
        expect(mockGetChat).toHaveBeenCalled();
      });
    });
  });

  describe('Loading State', () => {
    it('should allow clicking again after export completes', async () => {
      jest.clearAllMocks();

      const user = userEvent.setup();

      mockGetChat.mockResolvedValue({ messages: {} });

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');

      // First click
      await user.click(button);

      // Wait for first export to complete
      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalledTimes(1);
      });

      const firstCallCount = mockGetChat.mock.calls.length;

      // Click again after completion
      await user.click(button);

      // Wait for second export to complete
      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalledTimes(2);
      });

      // Should have been called again
      expect(mockGetChat.mock.calls.length).toBeGreaterThan(firstCallCount);
    });

    it('should show loading message when export starts', async () => {
      jest.clearAllMocks();

      const user = userEvent.setup();
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockMessageLoading).toHaveBeenCalledWith(
          'The chat history exporting in progress...',
          1,
        );
      });
    });
  });

  describe('File Naming', () => {
    it('should generate correct filename with chat title and date', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat({
        title: 'My Important Chat',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            fileName: 'Chat history "My Important Chat" 01.01.2024',
          }),
        );
      });
    });

    it('should handle chat title with special characters', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat({
        title: 'Chat with "quotes" & symbols!',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            fileName: 'Chat history "Chat with "quotes" & symbols!" 01.01.2024',
          }),
        );
      });
    });

    it('should handle empty chat title', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat({
        title: '',
      });

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            fileName: 'Chat history "" 01.01.2024',
          }),
        );
      });
    });
  });

  describe('Data Transformation', () => {
    it('should correctly transform message data', async () => {
      const user = userEvent.setup();
      const mockMessages = {
        'message-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'First message',
            },
          },
          role: RoleEnum.USER,
          version_count: 2,
          version_index: 1,
          created_at: '2024-01-01T10:00:00Z',
          attachments: [],
        },
        'message-2': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Second message',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:01:00Z',
          attachments: [],
        },
      };

      mockGetChat.mockResolvedValue({
        messages: mockMessages,
      });

      const mockChat = createMockChat();

      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: [
            {
              message_id: 'message-1',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'First message',
                },
              },
              role: RoleEnum.USER,
              version_count: 2,
              version_index: 1,
              created_at: '2024-01-01T10:00:00Z',
              attachments: [],
            },
            {
              message_id: 'message-2',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'Second message',
                },
              },
              role: RoleEnum.ASSISTANT,
              version_count: 1,
              version_index: 0,
              created_at: '2024-01-01T10:01:00Z',
              attachments: [],
            },
          ],
          fileName: 'Chat history "Test Chat" 01.01.2024',
          exportType: 'json',
        });
      });
    });

    it('should handle messages with attachments', async () => {
      const user = userEvent.setup();
      const mockMessages = {
        msg1: {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Message with attachment',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:00:00Z',
          attachments: [
            {
              attachment_id: 'att1',
              filename: 'document.pdf',
              media_type: 'application/pdf',
              size: 1024,
            },
          ],
        },
      };

      mockGetChat.mockResolvedValue({
        messages: mockMessages,
      });

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            data: [
              expect.objectContaining({
                attachments: [
                  {
                    attachment_id: 'att1',
                    filename: 'document.pdf',
                    media_type: 'application/pdf',
                    size: 1024,
                  },
                ],
              }),
            ],
          }),
        );
      });
    });

    it('should handle complex message content', async () => {
      const user = userEvent.setup();
      const mockMessages = {
        msg1: {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Regular text',
            },
            1: {
              type: MessageTypeEnum.REASONING,
              reasoning: 'Thinking process',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-01T10:00:00Z',
          attachments: [],
        },
      };

      mockGetChat.mockResolvedValue({
        messages: mockMessages,
      });

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            data: [
              expect.objectContaining({
                content: {
                  0: {
                    type: MessageTypeEnum.TEXT,
                    text: 'Regular text',
                  },
                  1: {
                    type: MessageTypeEnum.REASONING,
                    reasoning: 'Thinking process',
                  },
                },
              }),
            ],
          }),
        );
      });
    });
  });

  describe('Export Configuration', () => {
    it('should always export as JSON format', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith(
          expect.objectContaining({
            exportType: 'json',
          }),
        );
      });
    });

    it('should include all required fields in export data', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockExportFromJSON).toHaveBeenCalledWith({
          data: expect.any(Array),
          fileName: expect.any(String),
          exportType: 'json',
        });
      });
    });
  });

  describe('Success Messages', () => {
    it('should show success message after successful export', async () => {
      const user = userEvent.setup();
      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalledWith(
          'The chat history has been exported successfully.',
        );
      });
    });

    it('should not show success message on error', async () => {
      const user = userEvent.setup();
      const error = new Error('Export failed');
      mockGetChat.mockRejectedValue(error);

      const mockChat = createMockChat();
      const store = mockStore(
        createInitialState({
          chats: {
            chats: [],
            activeChat: mockChat,
            vaultMode: false,
            vaultModeRegistered: false,
            showEnableVaultModal: false,
            aiTyping: false,
            hasMoreChats: false,
            totalChats: 0,
            hasMoreMessages: false,
          },
        }),
      );

      renderLayout(<ExportChatButton />, { store });

      const button = screen.getByTestId('float-button');
      await user.click(button);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalled();
      });

      expect(mockMessageSuccess).not.toHaveBeenCalled();
    });
  });
});
