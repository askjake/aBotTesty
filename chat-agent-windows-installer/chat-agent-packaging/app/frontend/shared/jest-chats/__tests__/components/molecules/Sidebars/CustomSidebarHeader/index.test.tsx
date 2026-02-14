import React from 'react';
import { screen, fireEvent, act } from '@testing-library/react';

// Mock the reducers BEFORE importing anything else
jest.mock('@shared/ui/store/settings/settings.slice', () => ({
  settingsReducer: (
    state = { themeMode: 'light', collapsedSidebar: false },
    action: any,
  ) => {
    switch (action.type) {
      case 'settings/toggleSideBar':
        return { ...state, collapsedSidebar: !state.collapsedSidebar };
      default:
        return state;
    }
  },
  toggleSideBar: jest.fn(() => ({ type: 'settings/toggleSideBar' })),
}));

jest.mock('@shared/ui/store/chats/chats.slice', () => ({
  chatsReducer: (
    state = {
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      totalChats: 0,
    },
    action: any,
  ) => {
    switch (action.type) {
      case 'chats/setAiTyping':
        return { ...state, aiTyping: action.payload };
      default:
        return state;
    }
  },
}));

// Mock the dynamic button components
jest.mock('@/components/molecules/Buttons/CreateChatButton', () => {
  const MockCreateChatButton = ({ disabled, ...props }: any) => (
    <button
      data-testid='create-chat-button'
      data-disabled={disabled}
      {...props}
    >
      Create Chat
    </button>
  );
  MockCreateChatButton.displayName = 'CreateChatButton';
  return { __esModule: true, default: MockCreateChatButton };
});

jest.mock('@/components/molecules/Buttons/VaultModeButton', () => {
  const MockVaultModeButton = ({ disabled, ...props }: any) => (
    <button data-testid='vault-mode-button' data-disabled={disabled} {...props}>
      Vault Mode
    </button>
  );
  MockVaultModeButton.displayName = 'VaultModeButton';
  return { __esModule: true, default: MockVaultModeButton };
});

jest.mock('@/components/molecules/Buttons/SearchChatsButton', () => {
  const MockSearchChatsButton = ({ disabled, ...props }: any) => (
    <button
      data-testid='search-chats-button'
      data-disabled={disabled}
      {...props}
    >
      Search Chats
    </button>
  );
  MockSearchChatsButton.displayName = 'SearchChatsButton';
  return { __esModule: true, default: MockSearchChatsButton };
});

// Mock Next.js dynamic imports - much simpler approach
jest.mock('next/dynamic', () => {
  return (importFunc: any) => {
    // Create a component that renders the mocked components directly
    const DynamicComponent = (props: any) => {
      // Get the import function as string to determine which component to render
      const funcString = importFunc.toString();

      if (funcString.includes('CreateChatButton')) {
        return (
          <button
            data-testid='create-chat-button'
            data-disabled={props.disabled}
            {...props}
          >
            Create Chat
          </button>
        );
      }

      if (funcString.includes('VaultModeButton')) {
        return (
          <button
            data-testid='vault-mode-button'
            data-disabled={props.disabled}
            {...props}
          >
            Vault Mode
          </button>
        );
      }

      if (funcString.includes('SearchChatsButton')) {
        return (
          <button
            data-testid='search-chats-button'
            data-disabled={props.disabled}
            {...props}
          >
            Search Chats
          </button>
        );
      }

      // Fallback
      return (
        <div data-testid='dynamic-fallback' {...props}>
          Dynamic Component
        </div>
      );
    };

    DynamicComponent.displayName = 'DynamicComponent';
    return DynamicComponent;
  };
});

// Now import the rest
import { toggleSideBar } from '@shared/ui/store/settings/settings.slice';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import CustomSidebarHeader from '@/components/molecules/Sidebars/CustomSidebarHeader';

// Mock Ant Design components
jest.mock('antd', () => ({
  Skeleton: {
    Button: ({ active, shape, ...props }: any) => (
      <div
        data-testid='skeleton-button'
        data-active={active}
        data-shape={shape}
        {...props}
      />
    ),
  },
  Tooltip: ({ title, children }: any) => (
    <div data-testid='tooltip' title={title}>
      {children}
    </div>
  ),
}));

// Mock Ant Design icons
jest.mock('@ant-design/icons', () => ({
  MenuFoldOutlined: () => <div data-testid='menu-fold-icon'>MenuFoldIcon</div>,
}));

// Mock styled components
jest.mock(
  '@/components/molecules/Sidebars/CustomSidebarHeader/CustomSidebarHeader.styled',
  () => ({
    StyledCustomSidebarHeaderWrapper: ({
      children,
      className,
      ...props
    }: any) => (
      <div data-testid='styled-header-wrapper' className={className} {...props}>
        {children}
      </div>
    ),
    StyledCustomSidebarHeader: ({ children, ...props }: any) => (
      <header data-testid='styled-header' {...props}>
        {children}
      </header>
    ),
    StyledCustomSidebarButtonsList: ({ children, ...props }: any) => (
      <div data-testid='styled-buttons-list' {...props}>
        {children}
      </div>
    ),
  }),
);

// Mock IconButton component
jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => {
  return function MockIconButton({ type, icon, onClick, ...props }: any) {
    return (
      <button
        data-testid='icon-button'
        data-type={type}
        onClick={onClick}
        {...props}
      >
        {icon}
      </button>
    );
  };
});

const mockToggleSideBar = toggleSideBar as jest.MockedFunction<
  typeof toggleSideBar
