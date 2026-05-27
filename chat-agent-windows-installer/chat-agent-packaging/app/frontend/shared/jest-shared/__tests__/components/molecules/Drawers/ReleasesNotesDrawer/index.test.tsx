import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import { ChatUsageType, ChatType } from '@shared/ui/types/chats.types';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import {
  getChatsUsageByRange,
  getChatUsage,
} from '@shared/ui/services/chats.services';
import ChatInfoDrawer from '@chats/components/molecules/Drawers/ChatInfoDrawer';

// Mock services
jest.mock('@shared/ui/services/chats.services');
const mockGetChatsUsageByRange = getChatsUsageByRange as jest.MockedFunction<
  typeof getChatsUsageByRange
>;
const mockGetChatUsage = getChatUsage as jest.MockedFunction<
  typeof getChatUsage
>;

// Mock hooks
jest.mock('@shared/ui/hooks/useHandleError.hook');
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;

// Mock dayjs
jest.mock('@shared/ui/libs/dayjs.libs', () => ({
  __esModule: true,
  default: () => ({
    subtract: jest.fn().mockReturnThis(),
    toDate: jest.fn().mockReturnValue(new Date('2024-01-01')),
  }),
}));

// Mock Ant Design components
jest.mock('antd', () => ({
  Drawer: ({ children, title, loading, placement, ...props }: any) => {
    // Handle boolean attributes properly for DOM
    const domProps = { ...props };
    if (typeof domProps.closable === 'boolean') {
      domProps.closable = domProps.closable.toString();
    }

    return (
      <div
        data-testid='chat-info-drawer'
        data-title={title}
        data-loading={loading?.toString()}
        data-placement={placement}
        {...domProps}
      >
        {!loading && children}
      </div>
    );
  },
  Col: ({ children, span, ...props }: any) => (
    <div data-testid='col' data-span={span} {...props}>
      {children}
    </div>
  ),
  Row: ({ children, gutter, ...props }: any) => (
    <div data-testid='row' data-gutter={gutter} {...props}>
      {children}
    </div>
  ),
  Divider: (props: any) => <hr data-testid='divider' {...props} />,
  Statistic: ({ title, value, ...props }: any) => (
    <div data-testid='statistic' data-title={title} {...props}>
      <div data-testid='statistic-title'>{title}</div>
      <div data-testid='statistic-value'>{value}</div>
    </div>
  ),
  Typography: {
    Title: ({ children, level, ...props }: any) => (
      <h1 data-testid='title' data-level={level} {...props}>
        {children}
      </h1>
    ),
  },
}));

