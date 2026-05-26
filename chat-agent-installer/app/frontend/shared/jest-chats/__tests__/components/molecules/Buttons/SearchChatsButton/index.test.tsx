import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import SearchChatsButton from '@/components/molecules/Buttons/SearchChatsButton';
import {
  getChat,
  getChats,
  updateChat,
} from '@shared/ui/services/chats.services';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { CHATS_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { ChatType } from '@shared/ui/types/chats.types';
import { PaginationType } from '@shared/ui/types/pagination.types';

// Mock services
jest.mock('@shared/ui/services/chats.services', () => ({
  getChats: jest.fn(),
  getChat: jest.fn(),
  updateChat: jest.fn(),
}));

// Mock hooks
jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: () => jest.fn(),
}));

// Mock debounce to execute immediately but track calls
let debouncedCallback: any = null;
jest.mock('@shared/ui/hooks/useDebounceCallback.hook', () => ({
  __esModule: true,
  default: (callback: any, delay: number) => {
    debouncedCallback = callback;
    return callback;
  },
}));

// Mock usePrevious to properly return previous value
let previousValue: any = null;
jest.mock('@shared/ui/hooks/usePrevious.hook', () => ({
  __esModule: true,
  default: (value: any) => {
    const prev = previousValue;
    previousValue = value;
    return prev;
  },
}));

// Mock utils
jest.mock('@/utils/chats.utils', () => ({
  defineGroup: jest.fn(() => 'today'),
  sortChats: jest.fn((chats) => chats),
}));

// Mock child components
jest.mock('@/components/molecules/Modals/SearchModal', () => ({
  __esModule: true,
  default: ({
    open,
    items,
    hasMoreData,
    activeKey,
    onActiveKeyChange,
    onCancel,
    onSearchChange,
    onLoadMore,
    customSearchPlaceholder,
  }: any) =>
    open ? (
      <div data-testid='search-modal'>
        <input
          data-testid='search-input'
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={customSearchPlaceholder}
        />
        <div data-testid='items-count'>{items.length}</div>
        <button data-testid='load-more' onClick={() => onLoadMore(false)}>
          Load More
        </button>
        {items.map((item: any) => (
          <div
            key={item.key}
            data-testid={`chat-item-${item.key}`}
            onClick={() => onActiveKeyChange(item.key)}
            data-active={item.key === activeKey}
            data-disabled-by-vault={item.disabledByVault}
          >
            {item.label}
            {item.icon}
          </div>
        ))}
        <button data-testid='close-modal' onClick={onCancel}>
          Close
        </button>
        {hasMoreData && <div data-testid='has-more'>Has More</div>}
      </div>
    ) : null,
}));

jest.mock(
  '@/components/molecules/Modals/VaultMode/VaultModeWarningModal',
  () => ({
    __esModule: true,
    default: ({ open, onCancel }: any) =>
      open ? (
        <div data-testid='vault-warning-modal'>
          <button data-testid='close-vault-warning' onClick={onCancel}>
            Close
          </button>
        </div>
      ) : null,
  }),
);

jest.mock('@/components/atoms/Icons/FavoriteIcon', () => ({
  __esModule: true,
  default: ({ active }: any) => (
    <span data-testid={`favorite-icon-${active}`}>Favorite</span>
  ),
}));

jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => ({
  __esModule: true,
  default: ({ onClick, icon, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {icon}
    </button>
  ),
}));

// Mock Ant Design
jest.mock('antd', () => ({
  Tooltip: ({ children, title }: any) => (
    <div data-testid='tooltip' data-title={title}>
      {children}
    </div>
  ),
}));

// Mock icons
jest.mock('@ant-design/icons', () => ({
  SearchOutlined: () => (
    <span className='anticon-search' data-testid='search-icon'>
      Search
    </span>
  ),
}));

const mockGetChats = getChats as jest.MockedFunction<typeof getChats>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockUpdateChat = updateChat as jest.MockedFunction<typeof updateChat>;

