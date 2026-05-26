// AppsSidebarHeader.test.tsx
import React from 'react';
import { screen, fireEvent, act } from '@testing-library/react';
import AppsSidebarHeader from '@shared/ui/components/molecules/Sidebars/AppsSidebarHeader';
import { AppsSidebarHeaderProps } from '@shared/ui/components/molecules/Sidebars/AppsSidebarHeader/AppsSidebarHeader.props';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { RootStore } from '@shared/ui/types/store.types';

// Mock ThemeSwitcher component
jest.mock('@shared/ui/components/molecules/Switchers/ThemeSwitcher', () => ({
  __esModule: true,
  default: () => <div data-testid='theme-switcher'>Theme Switcher</div>,
}));

// Mock IconButton component
jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => ({
  __esModule: true,
  default: ({ onClick, icon, ...props }: any) => (
    <button onClick={onClick} data-testid='icon-button' {...props}>
      {icon}
    </button>
  ),
}));

describe('AppsSidebarHeader Component', () => {
  const initialState: Partial<RootStore> = {
    settings: {
      collapsedSidebar: false,
      themeMode: 'light',
      releases: [],
      hasMoreReleases: false,
      showReleaseModal: false,
      user: {
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        last_release_date: null,
      },
    },
  };

  const defaultProps: AppsSidebarHeaderProps = {};

  it('renders correctly when sidebar is expanded', () => {
    const store = mockStore(initialState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    expect(screen.getByTestId('theme-switcher')).toBeInTheDocument();
    expect(screen.getByTestId('icon-button')).toBeInTheDocument();
  });

  it('renders correctly when sidebar is collapsed', () => {
    const collapsedState: Partial<RootStore> = {
      ...initialState,
      settings: {
        ...initialState.settings!,
        collapsedSidebar: true,
      },
    };

    const store = mockStore(collapsedState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    expect(screen.queryByTestId('theme-switcher')).not.toBeInTheDocument();
    expect(screen.getByTestId('icon-button')).toBeInTheDocument();
  });

  it('displays MenuFoldOutlined icon when sidebar is expanded', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const foldIcon = container.querySelector('.anticon-menu-fold');
    expect(foldIcon).toBeInTheDocument();
  });

  it('displays MenuUnfoldOutlined icon when sidebar is collapsed', () => {
    const collapsedState: Partial<RootStore> = {
      ...initialState,
      settings: {
        ...initialState.settings!,
        collapsedSidebar: true,
      },
    };

    const store = mockStore(collapsedState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const unfoldIcon = container.querySelector('.anticon-menu-unfold');
    expect(unfoldIcon).toBeInTheDocument();
  });

  it('shows "Hide sidebar" tooltip when sidebar is expanded', async () => {
    const store = mockStore(initialState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    const button = screen.getByTestId('icon-button');

    await act(async () => {
      fireEvent.mouseEnter(button);
    });

    expect(await screen.findByText('Hide sidebar')).toBeInTheDocument();
  });

  it('shows "Show sidebar" tooltip when sidebar is collapsed', async () => {
    const collapsedState: Partial<RootStore> = {
      ...initialState,
      settings: {
        ...initialState.settings!,
        collapsedSidebar: true,
      },
    };

    const store = mockStore(collapsedState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    const button = screen.getByTestId('icon-button');

    await act(async () => {
      fireEvent.mouseEnter(button);
    });

    expect(await screen.findByText('Show sidebar')).toBeInTheDocument();
  });

  it('toggles sidebar state when button is clicked', async () => {
    const store = mockStore(initialState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    const initialCollapsed = store.getState().settings.collapsedSidebar;
    const button = screen.getByTestId('icon-button');

    await act(async () => {
      fireEvent.click(button);
    });

    const finalCollapsed = store.getState().settings.collapsedSidebar;
    expect(finalCollapsed).toBe(!initialCollapsed);
  });

  it('applies custom className', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} className='custom-class' />,
      { store },
    );

    const header = container.querySelector('.apps-sidebar-header');
    expect(header).toHaveClass('apps-sidebar-header');
    expect(header).toHaveClass('custom-class');
  });

  it('applies default className when not provided', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const header = container.querySelector('.apps-sidebar-header');
    expect(header).toHaveClass('apps-sidebar-header');
  });

  it('passes additional HTML div props', () => {
    const store = mockStore(initialState);
    renderLayout(
      <AppsSidebarHeader
        {...defaultProps}
        data-testid='custom-header'
        style={{ padding: '20px' }}
      />,
      { store },
    );

    const header = screen.getByTestId('custom-header');
    expect(header).toBeInTheDocument();
    expect(header).toHaveStyle({ padding: '20px' });
  });

  it('hides ThemeSwitcher when sidebar is collapsed', () => {
    const collapsedState: Partial<RootStore> = {
      ...initialState,
      settings: {
        ...initialState.settings!,
        collapsedSidebar: true,
      },
    };

    const store = mockStore(collapsedState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    expect(screen.queryByTestId('theme-switcher')).not.toBeInTheDocument();
  });

  it('toggles sidebar state multiple times', async () => {
    const store = mockStore(initialState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    const button = screen.getByTestId('icon-button');
    const initialCollapsed = store.getState().settings.collapsedSidebar;

    await act(async () => {
      fireEvent.click(button);
    });

    const afterFirstClick = store.getState().settings.collapsedSidebar;
    expect(afterFirstClick).toBe(!initialCollapsed);

    await act(async () => {
      fireEvent.click(button);
    });

    const afterSecondClick = store.getState().settings.collapsedSidebar;
    expect(afterSecondClick).toBe(initialCollapsed);
  });

  it('renders with correct header structure', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const headerWrapper = container.querySelector('.apps-sidebar-header');
    const header = container.querySelector('header');

    expect(headerWrapper).toBeInTheDocument();
    expect(header).toBeInTheDocument();
  });

  it('has sticky positioning on header', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const header = container.querySelector('header');
    expect(header).toHaveStyle({ position: 'sticky' });
  });

  it('applies correct justification when collapsed', () => {
    const collapsedState: Partial<RootStore> = {
      ...initialState,
      settings: {
        ...initialState.settings!,
        collapsedSidebar: true,
      },
    };

    const store = mockStore(collapsedState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const header = container.querySelector('header');
    expect(header).toHaveStyle({ justifyContent: 'center' });
  });

  it('applies correct justification when expanded', () => {
    const store = mockStore(initialState);
    const { container } = renderLayout(
      <AppsSidebarHeader {...defaultProps} />,
      { store },
    );

    const header = container.querySelector('header');
    expect(header).toHaveStyle({ justifyContent: 'space-between' });
  });

  it('renders IconButton with text type', () => {
    const store = mockStore(initialState);
    renderLayout(<AppsSidebarHeader {...defaultProps} />, { store });

    const button = screen.getByTestId('icon-button');
    expect(button).toHaveAttribute('type', 'text');
  });
});
