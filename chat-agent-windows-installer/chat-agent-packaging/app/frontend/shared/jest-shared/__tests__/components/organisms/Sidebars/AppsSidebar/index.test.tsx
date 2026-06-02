// AppsSidebar.test.tsx
import React from 'react';
import { screen } from '@testing-library/react';
import AppsSidebar from '@shared/ui/components/organisms/Sidebars/AppsSidebar';
import { AppsSidebarProps } from '@shared/ui/components/organisms/Sidebars/AppsSidebar/AppsSidebar.props';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import { RootStore } from '@shared/ui/types/store.types';

// Mock next/navigation
const mockPathname = '/test-path';
jest.mock('next/navigation', () => ({
  usePathname: jest.fn(() => mockPathname),
}));

// Mock AppsSidebarHeader
jest.mock('@shared/ui/components/molecules/Sidebars/AppsSidebarHeader', () => ({
  __esModule: true,
  default: () => <div data-testid='apps-sidebar-header'>Header</div>,
}));

// Mock UserAvatar
jest.mock('@shared/ui/components/atoms/Avatars/UserAvatar', () => ({
  __esModule: true,
  default: ({ userEmail, size }: any) => (
    <div data-testid='user-avatar' data-email={userEmail} data-size={size}>
      Avatar
    </div>
  ),
}));

// Mock UserMenu
jest.mock('@shared/ui/components/molecules/Header/UserMenu', () => ({
  __esModule: true,
  default: ({ children, placement }: any) => (
    <div data-testid='user-menu' data-placement={placement}>
      {children}
    </div>
  ),
}));

// Mock Ant Design components
jest.mock('antd', () => {
  const React = require('react');

  // Mock Sider component
  const Sider = React.forwardRef(
    (
      {
        children,
        collapsed,
        collapsible,
        trigger,
        width,
        className = '',
        ...props
      }: any,
      ref: any,
    ) => {
      const collapsedClass = collapsed ? 'ant-layout-sider-collapsed' : '';
      return (
        <aside
          ref={ref}
          className={`ant-layout-sider ${collapsedClass} ${className}`}
          style={{ width: collapsed ? 80 : width }}
          {...props}
        >
          {children}
          {trigger !== null && (
            <div className='ant-layout-sider-trigger'>{trigger}</div>
          )}
        </aside>
      );
    },
  );
  Sider.displayName = 'Sider';

  // Mock Menu component
  const Menu = ({ items, selectedKeys, ...props }: any) => (
    <ul
      data-testid='menu'
      data-selected-keys={selectedKeys?.join(',')}
      {...props}
    >
      {items?.map((item: any) => (
        <li key={item.key} data-testid={`menu-item-${item.key}`}>
          {item.icon}
          {item.label}
        </li>
      ))}
    </ul>
  );

  return {
    Layout: {
      Sider,
    },
    Menu,
    Typography: {
      Text: ({ children, strong, ellipsis }: any) => (
        <span
          data-testid='typography-text'
          data-strong={strong}
          data-ellipsis={ellipsis}
        >
          {children}
        </span>
      ),
    },
    Flex: ({ children, align, gap }: any) => (
      <div data-testid='flex' data-align={align} data-gap={gap}>
        {children}
      </div>
    ),
  };
});