describe('ChatInfoDrawer', () => {
  const mockHandleError = jest.fn();

  const mockChatsUsage: ChatUsageType = {
    input_token: 1000,
    output_token: 2000,
    cost: 5.5,
  };

  const mockChatUsage: ChatUsageType = {
    input_token: 500,
    output_token: 800,
    cost: 2.25,
  };

  const mockActiveChat: ChatType = {
    chat_id: 'chat-123',
    title: 'Test Chat',
    created_at: '2024-01-01T00:00:00Z',
    owner_id: 'user-123',
    last_message_at: '2024-01-01T12:00:00Z',
    vault_mode: false,
    messages: {},
    active: true,
    favorite: false,
    status: ChatStatusEnum.NORMAL,
    status_msg: null,
    group_id: null,
  };

  const defaultProps = {
    open: true,
    onClose: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockGetChatsUsageByRange.mockResolvedValue(mockChatsUsage);
    mockGetChatUsage.mockResolvedValue(mockChatUsage);
  });

  const renderComponent = (props = {}, storeState: Partial<RootStore> = {}) => {
    const store = mockStore({
      settings: {},
      chatsGroups: {},
      ...storeState,
      chats: {
        activeChat: mockActiveChat,
        ...storeState?.chats,
      },
    });

    return renderLayout(<ChatInfoDrawer {...defaultProps} {...props} />, {
      store,
    });
  };

  describe('Component Rendering', () => {
    it('should render the drawer with correct title and placement', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(screen.getByTestId('chat-info-drawer')).toBeInTheDocument();
      });

      const drawer = screen.getByTestId('chat-info-drawer');
      expect(drawer).toHaveAttribute('data-title', 'Chat information');
      expect(drawer).toHaveAttribute('data-placement', 'right');
    });

    it('should show loading state initially', async () => {
      // Create a promise that we can control
      let resolvePromise: (value: any) => void;
      const controlledPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      mockGetChatsUsageByRange.mockReturnValue(controlledPromise);
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      mockGetChatUsage.mockReturnValue(controlledPromise);

      await act(async () => {
        renderComponent();
      });

      // Check loading state before promises resolve
      const drawer = screen.getByTestId('chat-info-drawer');
      expect(drawer).toHaveAttribute('data-loading', 'true');

      // Resolve the promises
      await act(async () => {
        resolvePromise!(mockChatsUsage);
      });
    });

    it('should hide loading state after data is loaded', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const drawer = screen.getByTestId('chat-info-drawer');
        expect(drawer).toHaveAttribute('data-loading', 'false');
      });
    });

    it('should pass through drawer props correctly', async () => {
      await act(async () => {
        renderComponent({ width: 500, closable: false });
      });

      await waitFor(() => {
        const drawer = screen.getByTestId('chat-info-drawer');
        expect(drawer).toHaveAttribute('width', '500');
        expect(drawer).toHaveAttribute('closable', 'false');
      });
    });
  });

  describe('Data Fetching', () => {
    it('should fetch chats usage data with correct date range', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(mockGetChatsUsageByRange).toHaveBeenCalledWith({
          start_date: new Date('2024-01-01'),
          end_date: new Date('2024-01-01'),
        });
      });
    });

    it('should fetch individual chat usage when activeChat exists', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(mockGetChatUsage).toHaveBeenCalledWith('chat-123');
      });
    });

    it('should not fetch individual chat usage when no activeChat', async () => {
      await act(async () => {
        renderComponent(
          {},
          {
            chats: {
              activeChat: null,
              vaultMode: false,
              vaultModeRegistered: false,
              totalChats: 0,
              chats: [],
              aiTyping: false,
              hasMoreChats: false,
              showEnableVaultModal: false,
            },
          },
        );
      });

      await waitFor(() => {
        expect(mockGetChatsUsageByRange).toHaveBeenCalled();
      });

      expect(mockGetChatUsage).not.toHaveBeenCalled();
    });
  });

  describe('Total Usage Section', () => {
    it('should render total usage section with correct title', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(
          screen.getByText('Total usage in last 30 days'),
        ).toBeInTheDocument();
      });

      const title = screen.getByText('Total usage in last 30 days');
      expect(title).toHaveAttribute('data-level', '4');
    });

    it('should render total usage statistics correctly', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const statistics = screen.getAllByTestId('statistic');
        expect(statistics.length).toBeGreaterThanOrEqual(3);
      });

      const statistics = screen.getAllByTestId('statistic');
      const totalStats = statistics.slice(0, 3); // First 3 are for total usage

      expect(totalStats[0]).toHaveAttribute('data-title', 'Total input tokens');
      expect(totalStats[0]).toHaveTextContent('1000');

      expect(totalStats[1]).toHaveAttribute(
        'data-title',
        'Total output tokens',
      );
      expect(totalStats[1]).toHaveTextContent('2000');

      expect(totalStats[2]).toHaveAttribute('data-title', 'Total cost');
      expect(totalStats[2]).toHaveTextContent('$5.5');
    });

    it('should not render total usage section when chatsInfo is null', async () => {
      mockGetChatsUsageByRange.mockResolvedValue(null as any);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const drawer = screen.getByTestId('chat-info-drawer');
        expect(drawer).toHaveAttribute('data-loading', 'false');
      });

      expect(
        screen.queryByText('Total usage in last 30 days'),
      ).not.toBeInTheDocument();
    });
  });

  describe('Individual Chat Usage Section', () => {
    it('should render individual chat usage section with correct title', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Total usage by current chat/),
        ).toBeInTheDocument();
      });

      const title = screen.getByText(/Total usage by current chat/);
      expect(title).toHaveAttribute('data-level', '4');
    });

    it('should render individual chat statistics correctly', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const statistics = screen.getAllByTestId('statistic');
        expect(statistics).toHaveLength(6); // 3 for total + 3 for individual chat
      });

      const statistics = screen.getAllByTestId('statistic');
      const chatStats = statistics.slice(3, 6); // Last 3 are for individual chat

      expect(chatStats[0]).toHaveAttribute('data-title', 'Total input tokens');
      expect(chatStats[0]).toHaveTextContent('500');

      expect(chatStats[1]).toHaveAttribute('data-title', 'Total output tokens');
      expect(chatStats[1]).toHaveTextContent('800');

      expect(chatStats[2]).toHaveAttribute('data-title', 'Total cost');
      expect(chatStats[2]).toHaveTextContent('$2.25');
    });

    it('should not render individual chat section when chatInfo is null', async () => {
      mockGetChatUsage.mockResolvedValue(null as any);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(
          screen.getByText('Total usage in last 30 days'),
        ).toBeInTheDocument();
      });

      expect(screen.queryByText(/Total usage by chat/)).not.toBeInTheDocument();
    });

    it('should not render individual chat section when no activeChat', async () => {
      await act(async () => {
        renderComponent(
          {},
          {
            chats: {
              activeChat: null,
              vaultMode: false,
              vaultModeRegistered: false,
              totalChats: 0,
              chats: [],
              aiTyping: false,
              hasMoreChats: false,
              showEnableVaultModal: false,
            },
          },
        );
      });

      await waitFor(() => {
        expect(
          screen.getByText('Total usage in last 30 days'),
        ).toBeInTheDocument();
      });

      expect(screen.queryByText(/Total usage by chat/)).not.toBeInTheDocument();
    });
  });

  describe('Layout and Structure', () => {
    it('should render rows and columns with correct props', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const rows = screen.getAllByTestId('row');
        expect(rows).toHaveLength(2); // One for total, one for individual chat
      });

      const rows = screen.getAllByTestId('row');
      rows.forEach((row) => {
        expect(row).toHaveAttribute('data-gutter', '16');
      });

      const cols = screen.getAllByTestId('col');
      cols.forEach((col) => {
        expect(col).toHaveAttribute('data-span', '12');
      });
    });

    it('should render dividers between sections', async () => {
      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const dividers = screen.getAllByTestId('divider');
        expect(dividers).toHaveLength(2); // One for each section
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle error when fetching chats usage fails', async () => {
      const error = new Error('Failed to fetch chats usage');
      mockGetChatsUsageByRange.mockRejectedValue(error);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      await waitFor(() => {
        const drawer = screen.getByTestId('chat-info-drawer');
        expect(drawer).toHaveAttribute('data-loading', 'false');
      });
    });

    it('should handle error when fetching individual chat usage fails', async () => {
      const error = new Error('Failed to fetch chat usage');
      mockGetChatUsage.mockRejectedValue(error);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      await waitFor(() => {
        const drawer = screen.getByTestId('chat-info-drawer');
        expect(drawer).toHaveAttribute('data-loading', 'false');
      });
    });

    it('should continue loading total usage even if individual chat usage fails', async () => {
      mockGetChatUsage.mockRejectedValue(new Error('Chat usage failed'));

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        expect(
          screen.getByText('Total usage in last 30 days'),
        ).toBeInTheDocument();
      });

      expect(screen.queryByText(/Total usage by chat/)).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero values in statistics', async () => {
      const zeroUsage: ChatUsageType = {
        input_token: 0,
        output_token: 0,
        cost: 0,
      };

      mockGetChatsUsageByRange.mockResolvedValue(zeroUsage);
      mockGetChatUsage.mockResolvedValue(zeroUsage);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const values = screen.getAllByTestId('statistic-value');

        expect(values[0]).toHaveTextContent('0'); // input tokens
        expect(values[1]).toHaveTextContent('0'); // output tokens
        expect(values[2]).toHaveTextContent('$0'); // cost
      });
    });

    it('should handle large numbers in statistics', async () => {
      const largeUsage: ChatUsageType = {
        input_token: 1000000,
        output_token: 2000000,
        cost: 999.99,
      };

      mockGetChatsUsageByRange.mockResolvedValue(largeUsage);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const values = screen.getAllByTestId('statistic-value');
        expect(values[0]).toHaveTextContent('1000000');
        expect(values[1]).toHaveTextContent('2000000');
        expect(values[2]).toHaveTextContent('$999.99');
      });
    });

    it('should handle decimal cost values', async () => {
      const decimalUsage: ChatUsageType = {
        input_token: 100,
        output_token: 200,
        cost: 1.234567,
      };

      mockGetChatsUsageByRange.mockResolvedValue(decimalUsage);

      await act(async () => {
        renderComponent();
      });

      await waitFor(() => {
        const values = screen.getAllByTestId('statistic-value');
        expect(values[2]).toHaveTextContent('$1.23');
      });
    });

    it('should handle activeChat without chat_id', async () => {
      const chatWithoutId = {
        ...mockActiveChat,
        chat_id: '',
      };

      await act(async () => {
        renderComponent(
          {},
          {
            chats: {
              activeChat: chatWithoutId,
              vaultMode: false,
              vaultModeRegistered: false,
              totalChats: 0,
              chats: [],
              aiTyping: false,
              hasMoreChats: false,
              showEnableVaultModal: false,
            },
          },
        );
      });

      await waitFor(() => {
        expect(mockGetChatsUsageByRange).toHaveBeenCalled();
      });

      expect(mockGetChatUsage).not.toHaveBeenCalled();
    });

    it('should handle empty chat title', async () => {
      const chatWithEmptyTitle: ChatType = {
        ...mockActiveChat,
        title: '',
      };

      await act(async () => {
        renderComponent(
          {},
          {
            chats: {
              activeChat: chatWithEmptyTitle,
              vaultMode: false,
              vaultModeRegistered: false,
              totalChats: 0,
              chats: [],
              aiTyping: false,
              hasMoreChats: false,
              showEnableVaultModal: false,
            },
          },
        );
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Total usage by current chat/),
        ).toBeInTheDocument();
      });
    });
  });
});
