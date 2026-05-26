import React from 'react';
import { screen, fireEvent, act, waitFor } from '@testing-library/react';

import CustomSidebarChats from '@/components/molecules/Sidebars/CustomSidebarChats';
import {
  deleteChat,
  getChat,
  updateChat,
} from '@shared/ui/services/chats.services';
import { getMessages } from '@shared/ui/services/messages.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import useClickOutside from '@shared/ui/hooks/useClickOutside.hook';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';

// Mock EmptyChats component
jest.mock('@/components/molecules/Empty/EmptyChats', () => ({
  __esModule: true,
  default: function EmptyChats() {
    return <div data-testid='empty-chats'>No chats available</div>;
  },
}));

// Mock VaultModeWarningModal
jest.mock(
  '@/components/molecules/Modals/VaultMode/VaultModeWarningModal',
  () => ({
    __esModule: true,
    default: function VaultModeWarningModal({ open, onCancel }: any) {
      return open ? (
        <div data-testid='vault-mode-warning-modal'>
          <button data-testid='vault-modal-cancel' onClick={onCancel}>
            Close
          </button>
        </div>
      ) : null;
    },
  }),
);

// Mock FavoriteIcon component
jest.mock('@/components/atoms/Icons/FavoriteIcon', () => {
  const MockFavoriteIcon = ({ active }: { active: boolean }) => (
    <span data-testid={`favorite-icon-${active}`}>FavoriteIcon</span>
  );
  MockFavoriteIcon.displayName = 'MockFavoriteIcon';
  return MockFavoriteIcon;
});

// Mock Ant Design X components
// Update the Conversations mock
jest.mock('@ant-design/x', () => ({
  Conversations: ({
    items,
    onActiveChange,
    menu,
    activeKey,
    groupable, // Extract this so it doesn't get passed to DOM
    ...props
  }: any) => {
    const [editingItem, setEditingItem] = React.useState<string | null>(null);

    return (
      <div data-testid='conversations' {...props}>
        {items?.map((item: any) => (
          <div
            key={item.key}
            data-testid={`chat-item-${item.key}`}
            data-active={activeKey === item.key}
            onClick={() => onActiveChange?.(item.key)}
            className={item.disabledByVault ? 'disabled' : ''}
          >
            {editingItem === item.key ? (
              <input
                data-testid='input'
                defaultValue={
                  typeof item.label === 'string' ? item.label : item.title
                }
                onBlur={() => setEditingItem(null)}
              />
            ) : (
              <span>
                {typeof item.label === 'string' ? item.label : item.title}
              </span>
            )}
            <div data-testid={`group-${item.key}`}>{item.group}</div>
            <div data-testid={`status-${item.key}`}>{item.status}</div>
            <div data-testid={`icon-${item.key}`}>{item.icon}</div>
            <button
              data-testid={`menu-${item.key}`}
              onClick={(e) => {
                e.stopPropagation();
                setEditingItem(item.key);
                const menuConfig = menu(item);
                if (menuConfig?.onClick) {
                  menuConfig.onClick({ key: 'edit' });
                }
              }}
            >
              Menu
            </button>
            <button
              data-testid={`favorite-${item.key}`}
              onClick={(e) => {
                e.stopPropagation();
                const menuConfig = menu(item);
                if (menuConfig?.onClick) {
                  menuConfig.onClick({ key: 'favorite' });
                }
              }}
            >
              Favorite
            </button>
            <button
              data-testid={`add-to-group-${item.key}`}
              onClick={(e) => {
                e.stopPropagation();
                const menuConfig = menu(item);
                if (menuConfig?.onClick) {
                  menuConfig.onClick({ key: 'addToGroup' });
                }
              }}
            >
              Add to Group
            </button>
            <button
              data-testid={`delete-${item.key}`}
              onClick={(e) => {
                e.stopPropagation();
                const menuConfig = menu(item);
                if (menuConfig?.onClick) {
                  menuConfig.onClick({ key: 'delete' });
                }
              }}
            >
              Delete
            </button>
          </div>
        ))}
      </div>
    );
  },
}));

// Mock dependencies
jest.mock('@shared/ui/services/chats.services', () => ({
  deleteChat: jest.fn().mockResolvedValue({ chat_id: '1' }),
  getChat: jest.fn(),
  updateChat: jest.fn(),
}));

jest.mock('@shared/ui/services/messages.services', () => ({
  getMessages: jest.fn(),
}));