describe('AppsSidebar Component', () => {
  const mockMenuItems = [
    {
      key: '1',
      label: 'Dashboard',
      value: '/dashboard',
      icon: <span>📊</span>,
    },
    {
      key: '2',
      label: 'Settings',
      value: '/settings',
      icon: <span>⚙️</span>,
    },
    {
      key: '3',
      label: 'Profile',
      value: '/profile',
      icon: <span>👤</span>,
    },
  ];

  const defaultProps: AppsSidebarProps = {
    menuItems: mockMenuItems,
  };

  const createStoreState = (
    collapsedSidebar = false,
    userEmail = 'test@example.com',
  ): RootStore => ({
    settings: {
      themeMode: 'light',
      collapsedSidebar,
      releases: [],
      hasMoreReleases: false,
      showReleaseModal: false,
      user: {
        email: userEmail,
        first_name: 'Test',
        last_name: 'User',
        last_release_date: null,
      },
    },
    chats: {
      chats: [],
      activeChat: null,
      vaultMode: false,
      vaultModeRegistered: false,
      showEnableVaultModal: false,
      aiTyping: false,
      hasMoreChats: false,
      totalChats: 0,
    },
    chatsGroups: {
      chatsGroups: [],
      activeChatGroup: null,
    },
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders without crashing', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    });

    it('renders with default props', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar menuItems={[]} />, { store });

      expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} className='custom-class' />, {
        store,
      });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveClass('apps-sidebar');
      expect(sidebar).toHaveClass('custom-class');
    });

    it('renders all main components', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByTestId('apps-sidebar-header')).toBeInTheDocument();
      expect(screen.getByTestId('user-menu')).toBeInTheDocument();
      expect(screen.getByTestId('user-avatar')).toBeInTheDocument();
      expect(screen.getByTestId('menu')).toBeInTheDocument();
    });
  });

  describe('Sidebar State', () => {
    it('renders collapsed sidebar', () => {
      const store = mockStore(createStoreState(true));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveClass('ant-layout-sider-collapsed');
    });

    it('renders expanded sidebar', () => {
      const store = mockStore(createStoreState(false));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).not.toHaveClass('ant-layout-sider-collapsed');
    });

    it('has correct width when expanded', () => {
      const store = mockStore(createStoreState(false));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveStyle({ width: '320px' });
    });

    it('has correct width when collapsed', () => {
      const store = mockStore(createStoreState(true));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveStyle({ width: '80px' });
    });

    it('has trigger set to null', () => {
      const store = mockStore(createStoreState());
      const { container } = renderLayout(<AppsSidebar {...defaultProps} />, {
        store,
      });

      const trigger = container.querySelector('.ant-layout-sider-trigger');
      expect(trigger).not.toBeInTheDocument();
    });
  });

  describe('Menu Items', () => {
    it('renders menu with provided items', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByTestId('menu')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-2')).toBeInTheDocument();
      expect(screen.getByTestId('menu-item-3')).toBeInTheDocument();
    });

    it('renders menu item labels', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Profile')).toBeInTheDocument();
    });

    it('renders with empty menu items', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar menuItems={[]} />, { store });

      expect(screen.getByTestId('menu')).toBeInTheDocument();
      expect(screen.queryByTestId(/^menu-item-/)).not.toBeInTheDocument();
    });

    it('handles complex menu structure with children', () => {
      const complexMenuItems = [
        {
          key: '1',
          label: 'Parent',
          value: '/parent',
          children: [
            { key: '1-1', label: 'Child 1', value: '/parent/child1' },
            { key: '1-2', label: 'Child 2', value: '/parent/child2' },
          ],
        },
      ];

      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar menuItems={complexMenuItems} />, { store });

      expect(screen.getByTestId('menu')).toBeInTheDocument();
    });
  });

  describe('Selected Keys', () => {
    it('selects menu item based on current pathname', () => {
      const { usePathname } = require('next/navigation');
      usePathname.mockReturnValue('/dashboard');

      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const menu = screen.getByTestId('menu');
      expect(menu).toHaveAttribute('data-selected-keys', '1');
    });

    it('handles no matching pathname', () => {
      const { usePathname } = require('next/navigation');
      usePathname.mockReturnValue('/non-existent');

      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const menu = screen.getByTestId('menu');
      expect(menu).toHaveAttribute('data-selected-keys', '');
    });

    it('updates selected keys when pathname changes', () => {
      const { usePathname } = require('next/navigation');
      usePathname.mockReturnValue('/dashboard');

      const store = mockStore(createStoreState());
      const { rerender } = renderLayout(<AppsSidebar {...defaultProps} />, {
        store,
      });

      let menu = screen.getByTestId('menu');
      expect(menu).toHaveAttribute('data-selected-keys', '1');

      // Change pathname
      usePathname.mockReturnValue('/settings');

      rerender(<AppsSidebar {...defaultProps} />);

      menu = screen.getByTestId('menu');
      expect(menu).toHaveAttribute('data-selected-keys', '2');
    });
  });

  describe('User Information', () => {
    it('displays user email', () => {
      const store = mockStore(createStoreState(false, 'user@test.com'));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const userText = screen.getByTestId('typography-text');
      expect(userText).toHaveTextContent('user@test.com');
    });

    it('renders UserAvatar with correct props', () => {
      const store = mockStore(createStoreState(false, 'avatar@test.com'));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const avatar = screen.getByTestId('user-avatar');
      expect(avatar).toHaveAttribute('data-email', 'avatar@test.com');
      expect(avatar).toHaveAttribute('data-size', 'large');
    });

    it('handles missing user data gracefully', () => {
      const storeState = createStoreState();
      // @ts-ignore - Testing edge case
      storeState.settings.user = null;
      const store = mockStore(storeState);

      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    });

    it('applies text styling correctly', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const text = screen.getByTestId('typography-text');
      expect(text).toHaveAttribute('data-strong', 'true');
      expect(text).toHaveAttribute('data-ellipsis', 'true');
    });
  });

  describe('UserMenu', () => {
    it('renders UserMenu with correct placement', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const userMenu = screen.getByTestId('user-menu');
      expect(userMenu).toHaveAttribute('data-placement', 'top');
    });

    it('UserMenu contains user avatar and email', () => {
      const store = mockStore(createStoreState(false, 'menu@test.com'));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const userMenu = screen.getByTestId('user-menu');
      expect(userMenu).toBeInTheDocument();

      const avatar = screen.getByTestId('user-avatar');
      const text = screen.getByTestId('typography-text');

      expect(avatar).toBeInTheDocument();
      expect(text).toHaveTextContent('menu@test.com');
    });
  });

  describe('Layout Structure', () => {
    it('renders Flex container with correct props', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const flex = screen.getByTestId('flex');
      expect(flex).toHaveAttribute('data-align', 'center');
      expect(flex).toHaveAttribute('data-gap', '6');
    });

    it('renders as aside element', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar.tagName).toBe('ASIDE');
    });
  });

  describe('Props Forwarding', () => {
    it('forwards additional Sider props', () => {
      const store = mockStore(createStoreState());
      renderLayout(
        <AppsSidebar
          {...defaultProps}
          data-custom='test-value'
          style={{ backgroundColor: 'red' }}
        />,
        { store },
      );

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveAttribute('data-custom', 'test-value');
      expect(sidebar).toHaveStyle({ backgroundColor: 'red' });
    });

    it('allows width override', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} width={400} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveStyle({ width: '400px' });
    });
  });

  describe('Integration with Redux', () => {
    it('reads collapsedSidebar from Redux store', () => {
      const store = mockStore(createStoreState(true));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveClass('ant-layout-sider-collapsed');
    });

    it('reads user data from Redux store', () => {
      const store = mockStore(createStoreState(false, 'redux@test.com'));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const text = screen.getByTestId('typography-text');
      expect(text).toHaveTextContent('redux@test.com');
    });

    it('updates when Redux state changes', () => {
      const store = mockStore(createStoreState(false));
      const { rerender } = renderLayout(<AppsSidebar {...defaultProps} />, {
        store,
      });

      let sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).not.toHaveClass('ant-layout-sider-collapsed');

      // Update store
      store.dispatch({ type: 'settings/toggleSideBar' });

      rerender(<AppsSidebar {...defaultProps} />);

      sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveClass('ant-layout-sider-collapsed');
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined user gracefully', () => {
      const storeState = createStoreState();
      // @ts-ignore - Testing edge case
      storeState.settings.user = undefined;
      const store = mockStore(storeState);

      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    });

    it('handles very long user email', () => {
      const longEmail =
        'very.long.email.address.that.might.overflow@example.com';
      const store = mockStore(createStoreState(false, longEmail));
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const text = screen.getByTestId('typography-text');
      expect(text).toHaveTextContent(longEmail);
      expect(text).toHaveAttribute('data-ellipsis', 'true');
    });

    it('handles menu items without value property', () => {
      const itemsWithoutValue = [
        { key: '1', label: 'Item 1' },
        { key: '2', label: 'Item 2' },
      ];

      const store = mockStore(createStoreState());
      // @ts-ignore - Testing edge case
      renderLayout(<AppsSidebar menuItems={itemsWithoutValue} />, { store });

      expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('renders semantic HTML structure', () => {
      const store = mockStore(createStoreState());
      const { container } = renderLayout(<AppsSidebar {...defaultProps} />, {
        store,
      });

      const sidebar = container.querySelector('aside');
      expect(sidebar).toBeInTheDocument();
    });

    it('has proper sidebar class', () => {
      const store = mockStore(createStoreState());
      renderLayout(<AppsSidebar {...defaultProps} />, { store });

      const sidebar = screen.getByTestId('apps-sidebar');
      expect(sidebar).toHaveClass('ant-layout-sider');
    });
  });
});
