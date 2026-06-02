import React from 'react';
import { screen, act, waitFor } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import {
  createChat,
  getChat,
  getChats,
} from '@shared/ui/services/chats.services';
import {
  createMessage,
  createMessageVersion,
  getMessages,
  changeMessageVersion,
} from '@shared/ui/services/messages.services';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Mock styled components FIRST
jest.mock('@/components/organisms/ReportsChat/ReportsChat.styled', () => {
  const React = require('react');
  return {
    __esModule: true,
    StyledReportsChatContainer: ({ children, $hasMessages, ...props }: any) => (
      <div
        data-testid='styled-reports-chat-container'
        data-has-messages={$hasMessages}
        {...props}
      >
        {children}
      </div>
    ),
  };
});

// Mock @ant-design/x
jest.mock('@ant-design/x', () => ({
  XStream: jest.fn(),
  Bubble: {
    List: jest.fn(),
  },
}));

// Mock Next.js dynamic imports
jest.mock('next/dynamic', () => {
  return (importFunc: any, options?: any) => {
    const React = require('react');

    const DynamicComponent = React.forwardRef((props: any, ref: any) => {
      // @ts-ignore
      const [Component, setComponent] = React.useState<any>(null);

      React.useEffect(() => {
        let isMounted = true;

        const loadComponent = async () => {
          try {
            const funcString = importFunc.toString();
            let componentName = 'DynamicComponent';

            if (funcString.includes('WelcomeBlock')) {
              componentName = 'WelcomeBlock';
            } else if (funcString.includes('MessagesBlock')) {
              componentName = 'MessagesBlock';
            } else if (funcString.includes('ChatSender')) {
              componentName = 'ChatSender';
            }

            if (!isMounted) return;

            // Create a mock component based on the type
            const MockComponent = (componentProps: any) => {
              const {
                componentRef,
                items,
                logo,
                onRequest,
                onLoadMore,
                activeChat,
                customHeight,
                isLoading,
                ...domProps
              } = componentProps;

              // Expose scrollBottom method for MessagesBlock
              React.useImperativeHandle(
                componentRef || ref,
                () => ({
                  scrollBottom: jest.fn(),
                }),
                [],
              );

              return (
                <div
                  data-testid={`dynamic-${componentName.toLowerCase()}`}
                  data-component-name={componentName}
                  data-is-loading={isLoading}
                  ref={componentRef || ref}
                  {...domProps}
                >
                  {logo && (
                    <img src={logo} alt='logo' data-testid='welcome-logo' />
                  )}
                  {items !== undefined && (
                    <div data-testid='items-count'>{items.length}</div>
                  )}
                  {items && items.length === 0 && (
                    <div data-testid='no-items'>No items</div>
                  )}
                  {items && items.length > 0 && (
                    <div data-testid='has-items'>
                      {items.map((item: any, idx: number) => (
                        <div key={idx} data-testid={`item-${idx}`}>
                          {item.content}
                        </div>
                      ))}
                    </div>
                  )}
                  {onRequest && (
                    <button
                      data-testid='trigger-request'
                      onClick={() =>
                        onRequest({ content: 'test message', attachments: [] })
                      }
                    >
                      Send
                    </button>
                  )}
                  {onLoadMore && (
                    <button
                      data-testid='trigger-load-more'
                      onClick={() => onLoadMore()}
                    >
                      Load More
                    </button>
                  )}
                </div>
              );
            };

            setComponent(() => MockComponent);
          } catch (err) {
            console.error('Error loading dynamic component:', err);
          }
        };

        loadComponent();

        return () => {
          isMounted = false;
        };
      }, []);

      if (!Component) {
        return options?.loading ? React.createElement(options.loading) : null;
      }

      return React.createElement(Component, { ...props, ref });
    });

    DynamicComponent.displayName = 'LoadableComponent';
    return DynamicComponent;
  };
});

jest.mock('@shared/ui/hooks/useHandleError.hook');
jest.mock('@shared/ui/services/chats.services');
jest.mock('@shared/ui/services/messages.services');

