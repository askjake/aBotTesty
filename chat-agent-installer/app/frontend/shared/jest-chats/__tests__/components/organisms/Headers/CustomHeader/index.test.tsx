// __tests__/components/organisms/Headers/CustomHeader/CustomHeader.test.tsx
import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import * as chatsServices from '@shared/ui/services/chats.services';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import CustomHeader from '@/components/organisms/Headers/CustomHeader';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import userEvent from '@testing-library/user-event';
import { RootStore } from '@shared/ui/types/store.types';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';

// Mock the actual components first
jest.mock('@/components/molecules/Buttons/CreateChatButton', () => {
  return function MockCreateChatButton({ disabled }: { disabled?: boolean }) {
    return (
      <button data-testid='create-chat-button' disabled={disabled}>
        Create Chat
      </button>
    );
  };
});

// Mock UserMenu component
jest.mock('@shared/ui/components/molecules/Header/UserMenu', () => {
  return function MockUserMenu({ children }: { children: React.ReactNode }) {
    return (
      <div data-testid='user-menu' role='button' tabIndex={0}>
        {children}
      </div>
    );
  };
});

// Mock next/dynamic to return components directly without loading state
jest.mock('next/dynamic', () => {
  return (importFunc: () => Promise<any>) => {
    const componentName = importFunc.toString();

    if (componentName.includes('CreateChatButton')) {
      return function MockCreateChatButton({
        disabled,
      }: {
        disabled?: boolean;
      }) {
        return (
          <button data-testid='create-chat-button' disabled={disabled}>
            Create Chat
          </button>
        );
      };
    }

    if (componentName.includes('UserMenu')) {
      return function MockUserMenu({
        children,
      }: {
        children: React.ReactNode;
      }) {
        return (
          <div data-testid='user-menu' role='button' tabIndex={0}>
            {children}
          </div>
        );
      };
    }

    // Default fallback
    // eslint-disable-next-line react/display-name
    return () => <div data-testid='dynamic-component'>Dynamic Component</div>;
  };
});

// Mock services
jest.mock('@shared/ui/services/chats.services', () => ({
  updateChat: jest.fn(),
}));

// Mock hooks
const mockHandleError = jest.fn();
jest.mock('@shared/ui/hooks/useHandleError.hook', () => {
  return jest.fn(() => mockHandleError);
});

// Store the callback for manual triggering
let useClickOutsideCallback: (() => void) | null = null;

// Mock for useClickOutside that captures the callback for manual triggering
jest.mock('@shared/ui/hooks/useClickOutside.hook', () => {
  return jest.fn((ref, callback) => {
    useClickOutsideCallback = callback;

    React.useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (
          ref.current &&
          ref.current.nativeElement &&
          !ref.current.nativeElement.contains(event.target as Node)
        ) {
          callback();
        }
      };

      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [ref, callback]);
  });
});

// Mock UserAvatar component
jest.mock('@shared/ui/components/atoms/Avatars/UserAvatar', () => {
  return function MockUserAvatar({
    userEmail,
    size,
  }: {
    userEmail?: string;
    size?: string;
  }) {
    return (
      <div
        data-testid='user-avatar'
        data-email={userEmail || ''}
        data-size={size || ''}
      >
        Avatar
      </div>
    );
  };
});

// Mock IconButton component
jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => {
  return function MockIconButton({ icon, onClick, type }: any) {
    return (
      <button data-testid='icon-button' onClick={onClick} data-type={type}>
        {icon}
      </button>
    );
  };
});

// Mock ThemeSwitcher component
jest.mock('@shared/ui/components/molecules/Switchers/ThemeSwitcher', () => {
  return function MockThemeSwitcher() {
    return (
      <div data-testid='theme-switcher' role='switch' aria-checked='false' />
    );
  };
});

// Mock Ant Design App hook
const mockMessage = {
  success: jest.fn(),
  error: jest.fn(),
};

jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  App: {
    useApp: () => ({ message: mockMessage }),
  },
}));

