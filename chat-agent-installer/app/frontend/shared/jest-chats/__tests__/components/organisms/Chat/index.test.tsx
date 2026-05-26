import React from 'react';
import { screen, act, waitFor } from '@testing-library/react';
import {
  changeMessageVersion,
  getMessages,
  createMessage,
  createMessageVersion,
} from '@shared/ui/services/messages.services';
import { createChat, getChat } from '@shared/ui/services/chats.services';
import {
  transformToMessages,
  transformMessagesToObject,
} from '@shared/ui/utils/messages.utils';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { RoleEnum, ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import Chat from '@/components/organisms/Chat';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Mock the constants
jest.mock('@shared/ui/constants/common.constants', () => ({
  CHAT_MESSAGES_PAGE_SIZE: 20,
}));

// Mock XStream
jest.mock('@ant-design/x', () => ({
  XStream: jest.fn(),
}));

// Mock Next.js dynamic imports
jest.mock('next/dynamic', () => (importFunc: any) => {
  const DynamicComponent = React.forwardRef((props: any, ref: any) => {
    const componentName = importFunc.toString().includes('WelcomeBlock')
      ? 'WelcomeBlock'
      : importFunc.toString().includes('MessagesBlock')
        ? 'MessagesBlock'
        : importFunc.toString().includes('ChatSender')
          ? 'ChatSender'
          : importFunc.toString().includes('Result')
            ? 'Result'
            : importFunc.toString().includes('ChatSettings')
              ? 'ChatSettings'
              : 'DynamicComponent';

    const {
      componentRef,
      items,
      status,
      title,
      subTitle,
      children,
      onRequest,
      onLoadMore,
      activeChat,
      isLoading,
      ...domProps
    } = props;

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
        data-status={status}
        data-title={title}
        data-subtitle={subTitle}
        data-is-loading={isLoading}
        ref={ref}
        {...domProps}
      >
        {children}
        {items && <div data-testid='items-count'>{items.length}</div>}
        {items && items.length === 0 && (
          <div data-testid='no-items'>No items</div>
        )}
        {items && items.length > 0 && (
          <div data-testid='has-items'>Has items</div>
        )}
        {onRequest && (
          <button
            data-testid='trigger-request'
            onClick={() =>
              onRequest({
                content: 'test',
                attachments: [],
                selectedKey: ['1'],
              })
            }
          >
            Send
          </button>
        )}
        {onLoadMore && (
          <button
            data-testid='trigger-load-more'
            onClick={() => onLoadMore(false)}
          >
            Load More
          </button>
        )}
      </div>
    );
  });
  DynamicComponent.displayName = 'LoadableComponent';
  return DynamicComponent;
});

// Mock services and utils
jest.mock('@shared/ui/services/messages.services', () => ({
  changeMessageVersion: jest.fn(),
  getMessages: jest.fn(),
  createMessage: jest.fn(),
  createMessageVersion: jest.fn(),
}));

jest.mock('@shared/ui/services/chats.services', () => ({
  createChat: jest.fn(),
  getChat: jest.fn(),
}));

jest.mock('@shared/ui/utils/messages.utils', () => ({
  transformToMessages: jest.fn(),
  transformMessagesToObject: jest.fn(),
  handleMessageSend: jest.fn(),
}));

jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: jest.fn(),
}));

// Mock Redux
jest.mock('@shared/ui/store/chats/chats.slice', () => ({
  setActiveChat: jest.fn((payload) => ({
    type: 'chats/setActiveChat',
    payload,
  })),
  setAiTyping: jest.fn((payload) => ({
    type: 'chats/setAiTyping',
    payload,
  })),
  setChats: jest.fn((payload) => ({
    type: 'chats/setChats',
    payload,
  })),
  setTotalChats: jest.fn((payload) => ({
    type: 'chats/setTotalChats',
    payload,
  })),
  setHasMoreMessages: jest.fn((payload) => ({
    type: 'chats/setHasMoreMessages',
    payload,
  })),
  chatsReducer: (state = {}) => state,
}));