>;

describe('CustomSidebarHeader', () => {
  const defaultProps = {
    showChats: false,
  };

  const defaultState = {
    settings: {
      themeMode: 'light' as const,
      collapsedSidebar: false,
    },
    chats: {
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: true,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      totalChats: 0,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the component with basic structure', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} />, { store });
    });

    expect(screen.getByTestId('styled-header-wrapper')).toBeInTheDocument();
    expect(screen.getByTestId('styled-header')).toBeInTheDocument();
    expect(screen.getByTestId('icon-button')).toBeInTheDocument();
    expect(screen.getByTestId('tooltip')).toBeInTheDocument();
    expect(screen.getByTestId('styled-buttons-list')).toBeInTheDocument();
  });

  it('renders tooltip with correct title', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} />, { store });
    });

    const tooltip = screen.getByTestId('tooltip');
    expect(tooltip).toHaveAttribute('title', 'Hide sidebar');
  });

  it('renders MenuFoldOutlined icon in the button', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} />, { store });
    });

    expect(screen.getByTestId('menu-fold-icon')).toBeInTheDocument();
  });

  it('dispatches toggleSideBar action when icon button is clicked', async () => {
    const store = mockStore(defaultState);
    const mockDispatch = jest.fn();
    store.dispatch = mockDispatch;

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} />, { store });
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('icon-button'));
    });

    expect(mockToggleSideBar).toHaveBeenCalled();
    expect(mockDispatch).toHaveBeenCalledWith({
      type: 'settings/toggleSideBar',
    });
  });

  it('renders chat buttons when showChats is true', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} showChats={true} />, {
        store,
      });
    });

    expect(screen.getByTestId('search-chats-button')).toBeInTheDocument();
    expect(screen.getByTestId('vault-mode-button')).toBeInTheDocument();
    expect(screen.getByTestId('create-chat-button')).toBeInTheDocument();
  });

  it('does not render chat buttons when showChats is false', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(
        <CustomSidebarHeader {...defaultProps} showChats={false} />,
        {
          store,
        },
      );
    });

    expect(screen.queryByTestId('search-chats-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('vault-mode-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('create-chat-button')).not.toBeInTheDocument();
  });

  it('renders buttons in correct order when showChats is true', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} showChats={true} />, {
        store,
      });
    });

    const buttonsList = screen.getByTestId('styled-buttons-list');
    const buttons = buttonsList.querySelectorAll('button');

    expect(buttons[0]).toHaveAttribute('data-testid', 'search-chats-button');
    expect(buttons[1]).toHaveAttribute('data-testid', 'vault-mode-button');
    expect(buttons[2]).toHaveAttribute('data-testid', 'create-chat-button');
  });

  it('disables all chat buttons when AI is typing', async () => {
    const stateWithAiTyping = {
      ...defaultState,
      chats: { ...defaultState.chats, aiTyping: true },
    };
    const store = mockStore(stateWithAiTyping);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} showChats={true} />, {
        store,
      });
    });

    expect(screen.getByTestId('search-chats-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.getByTestId('vault-mode-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.getByTestId('create-chat-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
  });

  it('enables all chat buttons when AI is not typing', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} showChats={true} />, {
        store,
      });
    });

    expect(screen.getByTestId('search-chats-button')).toHaveAttribute(
      'data-disabled',
      'false',
    );
    expect(screen.getByTestId('vault-mode-button')).toHaveAttribute(
      'data-disabled',
      'false',
    );
    expect(screen.getByTestId('create-chat-button')).toHaveAttribute(
      'data-disabled',
      'false',
    );
  });

  it('applies custom className correctly', async () => {
    const store = mockStore(defaultState);
    const customClassName = 'custom-test-class';

    await act(async () => {
      renderLayout(
        <CustomSidebarHeader {...defaultProps} className={customClassName} />,
        { store },
      );
    });

    const wrapper = screen.getByTestId('styled-header-wrapper');
    expect(wrapper).toHaveClass(`custom-sidebar-header ${customClassName}`);
  });

  it('applies default className when no custom className provided', async () => {
    const store = mockStore(defaultState);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} />, { store });
    });

    const wrapper = screen.getByTestId('styled-header-wrapper');
    expect(wrapper).toHaveClass('custom-sidebar-header');
  });

  it('passes additional props to the wrapper component', async () => {
    const store = mockStore(defaultState);
    const additionalProps = {
      'data-custom': 'test-value',
      id: 'custom-id',
    };

    await act(async () => {
      renderLayout(
        <CustomSidebarHeader {...defaultProps} {...additionalProps} />,
        { store },
      );
    });

    const wrapper = screen.getByTestId('styled-header-wrapper');
    expect(wrapper).toHaveAttribute('data-custom', 'test-value');
    expect(wrapper).toHaveAttribute('id', 'custom-id');
  });

  it('uses aiTyping state from Redux store', async () => {
    const stateWithAiTyping = {
      ...defaultState,
      chats: { ...defaultState.chats, aiTyping: true },
    };
    const store = mockStore(stateWithAiTyping);

    await act(async () => {
      renderLayout(<CustomSidebarHeader {...defaultProps} showChats={true} />, {
        store,
      });
    });

    // Verify that the aiTyping state is being used correctly
    expect(screen.getByTestId('search-chats-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.getByTestId('vault-mode-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
    expect(screen.getByTestId('create-chat-button')).toHaveAttribute(
      'data-disabled',
      'true',
    );
  });
});
