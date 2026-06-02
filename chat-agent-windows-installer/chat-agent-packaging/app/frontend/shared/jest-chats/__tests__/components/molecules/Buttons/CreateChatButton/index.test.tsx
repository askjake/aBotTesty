import React from 'react';
import { screen, fireEvent, act, waitFor } from '@testing-library/react';
import { MAX_CHATS } from '@shared/ui/constants/validation.constants';
import { createChat } from '@shared/ui/services/chats.services';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import CreateChatButton from '@/components/molecules/Buttons/CreateChatButton';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';

// Mock dependencies
jest.mock('@shared/ui/services/chats.services', () => ({
  createChat: jest.fn(),
}));

jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: () => jest.fn(),
}));

// Mock IconButton
// Update the IconButton mock to properly handle disabled state
jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => ({
  __esModule: true,
  default: ({ onClick, icon, loading, disabled, className, ...props }: any) => {
    const handleClick = (e: any) => {
      // Don't call onClick if button is disabled or loading
      if (disabled || loading) {
        e.preventDefault();
        return;
      }
      onClick?.(e);
    };

    return (
      <button
        onClick={handleClick}
        disabled={disabled || loading}
        className={className}
        data-loading={loading}
        {...props}
      >
        {icon}
      </button>
    );
  },
}));

// Mock Tooltip
jest.mock('antd', () => ({
  Tooltip: ({ children, title }: any) => (
    <div data-testid='tooltip' data-title={title}>
      {children}
    </div>
  ),
}));

// Mock icons
jest.mock('@ant-design/icons', () => ({
  PlusOutlined: () => <span className='anticon-plus'>+</span>,
}));

const mockCreateChat = createChat as jest.MockedFunction<typeof createChat>;
const mockHandleError = jest.fn();

// Helper to create mock chat
const createMockChat = (overrides = {}) => ({
  chat_id: 'test-chat-id',
  title: 'New Chat',
  active: false,
  favorite: false,
  created_at: '2024-01-01T00:00:00Z',
  owner_id: 'user-123',
  last_message_at: '2024-01-01T00:00:00Z',
  vault_mode: false,
  status: ChatStatusEnum.NORMAL,
  status_msg: null,
  group_id: null,
  messages: {},
  ...overrides,
});