// Suppress act warnings for this test suite
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('act(...)') ||
        args[0].includes(
          'The current testing environment is not configured to support act',
        ))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('CustomHeader', () => {
  let store: ReturnType<typeof mockStore>;
  const mockUpdateChat = chatsServices.updateChat as jest.MockedFunction<
    typeof chatsServices.updateChat
  >;

  const createDefaultState = (): RootStore => ({
    settings: {
      collapsedSidebar: false,
      themeMode: 'light' as const,
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
      aiTyping: false,
      vaultModeRegistered: false,
      vaultMode: false,
      showEnableVaultModal: false,
      hasMoreChats: false,
      hasMoreMessages: false,
      totalChats: 0,
      activeChat: {
        chat_id: 'chat-1',
        title: 'Test Chat',
        favorite: false,
        active: true,
        vault_mode: false,
        status: ChatStatusEnum.NORMAL,
        status_msg: null,
        messages: {},
        last_message_at: customDayjs().toString(),
        owner_id: '1',
        created_at: customDayjs().toString(),
        group_id: null,
      },
      chats: [
        {
          chat_id: 'chat-1',
          title: 'Test Chat',
          favorite: false,
          active: true,
          vault_mode: false,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
          messages: {},
          last_message_at: customDayjs().toString(),
          owner_id: '1',
          created_at: customDayjs().toString(),
          group_id: null,
        },
      ],
    },
    chatsGroups: {
      chatsGroups: [],
      activeChatGroup: 'all',
    },
  });

  // Helper function to get the edit button
  const getEditButton = () => {
    const buttons = screen.queryAllByRole('button');
    // Find circle button with SVG that's not a test button
    return buttons.find((button) => {
      const hasSvg = button.querySelector('svg') !== null;
      const isNotTestButton = !button.getAttribute('data-testid');
      const hasCircleClass =
        button.className.includes('circle') ||
        button.className.includes('ant-btn-circle');
      return hasSvg && isNotTestButton && hasCircleClass;
    });
  };

  beforeEach(() => {
    store = mockStore(createDefaultState());
    jest.clearAllMocks();
    mockHandleError.mockClear();
    mockMessage.success.mockClear();
    mockMessage.error.mockClear();
    useClickOutsideCallback = null;
  });

  describe('Basic Rendering', () => {
    it('should render the header with correct test id', () => {
      renderLayout(<CustomHeader />, { store });

      expect(screen.getByTestId('custom-header')).toBeInTheDocument();
      expect(screen.getByTestId('custom-header')).toHaveClass('custom-header');
    });

    it('should apply custom className', () => {
      renderLayout(<CustomHeader className='test-class' />, { store });

      const header = screen.getByTestId('custom-header');
      expect(header).toHaveClass('custom-header', 'test-class');
    });

    it('should render user avatar with correct props', () => {
      renderLayout(<CustomHeader />, { store });

      const avatar = screen.getByTestId('user-avatar');
      expect(avatar).toHaveAttribute('data-email', 'test@example.com');
      expect(avatar).toHaveAttribute('data-size', 'large');
    });

    it('should render UserMenu component', () => {
      renderLayout(<CustomHeader />, { store });

      expect(screen.getByTestId('user-menu')).toBeInTheDocument();
    });

    it('should render UserAvatar inside UserMenu', () => {
      renderLayout(<CustomHeader />, { store });

      const userMenu = screen.getByTestId('user-menu');
      const avatar = screen.getByTestId('user-avatar');

      expect(userMenu).toContainElement(avatar);
    });

    it('should handle missing user email', () => {
      const noUserStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          user: undefined,
        },
      });

      renderLayout(<CustomHeader />, { store: noUserStore });

      const avatar = screen.getByTestId('user-avatar');
      expect(avatar).toHaveAttribute('data-email', '');
    });

    it('should render theme switcher', () => {
      renderLayout(<CustomHeader />, { store });

      expect(screen.getByTestId('theme-switcher')).toBeInTheDocument();
    });
  });

  describe('Sidebar Toggle', () => {
    it('should show sidebar toggle when sidebar is collapsed', () => {
      const collapsedStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          collapsedSidebar: true,
        },
      });

      renderLayout(<CustomHeader />, { store: collapsedStore });

      expect(screen.getByTestId('icon-button')).toBeInTheDocument();
    });

    it('should toggle sidebar when sidebar toggle is clicked', async () => {
      const user = userEvent.setup();
      const collapsedStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          collapsedSidebar: true,
        },
      });

      renderLayout(<CustomHeader />, { store: collapsedStore });

      await user.click(screen.getByTestId('icon-button'));

      const state = collapsedStore.getState();
      expect(state.settings.collapsedSidebar).toBe(false);
    });

    it('should not show sidebar toggle when sidebar is expanded', () => {
      renderLayout(<CustomHeader />, { store });

      expect(screen.queryByTestId('icon-button')).not.toBeInTheDocument();
    });
  });

  describe('Create Chat Button', () => {
    it('should show create chat button when showChats is true and sidebar is collapsed', () => {
      const collapsedStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          collapsedSidebar: true,
        },
      });

      renderLayout(<CustomHeader showChats />, { store: collapsedStore });

      const createChatButton = screen.getByTestId('create-chat-button');
      expect(createChatButton).toBeInTheDocument();
      expect(createChatButton).not.toBeDisabled();
    });

    it('should disable create chat button when AI is typing', () => {
      const typingStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          collapsedSidebar: true,
        },
        chats: {
          ...createDefaultState().chats,
          aiTyping: true,
        },
      });

      renderLayout(<CustomHeader showChats />, { store: typingStore });

      expect(screen.getByTestId('create-chat-button')).toBeDisabled();
    });

    it('should not show create chat button when showChats is false', () => {
      const collapsedStore = mockStore({
        ...createDefaultState(),
        settings: {
          ...createDefaultState().settings,
          collapsedSidebar: true,
        },
      });

      renderLayout(<CustomHeader showChats={false} />, {
        store: collapsedStore,
      });

      expect(
        screen.queryByTestId('create-chat-button'),
      ).not.toBeInTheDocument();
    });

    it('should not show create chat button when sidebar is expanded', () => {
      renderLayout(<CustomHeader showChats />, { store });

      expect(
        screen.queryByTestId('create-chat-button'),
      ).not.toBeInTheDocument();
    });
  });

  describe('Chat Title Display', () => {
    it('should display active chat title', () => {
      renderLayout(<CustomHeader />, { store });

      expect(screen.getByText('Test Chat')).toBeInTheDocument();
    });

    it('should not display title when no active chat', () => {
      const noActiveChatStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          activeChat: null,
        },
      });

      renderLayout(<CustomHeader />, { store: noActiveChatStore });

      expect(screen.queryByText('Test Chat')).not.toBeInTheDocument();
    });

    it('should render empty div when no active chat title', () => {
      const noTitleStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          activeChat: {
            ...createDefaultState().chats.activeChat!,
            title: '',
          },
        },
      });

      renderLayout(<CustomHeader />, { store: noTitleStore });

      expect(screen.getByTestId('custom-header')).toBeInTheDocument();
      expect(getEditButton()).toBeUndefined();
    });
  });

  describe('Chat Title Editing', () => {
    it('should show edit button for chat title when chat is not read-only', () => {
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      expect(editButton).toBeDefined();
    });

    it('should not show edit button when chat is read-only', () => {
      const readOnlyStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          activeChat: {
            ...createDefaultState().chats.activeChat!,
            status: ChatStatusEnum.READONLY,
          },
        },
      });

      renderLayout(<CustomHeader />, { store: readOnlyStore });

      const editButton = getEditButton();
      expect(editButton).toBeUndefined();
    });

    it('should show input field when edit button is clicked', async () => {
      const user = userEvent.setup();
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await user.click(editButton);
        expect(screen.getByDisplayValue('Test Chat')).toBeInTheDocument();
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should disable edit button when AI is typing', () => {
      const typingStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          aiTyping: true,
        },
      });

      renderLayout(<CustomHeader />, { store: typingStore });

      const editButton = getEditButton();
      expect(editButton).toBeDefined();
      if (editButton) {
        expect(editButton).toBeDisabled();
      }
    });

    it('should limit input maxLength to 50 characters', async () => {
      const user = userEvent.setup();
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await user.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        expect(input).toHaveAttribute('maxlength', '50');
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should update chat title successfully when valid title is provided', async () => {
      mockUpdateChat.mockResolvedValue({} as any);

      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        await userEvent.clear(input);
        await userEvent.type(input, 'Updated Chat Title');

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        await waitFor(() => {
          expect(mockUpdateChat).toHaveBeenCalledWith({
            id: 'chat-1',
            favorite: false,
            active: true,
            title: 'Updated Chat Title',
            group_id: null,
          });
        });

        expect(mockMessage.success).toHaveBeenCalledWith(
          "The chat's title has successfully updated",
        );
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should not update title if input is empty', async () => {
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        await userEvent.clear(input);

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        expect(mockUpdateChat).not.toHaveBeenCalled();
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should not update title if title is the same', async () => {
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        expect(mockUpdateChat).not.toHaveBeenCalled();
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should handle update chat error', async () => {
      mockUpdateChat.mockRejectedValue(new Error('Update failed'));

      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        await userEvent.clear(input);
        await userEvent.type(input, 'Updated Chat Title');

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        await waitFor(() => {
          expect(mockHandleError).toHaveBeenCalledWith(
            new Error('Update failed'),
          );
        });
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should close edit mode after successful update', async () => {
      mockUpdateChat.mockResolvedValue({} as any);

      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        await userEvent.clear(input);
        await userEvent.type(input, 'Updated Chat Title');

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        await waitFor(() => {
          expect(mockUpdateChat).toHaveBeenCalled();
        });

        await waitFor(() => {
          expect(
            screen.queryByDisplayValue('Updated Chat Title'),
          ).not.toBeInTheDocument();
        });
      } else {
        throw new Error('Edit button not found');
      }
    });
  });

  describe('Read-Only Chat Status', () => {
    it('should show read-only tag when chat status is read-only', () => {
      const readOnlyStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          activeChat: {
            ...createDefaultState().chats.activeChat!,
            status: ChatStatusEnum.READONLY,
          },
        },
      });

      renderLayout(<CustomHeader />, { store: readOnlyStore });

      expect(screen.getByText('Read-only')).toBeInTheDocument();
    });

    it('should not have edit button when chat is read-only', () => {
      const readOnlyStore = mockStore({
        ...createDefaultState(),
        chats: {
          ...createDefaultState().chats,
          activeChat: {
            ...createDefaultState().chats.activeChat!,
            status: ChatStatusEnum.READONLY,
          },
        },
      });

      renderLayout(<CustomHeader />, { store: readOnlyStore });

      expect(getEditButton()).toBeUndefined();
    });
  });

  describe('Edge Cases', () => {
    it('should handle very long titles', async () => {
      const user = userEvent.setup();
      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await user.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        const longTitle = 'A'.repeat(100);
        await userEvent.clear(input);
        await userEvent.type(input, longTitle);

        expect(input).toHaveValue('A'.repeat(50));
      } else {
        throw new Error('Edit button not found');
      }
    });

    it('should update store state after successful title change', async () => {
      mockUpdateChat.mockResolvedValue({} as any);

      renderLayout(<CustomHeader />, { store });

      const editButton = getEditButton();
      if (editButton) {
        await userEvent.click(editButton);

        const input = screen.getByDisplayValue('Test Chat');
        await userEvent.clear(input);
        await userEvent.type(input, 'New Title');

        act(() => {
          if (useClickOutsideCallback) {
            useClickOutsideCallback();
          }
        });

        await waitFor(() => {
          expect(mockUpdateChat).toHaveBeenCalled();
        });

        const state = store.getState();
        expect(state.chats.activeChat?.title).toBe('New Title');
        expect(state.chats.chats[0].title).toBe('New Title');
      } else {
        throw new Error('Edit button not found');
      }
    });
  });
});