// Mock utils
jest.mock('@shared/ui/utils/messages.utils', () => ({
  transformToMessages: jest.fn((params) => {
    const messages = params.messages || {};
    return Object.entries(messages).map(([key, value]: [string, any]) => ({
      key,
      content: value.content?.[0]?.text || '',
      variant: 'filled',
    }));
  }),
  transformMessagesToObject: jest.fn((docs) => {
    return docs.reduce((acc: any, doc: any) => {
      acc[doc.message_id] = doc;
      return acc;
    }, {});
  }),
}));

jest.mock('@shared/ui/utils/common.utils', () => ({
  omitKeys: jest.fn(({ obj, keysToRemove }) => {
    const result = { ...obj };
    keysToRemove.forEach((key: string) => delete result[key]);
    return result;
  }),
}));

jest.mock('@shared/ui/hooks/usePrevious.hook', () => ({
  __esModule: true,
  default: jest.fn(() => null),
}));

jest.mock('@shared/ui/constants/common.constants', () => ({
  CHAT_MESSAGES_PAGE_SIZE: 25,
}));

// Mock Redux actions and reducers
jest.mock('@shared/ui/store/chats/chats.slice', () => ({
  setAiTyping: jest.fn((payload) => ({
    type: 'chats/setAiTyping',
    payload,
  })),
  setHasMoreMessages: jest.fn((payload) => ({
    type: 'chats/setHasMoreMessages',
    payload,
  })),
  chatsReducer: (
    state = {
      chats: [],
      activeChat: null,
      hasMoreChats: false,
      hasMoreMessages: false,
      totalChats: 0,
      vaultMode: false,
      vaultModeRegistered: false,
      showEnableVaultModal: false,
      aiTyping: false,
    },
  ) => state,
}));

jest.mock('@shared/ui/store/chatsGroups/chatsGroups.slice', () => ({
  chatsGroupsReducer: (
    state = {
      activeChatGroup: 'all',
      groups: [],
    },
  ) => state,
}));

jest.mock('@shared/ui/store/settings/settings.slice', () => ({
  settingsReducer: (
    state = {
      themeMode: 'light',
      collapsedSidebar: false,
    },
  ) => state,
}));

// Import component after ALL mocks
import ReportsChat from '@/components/organisms/ReportsChat';

const mockGetChats = getChats as jest.MockedFunction<typeof getChats>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockCreateChat = createChat as jest.MockedFunction<typeof createChat>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;
const mockCreateMessage = createMessage as jest.MockedFunction<
  typeof createMessage
>;
const mockCreateMessageVersion = createMessageVersion as jest.MockedFunction<
  typeof createMessageVersion
>;
const mockChangeMessageVersion = changeMessageVersion as jest.MockedFunction<
  typeof changeMessageVersion
>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;