jest.mock('@shared/ui/store/chatsGroups/chatsGroups.slice', () => ({
  setActiveChatGroup: jest.fn((payload) => ({
    type: 'chatsGroups/setActiveChatGroup',
    payload,
  })),
  chatsGroupsReducer: (state = {}) => state,
}));

jest.mock('@shared/ui/store/settings/settings.slice', () => ({
  settingsReducer: (state = { themeMode: 'light', collapsedSidebar: false }) =>
    state,
}));

// Mock styled components
jest.mock('@/components/organisms/Chat/Chat.styled', () => ({
  StyledChatContainer: ({
    children,
    className,
    $hasMessages,
    $disabledByVault,
    ...props
  }: any) => (
    <div
      data-testid='styled-chat-container'
      className={className}
      data-has-messages={$hasMessages}
      data-disabled-by-vault={$disabledByVault}
      {...props}
    >
      {children}
    </div>
  ),
}));

// Import mocked functions
import {
  setActiveChat,
  setAiTyping,
  setChats,
  setTotalChats,
  setHasMoreMessages,
} from '@shared/ui/store/chats/chats.slice';
import { setActiveChatGroup } from '@shared/ui/store/chatsGroups/chatsGroups.slice';
import { XStream } from '@ant-design/x';
import { handleMessageSend } from '@shared/ui/utils/messages.utils';

const mockTransformToMessages = transformToMessages as jest.MockedFunction<
  typeof transformToMessages
>;
const mockTransformMessagesToObject =
  transformMessagesToObject as jest.MockedFunction<
    typeof transformMessagesToObject
  >;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;
const mockChangeMessageVersion = changeMessageVersion as jest.MockedFunction<
  typeof changeMessageVersion
>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;
const mockCreateMessage = createMessage as jest.MockedFunction<
  typeof createMessage
>;
const mockCreateMessageVersion = createMessageVersion as jest.MockedFunction<
  typeof createMessageVersion
>;
const mockCreateChat = createChat as jest.MockedFunction<typeof createChat>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockSetActiveChat = setActiveChat as jest.MockedFunction<
  typeof setActiveChat
>;
const mockSetAiTyping = setAiTyping as jest.MockedFunction<typeof setAiTyping>;
const mockSetChats = setChats as jest.MockedFunction<typeof setChats>;
const mockSetTotalChats = setTotalChats as jest.MockedFunction<
  typeof setTotalChats
>;
const mockSetHasMoreMessages = setHasMoreMessages as jest.MockedFunction<
  typeof setHasMoreMessages
>;
const mockSetActiveChatGroup = setActiveChatGroup as jest.MockedFunction<
  typeof setActiveChatGroup
>;
const mockXStream = XStream as jest.MockedFunction<typeof XStream>;
const mockHandleMessageSend = handleMessageSend as jest.MockedFunction<
  typeof handleMessageSend
>;