describe('CreateChatButton Component', () => {
  const defaultState: Partial<RootStore> = {
    chats: {
      totalChats: 0,
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      hasMoreMessages: false,
    },
    chatsGroups: {
      chatsGroups: [],
      activeChatGroup: 'all',
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@shared/ui/hooks/useHandleError.hook').default = () =>
      mockHandleError;
  });

  describe('Rendering', () => {
    it('renders correctly with tooltip', async () => {
      const store = mockStore(defaultState);
      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      expect(screen.getByRole('button')).toBeInTheDocument();
      expect(screen.getByTestId('tooltip')).toHaveAttribute(
        'data-title',
        'Create a new chat',
      );
      expect(screen.getByText('+')).toBeInTheDocument();
    });

    it('renders with custom className', async () => {
      const store = mockStore(defaultState);
      await act(async () => {
        renderLayout(<CreateChatButton className='custom-class' />, { store });
      });

      const button = screen.getByRole('button');
      expect(button).toHaveClass('create-chat-button', 'custom-class');
    });

    it('passes additional props to IconButton', async () => {
      const store = mockStore(defaultState);
      await act(async () => {
        renderLayout(<CreateChatButton data-testid='custom-create-button' />, {
          store,
        });
      });

      expect(screen.getByTestId('custom-create-button')).toBeInTheDocument();
    });
  });

  describe('Disabled State', () => {
    it('is disabled when disabled prop is true', async () => {
      const store = mockStore(defaultState);
      await act(async () => {
        renderLayout(<CreateChatButton disabled />, { store });
      });

      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('does not create chat when disabled prop is true', async () => {
      const store = mockStore(defaultState);
      await act(async () => {
        renderLayout(<CreateChatButton disabled />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      expect(mockCreateChat).not.toHaveBeenCalled();
    });
  });

  describe('Chat Creation', () => {
    it('creates new chat successfully and updates state', async () => {
      const mockChatData = createMockChat({
        chat_id: 'new-chat-1',
        title: 'New Chat',
      });
      mockCreateChat.mockResolvedValue(mockChatData);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
      });

      const finalState = store.getState();
      expect(finalState.chats.totalChats).toBe(1);
      expect(finalState.chats.chats).toHaveLength(1);
      expect(finalState.chats.chats[0]).toMatchObject({
        chat_id: 'new-chat-1',
        title: 'New Chat',
        active: true,
        messages: {},
      });
      expect(finalState.chats.activeChat).toMatchObject({
        chat_id: 'new-chat-1',
        title: 'New Chat',
        active: true,
        messages: {},
      });
    });

    it('sets active chat group to "all" when creating new chat', async () => {
      const mockChatData = createMockChat();
      mockCreateChat.mockResolvedValue(mockChatData);

      const stateWithDifferentGroup: Partial<RootStore> = {
        ...defaultState,
        chatsGroups: {
          chatsGroups: [],
          activeChatGroup: 'favorites',
        },
      };

      const store = mockStore(stateWithDifferentGroup);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
      });

      const finalState = store.getState();
      expect(finalState.chatsGroups.activeChatGroup).toBe('all');
    });

    it('handles existing chats correctly when creating new chat', async () => {
      const mockChatData = createMockChat({
        chat_id: 'new-chat-2',
        title: 'New Chat 2',
      });
      mockCreateChat.mockResolvedValue(mockChatData);

      const existingChat = createMockChat({
        chat_id: 'existing-chat-1',
        title: 'Existing Chat',
        active: true,
      });

      const stateWithExistingChats: Partial<RootStore> = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          totalChats: 1,
          chats: [existingChat],
          activeChat: existingChat,
        },
      };

      const store = mockStore(stateWithExistingChats);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
      });

      const finalState = store.getState();
      expect(finalState.chats.totalChats).toBe(2);
      expect(finalState.chats.chats).toHaveLength(2);

      // New chat should be first and active
      expect(finalState.chats.chats[0]).toMatchObject({
        chat_id: 'new-chat-2',
        title: 'New Chat 2',
        active: true,
      });

      // Existing chat should be inactive
      expect(finalState.chats.chats[1]).toMatchObject({
        chat_id: 'existing-chat-1',
        active: false,
      });

      // Active chat should be the new one
      expect(finalState.chats.activeChat?.chat_id).toBe('new-chat-2');
    });

    it('handles multiple existing chats correctly', async () => {
      const mockChatData = createMockChat({
        chat_id: 'new-chat-3',
        title: 'New Chat 3',
      });
      mockCreateChat.mockResolvedValue(mockChatData);

      const existingChats = [
        createMockChat({
          chat_id: 'chat-1',
          title: 'Chat 1',
          active: true,
        }),
        createMockChat({
          chat_id: 'chat-2',
          title: 'Chat 2',
          active: false,
        }),
        createMockChat({
          chat_id: 'chat-3',
          title: 'Chat 3',
          active: false,
        }),
      ];

      const stateWithMultipleChats: Partial<RootStore> = {
        ...defaultState,
        chats: {
          ...defaultState.chats!,
          totalChats: 3,
          chats: existingChats,
          activeChat: existingChats[0],
        },
      };

      const store = mockStore(stateWithMultipleChats);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
      });

      const finalState = store.getState();
      expect(finalState.chats.totalChats).toBe(4);
      expect(finalState.chats.chats).toHaveLength(4);

      // All existing chats should be inactive
      expect(finalState.chats.chats[1]?.active).toBe(false);
      expect(finalState.chats.chats[2]?.active).toBe(false);
      expect(finalState.chats.chats[3]?.active).toBe(false);
    });
  });

  describe('Loading State', () => {
    it('shows loading state while creating chat', async () => {
      let resolveCreate: any;
      const createPromise = new Promise((resolve) => {
        resolveCreate = resolve;
      });
      mockCreateChat.mockReturnValue(createPromise as any);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      // Wait for loading state to be set
      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });

      // Button should be disabled during loading
      expect(button).toBeDisabled();

      // Resolve the promise
      await act(async () => {
        resolveCreate(createMockChat());
      });

      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'false');
        expect(button).not.toBeDisabled();
      });
    });

    it('prevents multiple simultaneous chat creation', async () => {
      let resolveCreate: any;
      const createPromise = new Promise((resolve) => {
        resolveCreate = resolve;
      });
      mockCreateChat.mockReturnValue(createPromise as any);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      // First click
      await act(async () => {
        fireEvent.click(button);
      });

      // Wait for loading state
      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });

      // Try to click again while loading - should be prevented
      await act(async () => {
        fireEvent.click(button);
        fireEvent.click(button);
      });

      // Should only call createChat once
      expect(mockCreateChat).toHaveBeenCalledTimes(1);

      // Resolve the promise
      await act(async () => {
        resolveCreate(createMockChat());
      });

      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'false');
      });
    });
  });

  describe('Edge Cases', () => {
    it('handles rapid consecutive clicks', async () => {
      // Use a Promise to control when the API call resolves
      let resolveCreate: any;
      const createPromise = new Promise((resolve) => {
        resolveCreate = resolve;
      });
      mockCreateChat.mockReturnValue(createPromise as any);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      // First click
      await act(async () => {
        fireEvent.click(button);
      });

      // Wait for loading state to be set
      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });

      // Additional rapid clicks while loading - should be ignored
      await act(async () => {
        fireEvent.click(button);
        fireEvent.click(button);
        fireEvent.click(button);
      });

      // Should only create one chat due to loading state
      expect(mockCreateChat).toHaveBeenCalledTimes(1);

      // Resolve the promise
      await act(async () => {
        resolveCreate(createMockChat());
      });

      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'false');
      });

      // Now we can click again
      mockCreateChat.mockResolvedValueOnce(
        createMockChat({ chat_id: 'chat-2' }),
      );

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API errors correctly', async () => {
      const mockError = new Error('API Error');
      mockCreateChat.mockRejectedValue(mockError);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
        expect(mockHandleError).toHaveBeenCalledWith(mockError);
      });

      // State should remain unchanged when error occurs
      const finalState = store.getState();
      expect(finalState.chats.totalChats).toBe(0);
      expect(finalState.chats.chats).toHaveLength(0);
      expect(finalState.chats.activeChat).toBeNull();
    });

    it('resets loading state after error', async () => {
      const mockError = new Error('API Error');
      mockCreateChat.mockRejectedValue(mockError);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(mockError);
      });

      // Button should not be loading after error
      expect(button).toHaveAttribute('data-loading', 'false');
      expect(button).not.toBeDisabled();
    });

    it('can retry after error', async () => {
      const mockError = new Error('API Error');
      mockCreateChat
        .mockRejectedValueOnce(mockError)
        .mockResolvedValueOnce(createMockChat());

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      // First attempt - should fail
      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(mockError);
      });

      // Second attempt - should succeed
      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalledTimes(2);
      });

      const finalState = store.getState();
      expect(finalState.chats.totalChats).toBe(1);
      expect(finalState.chats.chats).toHaveLength(1);
    });
  });

  describe('Edge Cases', () => {
    it('handles chat creation with no existing chats', async () => {
      const mockChatData = createMockChat();
      mockCreateChat.mockResolvedValue(mockChatData);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(mockCreateChat).toHaveBeenCalled();
      });

      const finalState = store.getState();
      expect(finalState.chats.chats).toHaveLength(1);
      expect(finalState.chats.totalChats).toBe(1);
    });

    it('handles rapid consecutive clicks', async () => {
      // Mock with a delay to simulate real API call
      let resolveCreate: any;
      const createPromise = new Promise((resolve) => {
        resolveCreate = resolve;
      });
      mockCreateChat.mockReturnValue(createPromise as any);

      const store = mockStore(defaultState);

      await act(async () => {
        renderLayout(<CreateChatButton />, { store });
      });

      const button = screen.getByRole('button');

      // First click
      await act(async () => {
        fireEvent.click(button);
      });

      // Wait for loading state to be set
      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'true');
      });

      // Now try additional clicks while still loading - these should be blocked
      fireEvent.click(button);
      fireEvent.click(button);

      // Should only have called createChat once
      expect(mockCreateChat).toHaveBeenCalledTimes(1);

      // Resolve the promise
      await act(async () => {
        resolveCreate(createMockChat());
      });

      // Wait for loading to complete
      await waitFor(() => {
        expect(button).toHaveAttribute('data-loading', 'false');
      });
    });
  });
});