// Suppress act warnings
const originalError = console.error;
beforeAll(() => {
  jest.useFakeTimers();
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act') ||
        args[0].includes('No reducer provided') ||
        args[0].includes('Store does not have a valid reducer'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  jest.useRealTimers();
  console.error = originalError;
});

describe('ReportsChat Component', () => {
  const mockHandleError = jest.fn();

  const mockChat = {
    chat_id: 'chat-1',
    title: 'Test Chat',
    created_at: '2025-01-01T00:00:00Z',
    owner_id: 'user-1',
    last_message_at: '2025-01-01T00:00:00Z',
    vault_mode: false,
    messages: {
      'msg-1': {
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        attachments: [],
      },
    },
    active: true,
    favorite: false,
    status: ChatStatusEnum.NORMAL,
    status_msg: null,
    group_id: null,
  };

  const mockMessagesResponse = {
    docs: [
      {
        message_id: 'msg-1',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        attachments: [],
      },
    ],
    hasNextPage: false,
    totalDocs: 1,
    limit: 25,
    page: 1,
    totalPages: 1,
    nextPage: 1,
    hasPrevPage: false,
    prevPage: 1,
  };

  const defaultState = {
    settings: {
      themeMode: 'light' as const,
      collapsedSidebar: false,
    },
    chats: {
      chats: [],
      activeChat: null,
      hasMoreChats: false,
      hasMoreMessages: false,
      totalChats: 0,
      vaultMode: false,
      vaultModeRegistered: false,
      showEnableVaultModal: false,
      aiTyping: false,
    },
    chatsGroups: {
      activeChatGroup: 'all',
      groups: [],
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockGetMessages.mockResolvedValue(mockMessagesResponse);
    mockGetChats.mockResolvedValue({
      docs: [mockChat],
      hasNextPage: false,
      totalDocs: 1,
      limit: 1,
      page: 1,
      totalPages: 1,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 1,
      active_chat_id: 'chat-1',
    });
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
  });

  const renderWithStore = (component: React.ReactElement) => {
    const store = mockStore(defaultState);
    return renderLayout(component, { store });
  };

  it('renders without crashing', async () => {
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(
        screen.getByTestId('styled-reports-chat-container'),
      ).toBeInTheDocument();
    });
  });

  it('renders ChatSender component', async () => {
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('dynamic-chatsender')).toBeInTheDocument();
    });
  });

  it('renders WelcomeBlock when no messages', async () => {
    const emptyChat = { ...mockChat, messages: {} };
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={emptyChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('dynamic-messagesblock')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-logo')).toBeInTheDocument();
    });
  });

  it('applies custom className', async () => {
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat
          chat={mockChat}
          componentRef={mockComponentRef}
          className='custom-class'
        />,
      );
    });

    await waitFor(() => {
      const card = screen.getByText((content, element) => {
        return (
          element?.className?.includes('reports-chat custom-class') || false
        );
      });
      expect(card.closest('.ant-card')).toHaveClass('reports-chat');
      expect(card.closest('.ant-card')).toHaveClass('custom-class');
    });
  });

  it('passes additional Card props', async () => {
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat
          chat={mockChat}
          componentRef={mockComponentRef}
          data-testid='custom-card'
        />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('custom-card')).toBeInTheDocument();
    });
  });

  it('exposes refetchData method via ref', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(<ReportsChat chat={mockChat} componentRef={ref} />);
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
      expect(ref.current.refetchData).toBeInstanceOf(Function);
    });
  });

  it('creates new chat if no existing chat found', async () => {
    mockGetChats.mockResolvedValue({
      docs: [],
      hasNextPage: false,
      totalDocs: 0,
      limit: 1,
      page: 1,
      totalPages: 0,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 1,
      active_chat_id: undefined,
    });

    mockCreateChat.mockResolvedValue(mockChat);

    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(<ReportsChat chat={mockChat} componentRef={ref} />);
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockCreateChat).toHaveBeenCalledWith({
        namespace: 'beta_report/androidtv',
      });
    });
  });

  it('handles API errors gracefully', async () => {
    const error = new Error('API Error');
    mockGetChats.mockRejectedValue(error);

    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(<ReportsChat chat={mockChat} componentRef={ref} />);
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(error);
    });
  });

  it('loads messages for active chat', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(<ReportsChat chat={mockChat} componentRef={ref} />);
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockGetMessages).toHaveBeenCalledWith({
        chat_id: 'chat-1',
        page: 1,
        limit: 25,
      });
    });
  });

  it('uses default platform when not provided', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(<ReportsChat chat={mockChat} componentRef={ref} />);
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 1,
        namespace: 'beta_report/androidtv',
      });
    });
  });

  it('handles load more messages', async () => {
    const mockComponentRef = { current: null };

    const moreMessagesResponse = {
      ...mockMessagesResponse,
      docs: [
        {
          message_id: 'msg-2',
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'More messages',
            },
          },
          role: RoleEnum.ASSISTANT,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
      ],
      hasNextPage: false,
    };

    mockGetMessages.mockResolvedValue(moreMessagesResponse);

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('trigger-load-more')).toBeInTheDocument();
    });

    const loadMoreButton = screen.getByTestId('trigger-load-more');

    await act(async () => {
      loadMoreButton.click();
    });

    await waitFor(() => {
      expect(mockGetMessages).toHaveBeenCalled();
    });
  });

  it('displays welcome block logo correctly', async () => {
    const emptyChat = { ...mockChat, messages: {} };
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={emptyChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      const logo = screen.getByTestId('welcome-logo');
      expect(logo).toHaveAttribute('src', '/beta-reports/img/logo.png');
    });
  });

  it('handles getMessages error during load more', async () => {
    const mockComponentRef = { current: null };
    const error = new Error('Failed to load messages');

    mockGetMessages.mockClear();
    mockHandleError.mockClear();

    mockGetMessages.mockRejectedValueOnce(error);

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('trigger-load-more')).toBeInTheDocument();
    });

    const loadMoreButton = screen.getByTestId('trigger-load-more');

    await act(async () => {
      loadMoreButton.click();
    });

    await waitFor(
      () => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      },
      { timeout: 3000 },
    );
  });

  it('does not load more when no active chat', async () => {
    const chatWithoutId = { ...mockChat, chat_id: '' };
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={chatWithoutId} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('trigger-load-more')).toBeInTheDocument();
    });

    const loadMoreButton = screen.getByTestId('trigger-load-more');

    mockGetMessages.mockClear();

    await act(async () => {
      loadMoreButton.click();
    });

    // Use fake timers to advance time instead of real setTimeout
    await act(async () => {
      jest.advanceTimersByTime(100);
    });

    expect(mockGetMessages).not.toHaveBeenCalled();
  });

  it('uses correct namespace format for platform', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(
        <ReportsChat
          chat={mockChat}
          componentRef={ref}
          platform='CustomPlatform'
        />,
      );
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 1,
        namespace: 'beta_report/customplatform',
      });
    });
  });

  it('converts platform to lowercase in namespace', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={ref} platform='DishTV' />,
      );
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 1,
        namespace: 'beta_report/dishtv',
      });
    });
  });

  it('passes isLoading prop to MessagesBlock', async () => {
    const mockComponentRef = { current: null };

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    await waitFor(() => {
      const messagesBlock = screen.getByTestId('dynamic-messagesblock');
      expect(messagesBlock).toHaveAttribute('data-is-loading', 'false');
    });
  });

  it('refetches data when platform changes', async () => {
    const ref = React.createRef<any>();
    const usePreviousMock =
      require('@shared/ui/hooks/usePrevious.hook').default;

    const { rerender } = await act(async () => {
      return renderWithStore(
        <ReportsChat chat={mockChat} componentRef={ref} platform='androidtv' />,
      );
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    // Mock usePrevious to return the previous platform value
    usePreviousMock.mockReturnValue('androidtv');

    mockGetChats.mockClear();

    await act(async () => {
      const store = mockStore(defaultState);
      rerender(
        // @ts-ignore
        renderLayout(
          <ReportsChat chat={mockChat} componentRef={ref} platform='dishtv' />,
          { store },
        ).container.firstChild as React.ReactElement,
      );
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 1,
        namespace: 'beta_report/dishtv',
      });
    });
  });

  it('sets loading state during load more', async () => {
    const mockComponentRef = { current: null };

    mockGetMessages.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve(mockMessagesResponse);
          }, 100);
        }),
    );

    await act(async () => {
      renderWithStore(
        <ReportsChat chat={mockChat} componentRef={mockComponentRef} />,
      );
    });

    const loadMoreButton = screen.getByTestId('trigger-load-more');

    act(() => {
      loadMoreButton.click();
    });

    // Verify isLoading is true during load
    await waitFor(() => {
      const messagesBlock = screen.getByTestId('dynamic-messagesblock');
      expect(messagesBlock).toHaveAttribute('data-is-loading', 'true');
    });

    // Fast-forward timers
    await act(async () => {
      jest.advanceTimersByTime(100);
    });

    // Verify isLoading is false after load
    await waitFor(() => {
      const messagesBlock = screen.getByTestId('dynamic-messagesblock');
      expect(messagesBlock).toHaveAttribute('data-is-loading', 'false');
    });
  });
});