describe('SearchChatsButton Component', () => {
  const createMockPagination = (
    docs: ChatType[],
    hasNextPage: boolean = false,
    page: number = 1,
  ): PaginationType<ChatType> & { active_chat_id?: string } => ({
    docs,
    totalDocs: docs.length,
    limit: CHATS_PAGE_SIZE,
    page,
    totalPages: Math.ceil(docs.length / CHATS_PAGE_SIZE),
    hasNextPage,
    nextPage: hasNextPage ? page + 1 : page,
    hasPrevPage: page > 1,
    prevPage: page > 1 ? page - 1 : page,
  });

  const mockChats: ChatType[] = [
    {
      chat_id: '1',
      title: 'Chat 1',
      vault_mode: false,
      favorite: false,
      active: false,
      last_message_at: new Date().toISOString(),
      status: ChatStatusEnum.NORMAL,
      created_at: new Date().toISOString(),
      owner_id: 'user1',
      messages: {},
      status_msg: null,
      group_id: null,
    },
    {
      chat_id: '2',
      title: 'Chat 2',
      vault_mode: false,
      favorite: true,
      active: false,
      last_message_at: new Date().toISOString(),
      status: ChatStatusEnum.NORMAL,
      created_at: new Date().toISOString(),
      owner_id: 'user1',
      messages: {},
      status_msg: null,
      group_id: null,
    },
  ];

  const initialState: Partial<RootStore> = {
    chats: {
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      hasMoreMessages: false,
      totalChats: 0,
    },
    chatsGroups: {
      chatsGroups: [],
      activeChatGroup: null,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    previousValue = null;
    mockGetChats.mockResolvedValue(createMockPagination(mockChats));
    mockGetChat.mockResolvedValue({
      chat_id: '1',
      title: 'Chat 1',
      vault_mode: false,
      favorite: false,
      active: true,
      last_message_at: new Date().toISOString(),
      status: ChatStatusEnum.NORMAL,
      created_at: new Date().toISOString(),
      owner_id: 'user1',
      messages: {},
      status_msg: null,
      group_id: null,
    });
    mockUpdateChat.mockResolvedValue({
      chat_id: '1',
      title: 'Chat 1',
      vault_mode: false,
      favorite: false,
      active: true,
      last_message_at: new Date().toISOString(),
      status: ChatStatusEnum.NORMAL,
      created_at: new Date().toISOString(),
      owner_id: 'user1',
      messages: {},
      status_msg: null,
      group_id: null,
    });
  });

  it('renders search button with tooltip', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    expect(screen.getByRole('button')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toHaveAttribute(
      'data-title',
      'Search chats',
    );
    expect(screen.getByTestId('search-icon')).toBeInTheDocument();
  });

  it('opens search modal when button is clicked', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('search-modal')).toBeInTheDocument();
    });
  });

  it('closes search modal when cancel is clicked', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('search-modal')).toBeInTheDocument();
    });

    const closeButton = screen.getByTestId('close-modal');

    await act(async () => {
      fireEvent.click(closeButton);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('search-modal')).not.toBeInTheDocument();
    });
  });

  it('loads chats when modal opens', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        search: '',
        group_id: null,
        limit: CHATS_PAGE_SIZE,
      });
    });
  });

  it('displays loaded chats in modal', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-2')).toBeInTheDocument();
      expect(screen.getByText('Chat 1')).toBeInTheDocument();
      expect(screen.getByText('Chat 2')).toBeInTheDocument();
    });
  });

  it('filters chats based on search text', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('search-modal')).toBeInTheDocument();
    });

    mockGetChats.mockClear();

    const searchInput = screen.getByTestId('search-input');

    await act(async () => {
      fireEvent.change(searchInput, { target: { value: 'test search' } });
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        search: 'test search',
        group_id: null,
        limit: CHATS_PAGE_SIZE,
      });
    });
  });

  it('calls load more when button is clicked', async () => {
    // First call returns page 1 with hasNextPage true
    mockGetChats.mockResolvedValueOnce(
      createMockPagination(mockChats, true, 1),
    );

    // Second call returns page 2 with different chats and hasNextPage false
    const page2Chats: ChatType[] = [
      {
        chat_id: '3',
        title: 'Chat 3',
        vault_mode: false,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
      {
        chat_id: '4',
        title: 'Chat 4',
        vault_mode: false,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
    ];
    mockGetChats.mockResolvedValueOnce(
      createMockPagination(page2Chats, false, 2),
    );

    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('has-more')).toBeInTheDocument();
      expect(mockGetChats).toHaveBeenCalledTimes(1);
    });

    const loadMoreButton = screen.getByTestId('load-more');

    await act(async () => {
      fireEvent.click(loadMoreButton);
    });

    await waitFor(
      () => {
        expect(mockGetChats).toHaveBeenCalledTimes(2);
      },
      { timeout: 3000 },
    );

    const calls = mockGetChats.mock.calls;
    expect(calls).toHaveLength(2);
    expect(calls[0][0]).toMatchObject({
      page: 1,
      search: '',
      group_id: null,
      limit: CHATS_PAGE_SIZE,
    });
    expect(calls[1][0]).toMatchObject({
      page: 2,
      search: '',
      group_id: null,
      limit: CHATS_PAGE_SIZE,
    });

    // Verify all 4 chats are now displayed (2 from page 1 + 2 from page 2)
    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-2')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-3')).toBeInTheDocument();
      expect(screen.getByTestId('chat-item-4')).toBeInTheDocument();
    });

    // Verify hasMore is now false (no more button should be shown)
    expect(screen.queryByTestId('has-more')).not.toBeInTheDocument();
  });

  it('changes active chat when chat item is clicked', async () => {
    const store = mockStore(initialState);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
    });

    const chatItem = screen.getByTestId('chat-item-1');

    await act(async () => {
      fireEvent.click(chatItem);
    });

    await waitFor(() => {
      expect(mockUpdateChat).toHaveBeenCalledWith({
        id: '1',
        favorite: false,
        active: true,
        title: 'Chat 1',
        group_id: null,
      });
      expect(mockGetChat).toHaveBeenCalledWith({ id: '1' });
    });
  });

  it('shows vault warning modal when clicking vault mode chat without vault mode enabled', async () => {
    const vaultModeChats: ChatType[] = [
      {
        chat_id: '1',
        title: 'Vault Chat',
        vault_mode: true,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
    ];

    mockGetChats.mockResolvedValue(createMockPagination(vaultModeChats));

    const store = mockStore(initialState);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
    });

    const chatItem = screen.getByTestId('chat-item-1');

    await act(async () => {
      fireEvent.click(chatItem);
    });

    await waitFor(() => {
      expect(screen.getByTestId('vault-warning-modal')).toBeInTheDocument();
    });

    // Verify updateChat was NOT called
    expect(mockUpdateChat).not.toHaveBeenCalled();
  });

  it('closes vault warning modal', async () => {
    const vaultModeChats: ChatType[] = [
      {
        chat_id: '1',
        title: 'Vault Chat',
        vault_mode: true,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
    ];

    mockGetChats.mockResolvedValue(createMockPagination(vaultModeChats));

    const store = mockStore(initialState);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
    });

    const chatItem = screen.getByTestId('chat-item-1');

    await act(async () => {
      fireEvent.click(chatItem);
    });

    await waitFor(() => {
      expect(screen.getByTestId('vault-warning-modal')).toBeInTheDocument();
    });

    const closeVaultWarning = screen.getByTestId('close-vault-warning');

    await act(async () => {
      fireEvent.click(closeVaultWarning);
    });

    await waitFor(() => {
      expect(
        screen.queryByTestId('vault-warning-modal'),
      ).not.toBeInTheDocument();
    });
  });

  it('resets state when modal is closed', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('search-modal')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('search-input') as HTMLInputElement;

    await act(async () => {
      fireEvent.change(searchInput, { target: { value: 'test' } });
    });

    const closeButton = screen.getByTestId('close-modal');

    await act(async () => {
      fireEvent.click(closeButton);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('search-modal')).not.toBeInTheDocument();
    });

    // Reset previousValue for the next modal open
    previousValue = null;

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      const reopenedSearchInput = screen.getByTestId(
        'search-input',
      ) as HTMLInputElement;
      expect(reopenedSearchInput.value).toBe('');
    });
  });

  it('displays favorite icon for favorite chats', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('favorite-icon-true')).toBeInTheDocument();
      expect(screen.getByTestId('favorite-icon-false')).toBeInTheDocument();
    });
  });

  it('passes additional button props correctly', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(
        <SearchChatsButton disabled data-testid='custom-search-button' />,
        { store },
      );
    });

    const button = screen.getByTestId('custom-search-button');
    expect(button).toBeDisabled();
  });

  it('handles empty chats response', async () => {
    mockGetChats.mockResolvedValue(createMockPagination([]));

    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('items-count')).toHaveTextContent('0');
    });
  });

  it('uses active chat group when filtering', async () => {
    const stateWithActiveGroup: Partial<RootStore> = {
      ...initialState,
      chatsGroups: {
        chatsGroups: [],
        activeChatGroup: 'group-123',
      },
    };

    const store = mockStore(stateWithActiveGroup);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        search: '',
        group_id: 'group-123',
        limit: CHATS_PAGE_SIZE,
      });
    });
  });

  it('handles readonly chat status', async () => {
    const readonlyChats: ChatType[] = [
      {
        chat_id: '1',
        title: 'Readonly Chat',
        vault_mode: false,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.READONLY,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: 'This chat is read-only',
        group_id: null,
      },
    ];

    mockGetChats.mockResolvedValue(createMockPagination(readonlyChats));

    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
      expect(screen.getByText('Readonly Chat')).toBeInTheDocument();
    });
  });

  it('marks chat items as disabled when vault mode is not enabled', async () => {
    const vaultModeChats: ChatType[] = [
      {
        chat_id: '1',
        title: 'Vault Chat',
        vault_mode: true,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
    ];

    mockGetChats.mockResolvedValue(createMockPagination(vaultModeChats));

    const store = mockStore(initialState);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      const chatItem = screen.getByTestId('chat-item-1');
      expect(chatItem).toHaveAttribute('data-disabled-by-vault', 'true');
    });
  });

  it('does not show vault warning when vault mode is enabled', async () => {
    const vaultModeChats: ChatType[] = [
      {
        chat_id: '1',
        title: 'Vault Chat',
        vault_mode: true,
        favorite: false,
        active: false,
        last_message_at: new Date().toISOString(),
        status: ChatStatusEnum.NORMAL,
        created_at: new Date().toISOString(),
        owner_id: 'user1',
        messages: {},
        status_msg: null,
        group_id: null,
      },
    ];

    mockGetChats.mockResolvedValue(createMockPagination(vaultModeChats));

    const stateWithVault: Partial<RootStore> = {
      ...initialState,
      chats: {
        ...initialState.chats!,
        vaultMode: true,
        vaultModeRegistered: true,
      },
    };

    const store = mockStore(stateWithVault);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
    });

    const chatItem = screen.getByTestId('chat-item-1');

    await act(async () => {
      fireEvent.click(chatItem);
    });

    await waitFor(() => {
      expect(mockUpdateChat).toHaveBeenCalled();
      expect(
        screen.queryByTestId('vault-warning-modal'),
      ).not.toBeInTheDocument();
    });
  });

  it('closes search modal after selecting a chat', async () => {
    const store = mockStore(initialState);

    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-item-1')).toBeInTheDocument();
    });

    const chatItem = screen.getByTestId('chat-item-1');

    await act(async () => {
      fireEvent.click(chatItem);
    });

    await waitFor(() => {
      expect(screen.queryByTestId('search-modal')).not.toBeInTheDocument();
    });
  });

  it('renders with custom search placeholder', async () => {
    const store = mockStore(initialState);
    await act(async () => {
      renderLayout(<SearchChatsButton />, { store });
    });

    const button = screen.getByRole('button');

    await act(async () => {
      fireEvent.click(button);
    });

    await waitFor(() => {
      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute('placeholder', 'Search chats...');
    });
  });
});