describe('Chat', () => {
  const mockHandleError = jest.fn();

  const defaultState = {
    settings: {
      themeMode: 'light' as const,
      collapsedSidebar: false,
    },
    chats: {
      chats: [],
      activeChat: {
        chat_id: 'chat-1',
        title: 'Test Chat',
        created_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-123',
        last_message_at: '2024-01-01T00:00:00Z',
        vault_mode: false,
        status: ChatStatusEnum.NORMAL,
        status_msg: null,
        group_id: null,
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
            edit: false,
            loading: false,
          },
          'msg-2': {
            content: {
              0: {
                type: MessageTypeEnum.TEXT,
                text: 'Hi there!',
              },
            },
            role: RoleEnum.ASSISTANT,
            version_count: 1,
            version_index: 0,
            attachments: [],
            edit: false,
            loading: false,
          },
        },
        active: true,
        favorite: false,
      },
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      hasMoreMessages: false,
      totalChats: 1,
    },
    chatsGroups: {
      activeChatGroup: 'all',
      groups: [],
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockTransformToMessages.mockReturnValue([
      {
        key: 'msg-1',
        content: 'Hello',
        role: 'user',
        variant: 'filled',
        edit: false,
        version_count: 1,
        version_index: 0,
      },
      {
        key: 'msg-2',
        content: 'Hi there!',
        variant: 'filled',
        role: 'assistant',
        edit: false,
        version_count: 1,
        version_index: 0,
      },
    ]);
    mockGetMessages.mockResolvedValue({
      docs: [],
      hasNextPage: false,
      totalDocs: 0,
      page: 1,
      totalPages: 1,
      limit: 20,
      nextPage: 1,
      prevPage: 1,
      hasPrevPage: false,
    });
    mockTransformMessagesToObject.mockReturnValue({});
    mockHandleMessageSend.mockResolvedValue(undefined);
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('renders chat with messages, sender and settings', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    expect(screen.getByTestId('styled-chat-container')).toBeInTheDocument();
    expect(screen.getByTestId('dynamic-messagesblock')).toBeInTheDocument();
    expect(screen.getByTestId('dynamic-chatsender')).toBeInTheDocument();
    expect(screen.getByTestId('dynamic-chatsettings')).toBeInTheDocument();
  });

  it('passes isLoading prop to MessagesBlock', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const messagesBlock = screen.getByTestId('dynamic-messagesblock');
    expect(messagesBlock).toHaveAttribute('data-is-loading', 'false');
  });

  it('does not render chat settings when there is only one message', async () => {
    const stateWithOneMessage = {
      ...defaultState,
      chats: {
        ...defaultState.chats,
        activeChat: {
          ...defaultState.chats.activeChat!,
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
              edit: false,
              loading: false,
            },
          },
        },
      },
    };
    const store = mockStore(stateWithOneMessage);

    mockTransformToMessages.mockReturnValue([
      {
        key: 'msg-1',
        content: 'Hello',
        variant: 'filled',
        edit: false,
        version_count: 1,
        version_index: 0,
        role: 'user',
      },
    ]);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    expect(screen.getByTestId('dynamic-messagesblock')).toBeInTheDocument();
    expect(screen.getByTestId('dynamic-chatsender')).toBeInTheDocument();
    expect(
      screen.queryByTestId('dynamic-chatsettings'),
    ).not.toBeInTheDocument();
  });

  it('shows access denied for vault chat when vault mode disabled', async () => {
    const vaultChatState = {
      ...defaultState,
      chats: {
        ...defaultState.chats,
        activeChat: {
          ...defaultState.chats.activeChat!,
          vault_mode: true,
        },
        vaultMode: false,
        vaultModeRegistered: false,
      },
    };
    const store = mockStore(vaultChatState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const resultComponent = screen.getByTestId('dynamic-result');
    expect(resultComponent).toBeInTheDocument();
    expect(resultComponent).toHaveAttribute('data-status', 'error');
    expect(resultComponent).toHaveAttribute('data-title', 'Access denied');
  });

  it('handles message version change successfully', async () => {
    const store = mockStore(defaultState);

    mockChangeMessageVersion.mockResolvedValue({
      active_message: {
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Updated',
            },
          },
          role: RoleEnum.USER,
          version_count: 2,
          version_index: 1,
          attachments: [],
          edit: false,
          loading: false,
        },
      },
      branched_history: {
        // @ts-ignore
        'msg-1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Updated',
            },
          },
          role: RoleEnum.USER,
          version_count: 2,
          version_index: 1,
          attachments: [],
          edit: false,
          loading: false,
        },
      },
    });

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const transformCall = mockTransformToMessages.mock.calls[0][0];
    const onChangeVersion = transformCall.onChangeVersion;

    await act(async () => {
      await onChangeVersion({ message_id: 'msg-1', version_index: 1 });
    });

    expect(mockChangeMessageVersion).toHaveBeenCalledWith({
      message_id: 'msg-1',
      chat_id: 'chat-1',
      version_index: 1,
    });
    expect(mockSetActiveChat).toHaveBeenCalled();
  });

  it('handles load more messages', async () => {
    const store = mockStore(defaultState);

    mockGetMessages.mockResolvedValue({
      docs: [
        {
          message_id: 'msg-0',
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Older message',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          attachments: [],
        },
      ],
      hasNextPage: true,
      totalDocs: 3,
      page: 2,
      totalPages: 2,
      limit: 20,
      hasPrevPage: true,
      nextPage: 2,
      prevPage: 1,
    });

    mockTransformMessagesToObject.mockReturnValue({
      'msg-0': {
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Older message',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        attachments: [],
      },
    });

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const loadMoreButton = screen.getByTestId('trigger-load-more');

    await act(async () => {
      loadMoreButton.click();
    });

    await waitFor(() => {
      expect(mockGetMessages).toHaveBeenCalledWith({
        chat_id: 'chat-1',
        page: 2,
        limit: 20,
      });
      expect(mockSetHasMoreMessages).toHaveBeenCalledWith(true);
    });
  });

  it('sets loading state during load more', async () => {
    const store = mockStore(defaultState);

    mockGetMessages.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              docs: [],
              hasNextPage: false,
              totalDocs: 0,
              page: 2,
              totalPages: 1,
              limit: 20,
              nextPage: 2,
              prevPage: 1,
              hasPrevPage: true,
            });
          }, 100);
        }),
    );

    await act(async () => {
      renderLayout(<Chat />, { store });
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

  it('handles sending message via ChatSender', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const sendButton = screen.getByTestId('trigger-request');

    await act(async () => {
      sendButton.click();
    });

    await waitFor(() => {
      expect(mockHandleMessageSend).toHaveBeenCalledWith(
        expect.objectContaining({
          content: 'test',
          attachments: [],
          selectedKey: ['1'],
          activeChat: defaultState.chats.activeChat,
          chats: defaultState.chats.chats,
          totalChats: defaultState.chats.totalChats,
        }),
      );
    });
  });

  it('handles toggle edit functionality', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const transformCall = mockTransformToMessages.mock.calls[0][0];
    const onToggleEdit = transformCall.onToggleEdit;

    await act(async () => {
      onToggleEdit('msg-1');
    });

    expect(mockSetActiveChat).toHaveBeenCalledWith(
      expect.objectContaining({
        chat_id: 'chat-1',
        messages: expect.objectContaining({
          'msg-1': expect.objectContaining({ edit: true }),
          'msg-2': expect.objectContaining({ edit: false }),
        }),
      }),
    );
  });

  it('handles cancel edit functionality', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const transformCall = mockTransformToMessages.mock.calls[0][0];
    const onCancelEdit = transformCall.onCancelEdit;

    await act(async () => {
      onCancelEdit('msg-1');
    });

    expect(mockSetActiveChat).toHaveBeenCalledWith(
      expect.objectContaining({
        chat_id: 'chat-1',
        messages: expect.objectContaining({
          'msg-1': expect.objectContaining({ edit: false }),
          'msg-2': expect.objectContaining({ edit: false }),
        }),
      }),
    );
  });

  it('renders welcome block when no messages', async () => {
    const stateWithoutMessages = {
      ...defaultState,
      chats: {
        ...defaultState.chats,
        activeChat: {
          ...defaultState.chats.activeChat!,
          messages: {},
        },
      },
    };
    const store = mockStore(stateWithoutMessages);

    mockTransformToMessages.mockReturnValue([]);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    expect(screen.getByTestId('items-count')).toHaveTextContent('1');
  });

  it('handles readonly chat status', async () => {
    const readonlyChatState = {
      ...defaultState,
      chats: {
        ...defaultState.chats,
        activeChat: {
          ...defaultState.chats.activeChat!,
          status: ChatStatusEnum.READONLY,
          status_msg: 'This chat is read-only',
        },
      },
    };
    const store = mockStore(readonlyChatState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    expect(mockTransformToMessages).toHaveBeenCalledWith({
      messages: expect.any(Object),
      refInput: expect.any(Object),
      onToggleEdit: expect.any(Function),
      onChangeVersion: expect.any(Function),
      onCancelEdit: expect.any(Function),
      onSaveEdit: expect.any(Function),
      readyOnlyChat: true,
      statusMessage: 'This chat is read-only',
    });
  });

  it('memoizes items to prevent unnecessary re-renders', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<Chat />, { store });
    });

    const firstCallCount = mockTransformToMessages.mock.calls.length;

    // Trigger a re-render without changing relevant dependencies
    await act(async () => {
      store.dispatch(setAiTyping(false));
    });

    // transformToMessages should not be called again
    expect(mockTransformToMessages.mock.calls.length).toBe(firstCallCount);
  });
});
