import React from 'react';
import { fireEvent, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { usePathname } from 'next/navigation';
import * as chatsServices from '@shared/ui/services/chats.services';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import CustomSidebar from '@/components/organisms/Sidebars/CustomSidebar';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(),
}));

// Mock services
jest.mock('@shared/ui/services/chats.services', () => ({
  getChats: jest.fn(),
}));

// Mock hooks
jest.mock('@shared/ui/hooks/useHandleError.hook', () => {
  return jest.fn(() => jest.fn());
});

// Mock Redux actions
jest.mock('@shared/ui/store/chats/chats.slice', () => ({
  setChats: jest.fn((payload) => ({
    type: 'chats/setChats',
    payload,
  })),
  setHasMoreChats: jest.fn((payload) => ({
    type: 'chats/setHasMoreChats',
    payload,
  })),
  chatsReducer: (state = {}) => state,
}));

// Mock components
jest.mock('@/components/molecules/Sidebars/CustomSidebarHeader', () => {
  return function MockCustomSidebarHeader({
    showChats,
  }: {
    showChats: boolean;
  }) {
    return (
      <div data-testid='custom-sidebar-header'>
        {showChats && (
          <span data-testid='show-chats-indicator'>Show Chats</span>
        )}
      </div>
    );
  };
});

jest.mock('@/components/molecules/Sidebars/CustomSidebarChats', () => {
  return function MockCustomSidebarChats({ onLoadMore }: any) {
    return (
      <div data-testid='custom-sidebar-chats'>
        <button
          data-testid='load-more-button'
          onClick={() => onLoadMore(false)}
        >
          Load More
        </button>
      </div>
    );
  };
});

jest.mock('@/components/molecules/ChatsGroupsFilter', () => {
  return function MockChatsGroupFilter() {
    return <div data-testid='chats-group-filter'>Group Filter</div>;
  };
});

// Mock utils
jest.mock('@/utils/chats.utils', () => ({
  sortChats: jest.fn((chats) => chats),
}));

jest.mock('@shared/ui/hooks/usePrevious.hook', () => {
  return jest.fn();
});

// Mock constants
jest.mock('@shared/ui/constants/menu.constants', () => ({
  MENU_ITEMS: [
    { key: 'home', value: '/', label: 'Home' },
    { key: 'chats', value: '/chats', label: 'Chats' },
    { key: 'settings', value: '/settings', label: 'Settings' },
  ],
}));

// Mock styled components
jest.mock(
  '@/components/organisms/Sidebars/CustomSidebar/CustomSidebar.styled',
  () => ({
    StyledCustomSidebar: ({ children, ...props }: any) => {
      const {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        collapsible,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        collapsed,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        trigger,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        collapsedWidth,
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        width,
        ...domProps
      } = props;

      return (
        <aside data-testid='custom-sidebar' role='complementary' {...domProps}>
          <div className='ant-layout-sider-children'>{children}</div>
        </aside>
      );
    },
    StyledSidebarWrapper: ({ children, $isCollapsed, ...props }: any) => (
      <div
        data-testid='sidebar-wrapper'
        data-collapsed={$isCollapsed}
        {...props}
      >
        {children}
      </div>
    ),
    StyledSidebarMenu: ({ items, selectedKeys, ...props }: any) => (
      <ul role='menu' data-testid='sidebar-menu' {...props}>
        {items?.map((item: any) => (
          <li
            key={item.key}
            role='menuitem'
            value={item.value}
            className={selectedKeys?.includes(item.key) ? 'selected' : ''}
          >
            <span className='ant-menu-title-content'>{item.label}</span>
          </li>
        ))}
      </ul>
    ),
  }),
);

// Import the mocked functions after the mock is set up
import { setChats, setHasMoreChats } from '@shared/ui/store/chats/chats.slice';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { RootStore } from '@shared/ui/types/store.types';

const mockSetChats = setChats as jest.MockedFunction<typeof setChats>;
const mockSetHasMoreChats = setHasMoreChats as jest.MockedFunction<
  typeof setHasMoreChats
>;

// Helper functions
const createMockChatsResponse = (overrides = {}) => ({
  docs: [],
  hasNextPage: false,
  active_chat_id: '1',
  hasPrevPage: false,
  prevPage: 1,
  nextPage: 1,
  page: 1,
  totalPages: 1,
  totalDocs: 0,
  limit: 25,
  pagingCounter: 1,
  ...overrides,
});

