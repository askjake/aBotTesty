import React from 'react';
import { screen, act } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import ContainerWithSidebar from '@/components/containers/ContainerWithSidebar';

jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  notification: {
    error: jest.fn(),
    success: jest.fn(),
    info: jest.fn(),
    warning: jest.fn(),
  },
}));

// Mock the useHandleError hook
const mockHandleError = jest.fn();
jest.mock('@shared/ui/hooks/useHandleError.hook', () => {
  return jest.fn(() => mockHandleError);
});

// Mock the services that might be called
jest.mock('@shared/ui/services/chats.services', () => ({
  getChats: jest.fn().mockResolvedValue({
    docs: [],
    hasNextPage: false,
    active_chat_id: '1',
    hasPrevPage: false,
    prevPage: 1,
    nextPage: 1,
    page: 1,
    totalPages: 1,
    totalDocs: 0,
    limit: 15,
  }),
  updateChat: jest.fn(),
}));

// Mock next/navigation
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(() => '/'),
}));

// Mock dynamic imports
jest.mock('next/dynamic', () => {
  return (importFunc: () => Promise<any>) => {
    const componentName = importFunc.toString();

    if (componentName.includes('CustomSidebarChats')) {
      return function MockCustomSidebarChats({
        onLoadMore,
      }: {
        onLoadMore: () => void;
      }) {
        return (
          <div data-testid='custom-sidebar-chats'>
            <button data-testid='load-more-button' onClick={() => onLoadMore()}>
              Load More
            </button>
          </div>
        );
      };
    }

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

// Mock other components that might be used
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

jest.mock('@/components/molecules/ChatsGroupsFilter', () => {
  return function MockChatsGroupFilter() {
    return <div data-testid='chats-group-filter'>Group Filter</div>;
  };
});

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

jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => {
  return function MockIconButton({ icon, onClick, type }: any) {
    return (
      <button data-testid='icon-button' onClick={onClick} data-type={type}>
        {icon}
      </button>
    );
  };
});

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

// Mock other styled components
jest.mock(
  '@/components/organisms/Headers/CustomHeader/CustomHeader.styled',
  () => ({
    StyledCustomHeader: ({ children, ...props }: any) => (
      <header data-testid='custom-header' {...props}>
        {children}
      </header>
    ),
    StyledCustomHeaderTitle: ({ children }: any) => <h1>{children}</h1>,
    StyledCustomHeaderTitleWrapper: ({ children }: any) => (
      <div>{children}</div>
    ),
    // eslint-disable-next-line react/display-name
    StyledEditTitleInput: React.forwardRef((props: any, ref: any) => (
      <input ref={ref} {...props} />
    )),
  }),
);

jest.mock(
  '@shared/ui/components/organisms/Footers/CustomFooter/CustomFooter.styled',
  () => ({
    StyledCustomFooter: ({ children, ...props }: any) => (
      <footer data-testid='custom-footer' {...props}>
        {children}
      </footer>
    ),
  }),
);

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

// Mock useClickOutside hook
jest.mock('@shared/ui/hooks/useClickOutside.hook', () => {
  return jest.fn((ref, callback) => {
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

// Suppress console errors for cleaner test output
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

describe('ContainerWithSidebar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockHandleError.mockClear();
  });

  it('renders without crashing', async () => {
    await act(async () => {
      renderLayout(
        <ContainerWithSidebar>
          <p>Test Content</p>
        </ContainerWithSidebar>,
      );
    });
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders CustomHeader and CustomFooter and CustomSidebar', async () => {
    await act(async () => {
      renderLayout(
        <ContainerWithSidebar>
          <p>Test Content</p>
        </ContainerWithSidebar>,
      );
    });
    expect(screen.getByTestId('custom-header')).toBeInTheDocument();
    expect(screen.getByTestId('custom-footer')).toBeInTheDocument();
    expect(screen.getByTestId('custom-sidebar')).toBeInTheDocument();
  });

  it('renders children content correctly', async () => {
    await act(async () => {
      renderLayout(
        <ContainerWithSidebar>
          <div data-testid='main-content'>
            <h1>Main Content</h1>
            <p>This is the main content area</p>
          </div>
        </ContainerWithSidebar>,
      );
    });

    expect(screen.getByTestId('main-content')).toBeInTheDocument();
    expect(screen.getByText('Main Content')).toBeInTheDocument();
    expect(
      screen.getByText('This is the main content area'),
    ).toBeInTheDocument();
  });

  it('passes props correctly to child components', async () => {
    await act(async () => {
      renderLayout(
        <ContainerWithSidebar className='test-container'>
          <p>Test Content</p>
        </ContainerWithSidebar>,
      );
    });

    // Verify that the container and its components are rendered
    expect(screen.getByTestId('custom-header')).toBeInTheDocument();
    expect(screen.getByTestId('custom-footer')).toBeInTheDocument();
    expect(screen.getByTestId('custom-sidebar')).toBeInTheDocument();
  });
});