jest.mock('@shared/ui/hooks/useHandleError.hook');
jest.mock('@shared/ui/hooks/useClickOutside.hook');

// Mock utils
jest.mock('@/utils/chats.utils', () => ({
  defineGroup: jest.fn().mockReturnValue('Today'),
  sortChats: jest.fn().mockImplementation((chats) => chats),
}));

jest.mock('@shared/ui/utils/messages.utils', () => ({
  groupable: jest.fn().mockReturnValue(true),
  transformMessagesToObject: jest.fn((docs) => {
    return docs.reduce((acc: any, doc: any) => {
      acc[doc.message_id] = doc;
      return acc;
    }, {});
  }),
}));

// Mock react-infinite-scroll-component
jest.mock('react-infinite-scroll-component', () => {
  const MockInfiniteScroll = ({
    children,
    loader,
    hasMore,
    next,
    scrollableTarget,
    dataLength,
  }: any) => (
    <div
      data-testid='infinite-scroll'
      data-scrollable-target={scrollableTarget}
      data-data-length={dataLength}
    >
      {children}
      {hasMore && (
        <div data-testid='load-more' onClick={next}>
          {loader}
        </div>
      )}
    </div>
  );
  MockInfiniteScroll.displayName = 'MockInfiniteScroll';
  return MockInfiniteScroll;
});

// Mock styled components
jest.mock(
  '@/components/molecules/Sidebars/CustomSidebarChats/CustomSidebarChats.styled',
  () => ({
    StyledConversations: ({ children, ...props }: any) => {
      const { Conversations } = require('@ant-design/x');
      return (
        <div data-testid='styled-conversations' className='ant-conversations'>
          <Conversations {...props}>{children}</Conversations>
        </div>
      );
    },
    StyledSidebarBody: React.forwardRef(({ children, ...props }: any, ref) => (
      <div
        ref={ref}
        data-testid='styled-sidebar-body'
        className='custom-sidebar-chats'
        {...props}
      >
        {children}
      </div>
    )),
  }),
);

// Mock Ant Design components
const mockMessage = {
  success: jest.fn(),
  error: jest.fn(),
};