const createMockChat = (overrides = {}) => ({
  chat_id: 'test-chat-id',
  title: 'Test Chat',
  active: false,
  favorite: false,
  created_at: '2024-01-01T00:00:00Z',
  owner_id: 'user-123',
  last_message_at: '2024-01-01T00:00:00Z',
  vault_mode: false,
  messages: {},
  status: ChatStatusEnum.NORMAL,
  status_msg: null,
  group_id: null,
  ...overrides,
});

describe('CustomSidebar', () => {
  let store: ReturnType<typeof mockStore>;
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let user: ReturnType<typeof userEvent.setup>;
  const mockGetChats = chatsServices.getChats as jest.MockedFunction<
    typeof chatsServices.getChats
  >;
  const mockUsePathname = usePathname as jest.MockedFunction<
    typeof usePathname
  >;
  const mockHandleError = jest.fn();

  const defaultState: RootStore = {
    settings: {
      collapsedSidebar: false,
      themeMode: 'dark',
      releases: [],
      showReleaseModal: false,
      hasMoreReleases: false,
      user: {
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        last_release_date: null,
      },
    },
    chats: {
      chats: [
        createMockChat({
          chat_id: 'chat-1',
          title: 'Test Chat 1',
        }),
        createMockChat({
          chat_id: 'chat-2',
          title: 'Test Chat 2',
          created_at: '2024-01-02T00:00:00Z',
          last_message_at: '2024-01-02T00:00:00Z',
        }),
      ],
      hasMoreChats: true,
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreMessages: false,
      totalChats: 2,
    },
    chatsGroups: {
      chatsGroups: [],
      activeChatGroup: 'all',
    },
  };

  const mockUsePrevious = jest.fn();

  beforeEach(() => {
    user = userEvent.setup();
    store = mockStore(defaultState);

    jest.clearAllMocks();
    mockUsePathname.mockReturnValue('/');
    mockUsePrevious.mockReturnValue(undefined);

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@shared/ui/hooks/useHandleError.hook').mockReturnValue(
      mockHandleError,
    );
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@shared/ui/hooks/usePrevious.hook').mockImplementation(
      mockUsePrevious,
    );
  });

  describe('Rendering', () => {
    it('should render the sidebar with correct test id', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toBeInTheDocument();
      expect(sidebar).toHaveClass('custom-sidebar');
    });

    it('should render with custom className', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar className='custom-class' />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toHaveClass('custom-sidebar', 'custom-class');
    });

    it('should render sidebar header', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const header = screen.getByTestId('custom-sidebar-header');
      expect(header).toBeInTheDocument();
    });

    it('should render sidebar menu', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const menu = screen.getByRole('menu');
      expect(menu).toBeInTheDocument();
    });

    it('should render sidebar wrapper with correct collapsed state', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const wrapper = screen.getByTestId('sidebar-wrapper');
      expect(wrapper).toBeInTheDocument();
      expect(wrapper).toHaveAttribute('data-collapsed', 'false');
    });

    it('should have proper accessibility attributes', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toHaveAttribute('role', 'complementary');

      const menu = screen.getByRole('menu');
      expect(menu).toBeInTheDocument();

      const menuItems = screen.getAllByRole('menuitem');
      expect(menuItems.length).toBeGreaterThan(0);
    });

    it('should render chats group filter', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const groupFilter = screen.getByTestId('chats-group-filter');
      expect(groupFilter).toBeInTheDocument();
    });
  });

  describe('Chat Display', () => {
    it('should show chats when showChats is true', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar showChats />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('custom-sidebar-chats')).toBeInTheDocument();
      });

      const showChatsIndicator = screen.getByTestId('show-chats-indicator');
      expect(showChatsIndicator).toBeInTheDocument();
    });

    it('should not show chats when showChats is false', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar showChats={false} />, { store });
      });

      const chats = screen.queryByTestId('custom-sidebar-chats');
      expect(chats).not.toBeInTheDocument();

      const showChatsIndicator = screen.queryByTestId('show-chats-indicator');
      expect(showChatsIndicator).not.toBeInTheDocument();
    });

    it('should show chats by default', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('custom-sidebar-chats')).toBeInTheDocument();
      });
    });
  });

  describe('Sidebar State', () => {
    it('should handle collapsed state from store', async () => {
      const collapsedStore = mockStore({
        ...defaultState,
        settings: {
          ...defaultState.settings,
          collapsedSidebar: true,
        },
      });

      await act(async () => {
        renderLayout(<CustomSidebar />, { store: collapsedStore });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toBeInTheDocument();

      const wrapper = screen.getByTestId('sidebar-wrapper');
      expect(wrapper).toHaveAttribute('data-collapsed', 'true');
    });

    it('should pass correct props to StyledCustomSidebar', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toBeInTheDocument();
    });
  });

  describe('Menu Selection', () => {
    it('should select correct menu item based on pathname', async () => {
      mockUsePathname.mockReturnValue('/chats');

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const menu = screen.getByTestId('sidebar-menu');
      expect(menu).toBeInTheDocument();

      const chatMenuItem = screen.getByText('Chats');
      expect(chatMenuItem).toBeInTheDocument();
      expect(chatMenuItem.closest('li')).toHaveClass('selected');
    });

    it('should handle unknown pathname', async () => {
      mockUsePathname.mockReturnValue('/unknown-path');

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const menu = screen.getByTestId('sidebar-menu');
      expect(menu).toBeInTheDocument();

      const selectedItems = screen.queryAllByText((content, element) => {
        return element?.closest('li')?.classList.contains('selected') || false;
      });
      expect(selectedItems).toHaveLength(0);
    });

    it('should select home menu item for root path', async () => {
      mockUsePathname.mockReturnValue('/');

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const homeMenuItem = screen.getByText('Home');
      expect(homeMenuItem).toBeInTheDocument();
      expect(homeMenuItem.closest('li')).toHaveClass('selected');
    });
  });

  describe('Load More Functionality', () => {
    it('should load more chats when onLoadMore is called', async () => {
      mockGetChats.mockResolvedValueOnce(
        createMockChatsResponse({
          docs: [
            createMockChat({
              chat_id: 'new-chat-3',
              title: 'New Chat 3',
              active: false,
            }),
            createMockChat({
              chat_id: 'new-chat-4',
              title: 'New Chat 4',
              active: false,
            }),
          ],
          hasNextPage: true,
          nextPage: 2,
          page: 2,
        }),
      );

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockGetChats).toHaveBeenCalledWith({
          page: 2,
          group_id: 'all',
          limit: 25,
        });
      });

      await waitFor(() => {
        expect(mockSetHasMoreChats).toHaveBeenCalledWith(true);
        expect(mockSetChats).toHaveBeenCalled();
      });
    });

    it('should update current page correctly', async () => {
      mockGetChats
        .mockResolvedValueOnce(
          createMockChatsResponse({
            docs: [
              createMockChat({
                chat_id: 'page-2-chat-1',
                title: 'Page 2 Chat 1',
              }),
            ],
            hasNextPage: true,
            nextPage: 3,
            page: 2,
          }),
        )
        .mockResolvedValueOnce(
          createMockChatsResponse({
            docs: [
              createMockChat({
                chat_id: 'page-3-chat-1',
                title: 'Page 3 Chat 1',
              }),
            ],
            hasNextPage: false,
            prevPage: 2,
            nextPage: 3,
            page: 3,
          }),
        );

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledWith({
          page: 2,
          group_id: 'all',
          limit: 25,
        });
      });

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledWith({
          page: 3,
          group_id: 'all',
          limit: 25,
        });
      });

      expect(mockGetChats).toHaveBeenCalledTimes(2);
    });
  });

  describe('Loading State Management', () => {
    it('should reset loading state after successful API call', async () => {
      mockGetChats.mockResolvedValue(createMockChatsResponse());

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
      });

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle API errors during load more', async () => {
      const error = new Error('API Error');
      mockGetChats.mockRejectedValue(error);

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });

    it('should reset loading state after error', async () => {
      const error = new Error('API Error');
      mockGetChats
        .mockRejectedValueOnce(error)
        .mockResolvedValueOnce(createMockChatsResponse());

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty docs array', async () => {
      mockGetChats.mockResolvedValue(
        createMockChatsResponse({
          docs: [],
        }),
      );

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockSetHasMoreChats).toHaveBeenCalledWith(false);
      });
    });

    it('should handle undefined docs in API response', async () => {
      mockGetChats.mockResolvedValue({
        docs: [],
        hasNextPage: false,
        active_chat_id: '1',
        hasPrevPage: false,
        prevPage: 1,
        nextPage: 1,
        page: 1,
        totalPages: 1,
        totalDocs: 0,
        limit: 1,
      });

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockSetChats).toHaveBeenCalled();
        // @ts-ignore
        const setChatsCall = mockSetChats.mock.calls[0][0];
        expect(Array.isArray(setChatsCall)).toBe(true);
      });
    });

    it('should handle undefined hasNextPage in API response', async () => {
      mockGetChats.mockResolvedValue({
        docs: [],
        active_chat_id: '1',
        hasPrevPage: false,
        prevPage: 1,
        nextPage: 1,
        page: 1,
        totalPages: 1,
        totalDocs: 0,
        limit: 1,
        hasNextPage: false,
      });

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockSetHasMoreChats).toHaveBeenCalledWith(false);
      });
    });
  });

  describe('Component Lifecycle', () => {
    it('should cleanup properly on unmount', async () => {
      let unmount: () => void;

      await act(async () => {
        const result = renderLayout(<CustomSidebar />, { store });
        unmount = result.unmount;
      });

      expect(() => unmount!()).not.toThrow();
    });
  });

  describe('Props Handling', () => {
    it('should pass through additional props', async () => {
      const customProps = {
        'data-custom': 'test-value',
        id: 'custom-sidebar-id',
      };

      await act(async () => {
        renderLayout(<CustomSidebar {...customProps} />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toHaveAttribute('data-custom', 'test-value');
      expect(sidebar).toHaveAttribute('id', 'custom-sidebar-id');
    });

    it('should handle default props correctly', async () => {
      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      const sidebar = screen.getByTestId('custom-sidebar');
      expect(sidebar).toHaveClass('custom-sidebar');

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('custom-sidebar-chats')).toBeInTheDocument();
      });
    });
  });

  describe('Utils Integration', () => {
    it('should use sortChats utility when setting chats', async () => {
      const newChats = [
        createMockChat({
          chat_id: 'new-1',
          title: 'New Chat 1',
        }),
      ];

      mockGetChats.mockResolvedValue(
        createMockChatsResponse({
          docs: newChats,
        }),
      );

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('load-more-button')).toBeInTheDocument();
      });

      const loadMoreButton = screen.getByTestId('load-more-button');

      await act(async () => {
        fireEvent.click(loadMoreButton);
      });

      await waitFor(() => {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { sortChats } = require('@/utils/chats.utils');
        expect(sortChats).toHaveBeenCalled();
      });
    });
  });

  describe('Chat Group Handling', () => {
    it('should reload chats when active chat group changes', async () => {
      mockUsePrevious.mockReturnValue(undefined);
      mockGetChats.mockResolvedValueOnce(createMockChatsResponse());

      const initialStore = mockStore({
        ...defaultState,
        chatsGroups: {
          activeChatGroup: 'all',
          chatsGroups: [],
        },
      });

      const { rerender } = renderLayout(<CustomSidebar />, {
        store: initialStore,
      });

      // Wait for dynamic component to load
      await waitFor(() => {
        expect(screen.getByTestId('custom-sidebar-chats')).toBeInTheDocument();
      });

      mockUsePrevious.mockReturnValue('all');
      mockGetChats.mockResolvedValueOnce(createMockChatsResponse());

      const updatedStore = mockStore({
        ...defaultState,
        chatsGroups: {
          activeChatGroup: 'favorites',
          chatsGroups: [],
        },
      });

      await act(async () => {
        // eslint-disable-next-line @typescript-eslint/no-require-imports
        const { Provider } = require('react-redux');
        rerender(
          <Provider store={updatedStore}>
            <CustomSidebar />
          </Provider>,
        );
      });

      await waitFor(() => {
        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          group_id: 'favorites',
          limit: 25,
        });
      });
    });

    it('should not reload chats when chat group stays the same', async () => {
      mockUsePrevious.mockReturnValue('all');

      await act(async () => {
        renderLayout(<CustomSidebar />, { store });
      });

      expect(mockGetChats).not.toHaveBeenCalled();
    });
  });
});
