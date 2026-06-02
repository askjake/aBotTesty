// AppsContainer.test.tsx
import React from 'react';
import { screen } from '@testing-library/react';
import AppsContainer from '@shared/ui/components/containers/AppsContainer';
import { AppsContainerProps } from '@shared/ui/components/containers/AppsContainer/AppsContainer.props';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock AppsSidebar component
jest.mock('@shared/ui/components/organisms/Sidebars/AppsSidebar', () => ({
  __esModule: true,
  default: ({ menuItems }: any) => (
    <div data-testid='apps-sidebar'>
      {menuItems.map((item: any) => (
        <div key={item.key} data-testid={`menu-item-${item.key}`}>
          {item.label}
        </div>
      ))}
    </div>
  ),
}));

describe('AppsContainer Component', () => {
  const mockMenuItems = [
    { key: '1', label: 'Menu Item 1', value: 'item1' },
    { key: '2', label: 'Menu Item 2', value: 'item2' },
    { key: '3', label: 'Menu Item 3', value: 'item3' },
  ];

  const defaultProps: AppsContainerProps = {
    menuItems: mockMenuItems,
  };

  it('renders correctly with children', () => {
    renderLayout(
      <AppsContainer {...defaultProps}>
        <div data-testid='test-content'>Test Content</div>
      </AppsContainer>,
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders AppsSidebar with menu items', () => {
    renderLayout(<AppsContainer {...defaultProps} />);

    expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item-1')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item-2')).toBeInTheDocument();
    expect(screen.getByTestId('menu-item-3')).toBeInTheDocument();
  });

  it('renders with empty menu items', () => {
    renderLayout(<AppsContainer menuItems={[]} />);

    expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
    expect(screen.queryByTestId(/^menu-item-/)).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = renderLayout(
      <AppsContainer {...defaultProps} className='custom-class' />,
    );

    const appsContainer = container.querySelector('.apps-container');
    expect(appsContainer).toHaveClass('apps-container');
    expect(appsContainer).toHaveClass('custom-class');
  });

  it('applies default className when not provided', () => {
    const { container } = renderLayout(<AppsContainer {...defaultProps} />);

    const appsContainer = container.querySelector('.apps-container');
    expect(appsContainer).toHaveClass('apps-container');
  });

  it('passes additional Layout props', () => {
    const { container } = renderLayout(
      <AppsContainer
        {...defaultProps}
        data-testid='custom-container'
        style={{ padding: '20px' }}
      />,
    );

    const appsContainer = screen.getByTestId('custom-container');
    expect(appsContainer).toBeInTheDocument();
    expect(appsContainer).toHaveStyle({ padding: '20px' });
  });

  it('renders with hasSider prop', () => {
    const { container } = renderLayout(<AppsContainer {...defaultProps} />);

    const layout = container.querySelector('.ant-layout-has-sider');
    expect(layout).toBeInTheDocument();
  });

  it('renders nested Layout structure', () => {
    const { container } = renderLayout(<AppsContainer {...defaultProps} />);

    const layouts = container.querySelectorAll('.ant-layout');
    expect(layouts.length).toBeGreaterThan(1);
  });

  it('renders content area', () => {
    const { container } = renderLayout(
      <AppsContainer {...defaultProps}>
        <div>Content</div>
      </AppsContainer>,
    );

    const content = container.querySelector('.ant-layout-content');
    expect(content).toBeInTheDocument();
  });

  it('renders multiple children', () => {
    renderLayout(
      <AppsContainer {...defaultProps}>
        <div data-testid='child-1'>Child 1</div>
        <div data-testid='child-2'>Child 2</div>
        <div data-testid='child-3'>Child 3</div>
      </AppsContainer>,
    );

    expect(screen.getByTestId('child-1')).toBeInTheDocument();
    expect(screen.getByTestId('child-2')).toBeInTheDocument();
    expect(screen.getByTestId('child-3')).toBeInTheDocument();
  });

  it('passes menu items to AppsSidebar', () => {
    renderLayout(<AppsContainer {...defaultProps} />);

    expect(screen.getByText('Menu Item 1')).toBeInTheDocument();
    expect(screen.getByText('Menu Item 2')).toBeInTheDocument();
    expect(screen.getByText('Menu Item 3')).toBeInTheDocument();
  });

  it('renders without children', () => {
    const { container } = renderLayout(<AppsContainer {...defaultProps} />);

    const content = container.querySelector('.ant-layout-content');
    expect(content).toBeInTheDocument();
  });

  it('handles complex menu items structure', () => {
    const complexMenuItems = [
      {
        key: '1',
        label: 'Parent Item',
        value: 'parent',
        children: [
          { key: '1-1', label: 'Child Item 1', value: 'child1' },
          { key: '1-2', label: 'Child Item 2', value: 'child2' },
        ],
      },
    ];

    renderLayout(<AppsContainer menuItems={complexMenuItems} />);

    expect(screen.getByTestId('apps-sidebar')).toBeInTheDocument();
  });

  it('maintains layout structure with sidebar and content', () => {
    const { container } = renderLayout(
      <AppsContainer {...defaultProps}>
        <div>Main Content</div>
      </AppsContainer>,
    );

    const sidebar = screen.getByTestId('apps-sidebar');
    const content = screen.getByText('Main Content');

    expect(sidebar).toBeInTheDocument();
    expect(content).toBeInTheDocument();
  });
});