jest.mock('antd', () => {
  const originalAntd = jest.requireActual('antd');
  return {
    ...originalAntd,
    App: {
      ...originalAntd.App,
      useApp: () => ({
        message: mockMessage,
      }),
    },
    Modal: ({
      open,
      onOk,
      onCancel,
      children,
      title,
      okType,
      okText,
      cancelText,
      loading,
      modalRender,
    }: any) => {
      if (!open) return null;

      if (modalRender) {
        return modalRender(
          <div data-testid='modal'>
            <div data-testid='modal-title'>{title}</div>
            <div data-testid='modal-content'>{children}</div>
            <button
              data-testid='modal-ok'
              type='submit'
              disabled={loading}
              className={okType === 'danger' ? 'danger-button' : ''}
            >
              {okText || 'OK'}
            </button>
            <button
              data-testid='modal-cancel'
              onClick={onCancel}
              disabled={loading}
            >
              {cancelText || 'Cancel'}
            </button>
          </div>,
        );
      }

      return (
        <div data-testid='modal'>
          <div data-testid='modal-title'>{title}</div>
          <div data-testid='modal-content'>{children}</div>
          <button
            data-testid='modal-ok'
            onClick={onOk}
            disabled={loading}
            className={okType === 'danger' ? 'danger-button' : ''}
          >
            {okText || 'OK'}
          </button>
          <button
            data-testid='modal-cancel'
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText || 'Cancel'}
          </button>
        </div>
      );
    },
    Form: Object.assign(
      ({ children, onFinish, form, layout, scrollToFirstError }: any) => (
        <form
          data-testid='form'
          onSubmit={(e) => {
            e.preventDefault();
            onFinish?.();
          }}
        >
          {children}
        </form>
      ),
      {
        Item: ({ children, label, name, normalize }: any) => (
          <div data-testid={`form-item-${name}`}>
            {label && <label>{label}</label>}
            {children}
          </div>
        ),
        useForm: () => [
          {
            setFieldValue: jest.fn(),
            validateFields: jest
              .fn()
              .mockResolvedValue({ group_id: 'group-1' }),
          },
        ],
      },
    ),

    Input: React.forwardRef<any, any>(({ defaultValue, ...props }, ref) => (
      <input
        data-testid='input'
        ref={ref}
        defaultValue={defaultValue}
        {...props}
      />
    )),
    // Update the Select mock - don't spread props
    Select: ({
      options,
      value,
      onChange,
      showSearch,
      optionFilterProp,
    }: any) => (
      <select
        data-testid='select'
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
      >
        {options?.map((opt: any) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    ),

    Spin: ({ indicator, size }: any) => (
      <div data-testid='spin' data-size={size}>
        {indicator}
      </div>
    ),
  };
});

// Set display name for Input component
(jest.mocked(require('antd')).Input as any).displayName = 'MockInput';

// Mock Ant Design icons
jest.mock('@ant-design/icons', () => ({
  DeleteOutlined: () => <span data-testid='delete-icon'>DeleteIcon</span>,
  EditOutlined: () => <span data-testid='edit-icon'>EditIcon</span>,
  DoubleRightOutlined: () => (
    <span data-testid='double-right-icon'>DoubleRightIcon</span>
  ),
  RedoOutlined: ({ spin }: any) => (
    <span data-testid='redo-icon' data-spin={spin}>
      RedoIcon
    </span>
  ),
}));

const mockDeleteChat = deleteChat as jest.MockedFunction<typeof deleteChat>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;
const mockUpdateChat = updateChat as jest.MockedFunction<typeof updateChat>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;
const mockUseClickOutside = useClickOutside as jest.MockedFunction<
  typeof useClickOutside
>;

describe('CustomSidebarChats', () => {
  const mockHandleError = jest.fn();
  const mockOnLoadMore = jest.fn();

  const defaultUser = {
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    last_release_date: null,
  };

  const defaultState: Partial<RootStore> = {
    chats: {
      hasMoreMessages: false,
      chats: [
        {
          chat_id: '1',
          title: 'Chat 1',
          created_at: '2024-01-01T00:00:00Z',
          owner_id: 'user-123',
          last_message_at: '2024-01-01T00:00:00Z',
          vault_mode: false,
          messages: {},
          active: true,
          favorite: false,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
          group_id: null,
        },
        {
          chat_id: '2',
          title: 'Chat 2',
          created_at: '2024-01-02T00:00:00Z',
          owner_id: 'user-123',
          last_message_at: '2024-01-02T00:00:00Z',
          vault_mode: true,
          messages: {},
          active: false,
          favorite: true,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
          group_id: null,
        },
      ],
      activeChat: {
        chat_id: '1',
        title: 'Chat 1',
        created_at: '2024-01-01T00:00:00Z',
        owner_id: 'user-123',
        last_message_at: '2024-01-01T00:00:00Z',
        vault_mode: false,
        messages: {},
        active: true,
        favorite: false,
        status: ChatStatusEnum.NORMAL,
        status_msg: null,
        group_id: null,
      },
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: true,
      totalChats: 2,
    },
    settings: {
      user: defaultUser,
      releases: [],
      showReleaseModal: false,
      themeMode: 'light',
      collapsedSidebar: false,
      hasMoreReleases: false,
    },
    chatsGroups: {
      chatsGroups: [
        {
          group_id: 'group-1',
          title: 'Work',
        },
      ],
      activeChatGroup: null,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockUseClickOutside.mockImplementation((ref, callback) => {
      (ref as any).clickOutsideCallback = callback;
    });

    mockDeleteChat.mockResolvedValue({ chat_id: '1' });

    mockGetChat.mockResolvedValue({
      chat_id: '2',
      title: 'Chat 2',
      created_at: '2024-01-02T00:00:00Z',
      owner_id: 'user-123',
      last_message_at: '2024-01-02T00:00:00Z',
      vault_mode: false,
      messages: {
        '1': {
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Test message',
            },
          },
          role: RoleEnum.USER,
          version_count: 1,
          version_index: 0,
          created_at: '2024-01-02T00:00:00Z',
          attachments: [],
          edit: false,
          loading: false,
        },
      },
      active: false,
      favorite: false,
      status: ChatStatusEnum.NORMAL,
      status_msg: null,
      group_id: null,
    });

    mockGetMessages.mockResolvedValue({
      docs: [
        {
          message_id: 'msg-1',
          content: {
            0: {
              type: MessageTypeEnum.TEXT,
              text: 'Test message',
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
      limit: CHAT_MESSAGES_PAGE_SIZE,
      page: 1,
      totalPages: 1,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 1,
    });

    mockUpdateChat.mockResolvedValue({
      chat_id: '1',
      title: 'Updated Chat',
      created_at: '2024-01-01T00:00:00Z',
      owner_id: 'user-123',
      last_message_at: '2024-01-01T00:00:00Z',
      vault_mode: false,
      messages: {},
      active: true,
      favorite: false,
      status: ChatStatusEnum.NORMAL,
      status_msg: null,
      group_id: null,
    });
  });

  describe('Basic Rendering', () => {
    it('renders sidebar with basic structure', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.getByTestId('styled-sidebar-body')).toBeInTheDocument();
      expect(screen.getByTestId('infinite-scroll')).toBeInTheDocument();
      expect(screen.getByTestId('styled-conversations')).toBeInTheDocument();
      expect(screen.getByTestId('conversations')).toBeInTheDocument();
    });

    it('renders chat items with all required elements', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.getByText('Chat 1')).toBeInTheDocument();
      expect(screen.getByText('Chat 2')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-2')).toBeInTheDocument();

      expect(screen.getByTestId('group-1')).toBeInTheDocument();
      expect(screen.getByTestId('group-2')).toBeInTheDocument();

      expect(screen.getByTestId('status-1')).toBeInTheDocument();
      expect(screen.getByTestId('status-2')).toBeInTheDocument();

      expect(screen.getByTestId('icon-1')).toBeInTheDocument();
      expect(screen.getByTestId('icon-2')).toBeInTheDocument();
    });

    it('renders with custom className and props', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(
          <CustomSidebarChats
            onLoadMore={mockOnLoadMore}
            className='custom-class'
            data-custom='test'
          />,
          { store },
        );
      });

      const sidebar = screen.getByTestId('styled-sidebar-body');
      expect(sidebar).toHaveClass('custom-sidebar-chats');
      expect(sidebar).toHaveAttribute('data-custom', 'test');
    });

    it('renders correctly with no chats', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          chats: [],
          activeChat: null,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.getByTestId('styled-sidebar-body')).toBeInTheDocument();
      expect(screen.getByTestId('empty-chats')).toBeInTheDocument();
      expect(screen.queryByTestId('conversations')).not.toBeInTheDocument();
    });
  });

  describe('Infinite Scroll', () => {
    it('configures infinite scroll correctly', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const infiniteScroll = screen.getByTestId('infinite-scroll');
      expect(infiniteScroll).toHaveAttribute(
        'data-scrollable-target',
        'sidebar-body',
      );
      expect(infiniteScroll).toHaveAttribute('data-data-length', '2');
    });

    it('shows load more with spinner when hasMoreChats is true', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.getByTestId('load-more')).toBeInTheDocument();
      expect(screen.getByTestId('spin')).toBeInTheDocument();
      expect(screen.getByTestId('redo-icon')).toBeInTheDocument();
    });

    it('calls onLoadMore when load more is clicked', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const loadMore = screen.getByTestId('load-more');
        fireEvent.click(loadMore);
      });

      expect(mockOnLoadMore).toHaveBeenCalled();
    });

    it('does not show load more when hasMoreChats is false', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          hasMoreChats: false,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.queryByTestId('load-more')).not.toBeInTheDocument();
    });
  });

  describe('Chat Selection', () => {
    it('handles chat selection successfully for non-vault chat', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const chatItem = screen.getByTestId('chat-item-1');
        fireEvent.click(chatItem);
      });

      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '1',
        favorite: false,
        active: true,
        title: 'Chat 1',
        group_id: null,
      });
      expect(mockGetChat).toHaveBeenCalledWith({ id: '1' });
      expect(mockGetMessages).toHaveBeenCalledWith({
        chat_id: '1',
        page: 1,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });
    });

    it('shows active chat correctly', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const activeChat = screen.getByTestId('chat-item-1');
      expect(activeChat).toHaveAttribute('data-active', 'true');

      const inactiveChat = screen.getByTestId('chat-item-2');
      expect(inactiveChat).toHaveAttribute('data-active', 'false');
    });

    it('prevents chat selection when AI is typing', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          aiTyping: true,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const chatItem = screen.getByTestId('chat-item-1');
        fireEvent.click(chatItem);
      });

      expect(mockMessage.error).toHaveBeenCalledWith(
        'Before doing this action, please, wait until the assistant will finish generating the message',
      );
      expect(mockUpdateChat).not.toHaveBeenCalled();
    });

    it('shows vault mode warning for vault chats when vault mode is disabled', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const vaultChat = screen.getByTestId('chat-item-2');
        fireEvent.click(vaultChat);
      });

      expect(
        screen.getByTestId('vault-mode-warning-modal'),
      ).toBeInTheDocument();
      expect(mockUpdateChat).not.toHaveBeenCalled();
    });

    it('handles vault chat selection when vault mode is enabled', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const vaultChat = screen.getByTestId('chat-item-2');
        fireEvent.click(vaultChat);
      });

      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '2',
        favorite: true,
        active: true,
        title: 'Chat 2',
        group_id: null,
      });
      expect(mockGetChat).toHaveBeenCalledWith({ id: '2' });
    });
  });

  describe('Vault Mode', () => {
    it('disables vault chats when vault mode is not enabled', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          vaultMode: false,
          vaultModeRegistered: false,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const vaultChat = screen.getByTestId('chat-item-2');
      expect(vaultChat).toHaveClass('disabled');
    });

    it('enables vault chats when vault mode is enabled', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const vaultChat = screen.getByTestId('chat-item-2');
      expect(vaultChat).not.toHaveClass('disabled');
    });
  });

  describe('Menu Actions', () => {
    it('handles favorite toggle successfully for non-vault chat', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-1');
        fireEvent.click(favoriteButton);
      });

      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '1',
        favorite: true,
        active: true,
        title: 'Chat 1',
        group_id: null,
      });
      expect(mockMessage.success).toHaveBeenCalledWith(
        'The chat "Chat 1" has successfully added to the favorite list',
      );
    });

    it('handles unfavorite successfully for vault chat when vault mode is enabled', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-2');
        fireEvent.click(favoriteButton);
      });

      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '2',
        favorite: false,
        active: false,
        title: 'Chat 2',
        group_id: null,
      });
      expect(mockMessage.success).toHaveBeenCalledWith(
        'The chat "Chat 2" has successfully deleted from the favorite list',
      );
    });

    it('prevents menu actions when AI is typing', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          aiTyping: true,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-1');
        fireEvent.click(favoriteButton);
      });

      expect(mockMessage.error).toHaveBeenCalledWith(
        'Before doing this action, please, wait until the assistant will finish generating the message',
      );
      expect(mockUpdateChat).not.toHaveBeenCalled();
    });

    it('prevents menu actions for readonly chats', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          chats: [
            {
              ...defaultState.chats!.chats[0],
              status: ChatStatusEnum.READONLY,
            },
            ...defaultState.chats!.chats.slice(1),
          ],
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-1');
        fireEvent.click(favoriteButton);
      });

      expect(mockMessage.error).toHaveBeenCalledWith(
        'This chat has the "read only" status. Please, choose another chat.',
      );
      expect(mockUpdateChat).not.toHaveBeenCalled();
    });

    it('shows vault mode warning for vault chat menu actions when vault mode is disabled', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-2');
        fireEvent.click(favoriteButton);
      });

      expect(
        screen.getByTestId('vault-mode-warning-modal'),
      ).toBeInTheDocument();
      expect(mockUpdateChat).not.toHaveBeenCalled();
    });
  });

  describe('Delete Chat', () => {
    it('opens delete confirmation modal', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const deleteButton = screen.getByTestId('delete-1');
        fireEvent.click(deleteButton);
      });

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent(
        'Delete chat?',
      );
    });

    it('cancels delete when cancel is clicked', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const deleteButton = screen.getByTestId('delete-1');
        fireEvent.click(deleteButton);
      });

      await act(async () => {
        const cancelButton = screen.getByTestId('modal-cancel');
        fireEvent.click(cancelButton);
      });

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
      expect(mockDeleteChat).not.toHaveBeenCalled();
    });

    it('handles delete error gracefully', async () => {
      mockDeleteChat.mockRejectedValueOnce(new Error('Delete failed'));
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const deleteButton = screen.getByTestId('delete-1');
        fireEvent.click(deleteButton);
      });

      await act(async () => {
        const okButton = screen.getByTestId('modal-ok');
        fireEvent.click(okButton);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          new Error('Delete failed'),
        );
      });
    });
  });

  describe('Edit Chat Title', () => {
    it('shows input field when edit is clicked', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const menuButton = screen.getByTestId('menu-1');
        fireEvent.click(menuButton);
      });

      expect(screen.getByTestId('input')).toBeInTheDocument();
    });

    it('updates title when clicking outside', async () => {
      let clickOutsideCallback: ((event: MouseEvent) => void) | undefined;
      mockUseClickOutside.mockImplementation((ref, callback) => {
        clickOutsideCallback = callback;
        (ref as any).current = {
          nativeElement: {
            value: 'Updated Chat Title',
          },
        };
      });

      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const menuButton = screen.getByTestId('menu-1');
        fireEvent.click(menuButton);
      });

      await act(async () => {
        if (clickOutsideCallback) {
          clickOutsideCallback(new MouseEvent('mousedown'));
        }
      });

      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '1',
        favorite: false,
        active: true,
        group_id: null,
        title: 'Updated Chat Title',
      });
      expect(mockMessage.success).toHaveBeenCalledWith(
        "The chat's title has successfully updated",
      );
    });
  });

  describe('Add to Group', () => {
    it('opens migration modal when add to group is clicked', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const addToGroupButton = screen.getByTestId('add-to-group-1');
        fireEvent.click(addToGroupButton);
      });

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent(
        'Move chat to the group',
      );
      expect(screen.getByTestId('form-item-group_id')).toBeInTheDocument();
      expect(screen.getByTestId('select')).toBeInTheDocument();
    });

    it('handles group migration successfully', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const addToGroupButton = screen.getByTestId('add-to-group-1');
        fireEvent.click(addToGroupButton);
      });

      await act(async () => {
        const form = screen.getByTestId('form');
        fireEvent.submit(form);
      });

      await waitFor(() => {
        expect(mockUpdateChat).toHaveBeenCalledWith({
          id: '1',
          favorite: false,
          active: true,
          title: 'Chat 1',
          group_id: 'group-1',
        });
        expect(mockMessage.success).toHaveBeenCalledWith(
          'The chat has successfully moved to the group',
        );
      });
    });

    it('cancels migration when cancel is clicked', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const addToGroupButton = screen.getByTestId('add-to-group-1');
        fireEvent.click(addToGroupButton);
      });

      await act(async () => {
        const cancelButton = screen.getByTestId('modal-cancel');
        fireEvent.click(cancelButton);
      });

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles chat selection error', async () => {
      mockUpdateChat.mockRejectedValueOnce(new Error('Update failed'));
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const chatItem = screen.getByTestId('chat-item-1');
        fireEvent.click(chatItem);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          new Error('Update failed'),
        );
      });
    });

    it('handles favorite toggle error', async () => {
      mockUpdateChat.mockRejectedValueOnce(new Error('Favorite failed'));
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const favoriteButton = screen.getByTestId('favorite-1');
        fireEvent.click(favoriteButton);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(
          new Error('Favorite failed'),
        );
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles null activeChat gracefully', async () => {
      const state = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          activeChat: null,
        },
      };
      const store = mockStore(state, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      expect(screen.getByTestId('styled-conversations')).toBeInTheDocument();
      expect(screen.getByText('Chat 1')).toBeInTheDocument();
      expect(screen.getByText('Chat 2')).toBeInTheDocument();
    });

    it('handles empty title update gracefully', async () => {
      let clickOutsideCallback: ((event: MouseEvent) => void) | undefined;
      mockUseClickOutside.mockImplementation((ref, callback) => {
        clickOutsideCallback = callback;
        (ref as any).current = {
          nativeElement: {
            value: '',
          },
        };
      });

      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      await act(async () => {
        const menuButton = screen.getByTestId('menu-1');
        fireEvent.click(menuButton);
      });

      await act(async () => {
        if (clickOutsideCallback) {
          clickOutsideCallback(new MouseEvent('mousedown'));
        }
      });

      expect(mockUpdateChat).not.toHaveBeenCalled();
    });

    it('applies ant-conversations class to styled component', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const styledConversations = screen.getByTestId('styled-conversations');
      expect(styledConversations).toHaveClass('ant-conversations');
    });

    it('renders sidebar body with correct id', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const sidebarBody = screen.getByTestId('styled-sidebar-body');
      expect(sidebarBody).toHaveAttribute('id', 'sidebar-body');
    });
  });

  describe('Groupable and Utils Integration', () => {
    it('passes groupable configuration to Conversations', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const { groupable } = require('@shared/ui/utils/messages.utils');
      expect(groupable).toHaveBeenCalled();
    });

    it('uses defineGroup and sortChats utilities', async () => {
      const store = mockStore(defaultState, { serializableCheck: false });

      await act(async () => {
        renderLayout(<CustomSidebarChats onLoadMore={mockOnLoadMore} />, {
          store,
        });
      });

      const { defineGroup, sortChats } = require('@/utils/chats.utils');
      expect(defineGroup).toHaveBeenCalled();
      expect(sortChats).toHaveBeenCalled();
    });
  });
});
