import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserMenu from '@shared/ui/components/molecules/Header/UserMenu';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';

// Mock next/dynamic
jest.mock('next/dynamic', () => {
  return jest.fn(() => {
    const MockedReleasesNotesDrawer = ({ open, onClose, ...props }: any) => (
      <div data-testid='releases-notes-drawer' data-open={open} {...props}>
        <div>Releases Notes Drawer</div>
        <button data-testid='close-drawer-button' onClick={onClose}>
          Close
        </button>
      </div>
    );
    MockedReleasesNotesDrawer.displayName = 'ReleasesNotesDrawer';
    return MockedReleasesNotesDrawer;
  });
});

// Mock Ant Design components
jest.mock('antd', () => ({
  Dropdown: ({ children, menu, trigger, ...props }: any) => (
    <div data-testid='dropdown' data-trigger={trigger?.join(',')} {...props}>
      {children}
      <div data-testid='dropdown-menu'>
        {menu?.items?.map((item: any, index: number) => (
          <div
            key={item.key || index}
            data-testid={`menu-item-${item.key}`}
            onClick={item.onClick}
            role='menuitem'
          >
            <span data-testid={`menu-item-icon-${item.key}`}>{item.icon}</span>
            <span data-testid={`menu-item-label-${item.key}`}>
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  ),
}));

// Mock Ant Design icons
jest.mock('@ant-design/icons', () => ({
  QuestionCircleOutlined: () => (
    <span data-testid='question-circle-icon'>?</span>
  ),
}));

describe('UserMenu', () => {
  const renderComponent = (props = {}) => {
    const store = mockStore({
      settings: {
        releases: [
          {
            title: 'Release 1.0.0',
            date: '2024-01-01',
            changes: ['Test change'],
          },
        ],
      },
    });

    return renderLayout(
      <UserMenu {...props}>
        <button data-testid='trigger-button'>User Menu</button>
      </UserMenu>,
      { store },
    );
  };

  it('should render dropdown with children', () => {
    renderComponent();

    expect(screen.getByTestId('dropdown')).toBeInTheDocument();
    expect(screen.getByTestId('trigger-button')).toBeInTheDocument();
    expect(screen.getByText('User Menu')).toBeInTheDocument();
  });

  it('should render "What\'s new?" menu item', () => {
    renderComponent();

    expect(screen.getByTestId('menu-item-0')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item-label-0')).toHaveTextContent(
      "What's new?",
    );
    expect(screen.getByTestId('question-circle-icon')).toBeInTheDocument();
  });

  it('should render releases notes drawer initially closed', () => {
    renderComponent();

    const drawer = screen.getByTestId('releases-notes-drawer');
    expect(drawer).toBeInTheDocument();
    expect(drawer).toHaveAttribute('data-open', 'false');
  });

  it('should open releases drawer when menu item is clicked', async () => {
    const user = userEvent.setup();
    renderComponent();

    const menuItem = screen.getByTestId('menu-item-0');
    await user.click(menuItem);

    const drawer = screen.getByTestId('releases-notes-drawer');
    expect(drawer).toHaveAttribute('data-open', 'true');
  });

  it('should close releases drawer when onClose is called', async () => {
    const user = userEvent.setup();
    renderComponent();

    // Open the drawer
    const menuItem = screen.getByTestId('menu-item-0');
    await user.click(menuItem);

    expect(screen.getByTestId('releases-notes-drawer')).toHaveAttribute(
      'data-open',
      'true',
    );

    // Close the drawer
    const closeButton = screen.getByTestId('close-drawer-button');
    await user.click(closeButton);

    expect(screen.getByTestId('releases-notes-drawer')).toHaveAttribute(
      'data-open',
      'false',
    );
  });

  it('should have correct dropdown trigger', () => {
    renderComponent();

    const dropdown = screen.getByTestId('dropdown');
    expect(dropdown).toHaveAttribute('data-trigger', 'click');
  });

  it('should handle menu item click with fireEvent', () => {
    renderComponent();

    const menuItem = screen.getByTestId('menu-item-0');
    fireEvent.click(menuItem);

    const drawer = screen.getByTestId('releases-notes-drawer');
    expect(drawer).toHaveAttribute('data-open', 'true');
  });
});
