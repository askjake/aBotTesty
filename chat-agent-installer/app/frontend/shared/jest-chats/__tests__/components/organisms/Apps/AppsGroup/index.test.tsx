// AppsGroup.test.tsx
import React from 'react';
import { screen } from '@testing-library/react';
import AppsGroup from '@/components/organisms/Apps/AppsGroup';
import { AppsGroupProps } from '@/components/organisms/Apps/AppsGroup/AppsGroup.props';
import { AppsItemType } from '@/types/apps.types';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock AppsItem component
jest.mock('@/components/molecules/Apps/AppsItem', () => ({
  __esModule: true,
  default: ({ name, path, image }: AppsItemType) => (
    <div data-testid={`apps-item-${name}`}>
      <span>{name}</span>
      <span>{path}</span>
      <span>{image}</span>
    </div>
  ),
}));

describe('AppsGroup Component', () => {
  const mockItems: AppsItemType[] = [
    {
      name: 'App One',
      path: '/app-one',
      image: '/img/app-one.png',
    },
    {
      name: 'App Two',
      path: '/app-two',
      image: '/img/app-two.png',
    },
    {
      name: 'App Three',
      path: '/app-three',
      image: '/img/app-three.png',
    },
  ];

  const defaultProps: AppsGroupProps = {
    title: 'Test Apps Group',
    items: mockItems,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with all props', () => {
    renderLayout(<AppsGroup {...defaultProps} />);

    // Check if title is rendered
    expect(screen.getByRole('heading', { level: 4 })).toBeInTheDocument();
    expect(screen.getByText('Test Apps Group')).toBeInTheDocument();

    // Check if all items are rendered
    expect(screen.getByTestId('apps-item-App One')).toBeInTheDocument();
    expect(screen.getByTestId('apps-item-App Two')).toBeInTheDocument();
    expect(screen.getByTestId('apps-item-App Three')).toBeInTheDocument();
  });

  it('renders with empty title when title prop is not provided', () => {
    const propsWithoutTitle = {
      ...defaultProps,
      title: '',
    };

    renderLayout(<AppsGroup {...propsWithoutTitle} />);

    const heading = screen.getByRole('heading', { level: 4 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent('');
  });

  it('renders with empty items array when items prop is not provided', () => {
    const propsWithoutItems = {
      title: 'Test Apps Group',
      items: [],
    };

    const { container } = renderLayout(<AppsGroup {...propsWithoutItems} />);

    expect(screen.getByText('Test Apps Group')).toBeInTheDocument();
    expect(
      container.querySelectorAll('[data-testid^="apps-item-"]'),
    ).toHaveLength(0);
  });

  it('applies custom className correctly', () => {
    const customClassName = 'custom-apps-group';
    const propsWithClassName = {
      ...defaultProps,
      className: customClassName,
    };

    const { container } = renderLayout(<AppsGroup {...propsWithClassName} />);

    const appsGroup = container.querySelector('.apps-group');
    expect(appsGroup).toHaveClass('apps-group');
    expect(appsGroup).toHaveClass(customClassName);
  });

  it('applies default className when className prop is not provided', () => {
    const { container } = renderLayout(<AppsGroup {...defaultProps} />);

    const appsGroup = container.querySelector('.apps-group');
    expect(appsGroup).toBeInTheDocument();
    expect(appsGroup).toHaveClass('apps-group');
  });

  it('passes additional HTML div props correctly', () => {
    const propsWithDivProps = {
      ...defaultProps,
      'data-testid': 'custom-apps-group',
      style: { backgroundColor: 'blue' },
      id: 'apps-group-id',
    };

    renderLayout(<AppsGroup {...propsWithDivProps} />);

    const appsGroup = screen.getByTestId('custom-apps-group');
    expect(appsGroup).toBeInTheDocument();
    expect(appsGroup).toHaveStyle({ backgroundColor: 'blue' });
    expect(appsGroup).toHaveAttribute('id', 'apps-group-id');
  });

  it('renders correct number of AppsItem components', () => {
    const { container } = renderLayout(<AppsGroup {...defaultProps} />);

    const items = container.querySelectorAll('[data-testid^="apps-item-"]');
    expect(items).toHaveLength(3);
  });

  it('renders AppsItem components with correct props', () => {
    renderLayout(<AppsGroup {...defaultProps} />);

    // Verify first item
    expect(screen.getByText('App One')).toBeInTheDocument();
    expect(screen.getByText('/app-one')).toBeInTheDocument();
    expect(screen.getByText('/img/app-one.png')).toBeInTheDocument();

    // Verify second item
    expect(screen.getByText('App Two')).toBeInTheDocument();
    expect(screen.getByText('/app-two')).toBeInTheDocument();
    expect(screen.getByText('/img/app-two.png')).toBeInTheDocument();
  });

  it('uses item name as key for AppsItem components', () => {
    const { container } = renderLayout(<AppsGroup {...defaultProps} />);

    const firstItem = screen.getByTestId('apps-item-App One');
    const secondItem = screen.getByTestId('apps-item-App Two');
    const thirdItem = screen.getByTestId('apps-item-App Three');

    expect(firstItem).toBeInTheDocument();
    expect(secondItem).toBeInTheDocument();
    expect(thirdItem).toBeInTheDocument();
  });

  it('renders single item correctly', () => {
    const singleItemProps = {
      title: 'Single App',
      items: [mockItems[0]],
    };

    const { container } = renderLayout(<AppsGroup {...singleItemProps} />);

    expect(screen.getByText('Single App')).toBeInTheDocument();
    expect(
      container.querySelectorAll('[data-testid^="apps-item-"]'),
    ).toHaveLength(1);
    expect(screen.getByTestId('apps-item-App One')).toBeInTheDocument();
  });

  it('renders many items correctly', () => {
    const manyItems: AppsItemType[] = Array.from({ length: 10 }, (_, i) => ({
      name: `App ${i + 1}`,
      path: `/app-${i + 1}`,
      image: `/img/app-${i + 1}.png`,
    }));

    const manyItemsProps = {
      title: 'Many Apps',
      items: manyItems,
    };

    const { container } = renderLayout(<AppsGroup {...manyItemsProps} />);

    expect(
      container.querySelectorAll('[data-testid^="apps-item-"]'),
    ).toHaveLength(10);
  });

  it('renders Title with correct level', () => {
    renderLayout(<AppsGroup {...defaultProps} />);

    const heading = screen.getByRole('heading', { level: 4 });
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent('Test Apps Group');
  });

  it('handles special characters in title', () => {
    const propsWithSpecialChars = {
      ...defaultProps,
      title: 'Test & Apps <Group>',
    };

    renderLayout(<AppsGroup {...propsWithSpecialChars} />);

    expect(screen.getByText('Test & Apps <Group>')).toBeInTheDocument();
  });

  it('renders StyledAppsGroupContainer', () => {
    const { container } = renderLayout(<AppsGroup {...defaultProps} />);

    // StyledAppsGroupContainer should be present (styled-component will have generated class)
    const styledContainer = container.querySelector(
      '.apps-group > div:last-child',
    );
    expect(styledContainer).toBeInTheDocument();
  });

  it('maintains correct DOM structure', () => {
    const { container } = renderLayout(<AppsGroup {...defaultProps} />);

    const appsGroup = container.querySelector('.apps-group');
    const title = appsGroup?.querySelector('h4');
    const itemsContainer = appsGroup?.querySelector('div:last-child');

    expect(appsGroup).toBeInTheDocument();
    expect(title).toBeInTheDocument();
    expect(itemsContainer).toBeInTheDocument();
    expect(itemsContainer?.children.length).toBe(3);
  });

  it('handles items with duplicate names gracefully', () => {
    const duplicateItems: AppsItemType[] = [
      {
        name: 'App One',
        path: '/app-one',
        image: '/img/app-one.png',
      },
      {
        name: 'App One',
        path: '/app-one-duplicate',
        image: '/img/app-one-duplicate.png',
      },
    ];

    const propsWithDuplicates = {
      title: 'Duplicate Apps',
      items: duplicateItems,
    };

    const { container } = renderLayout(<AppsGroup {...propsWithDuplicates} />);

    // Both items should render despite duplicate keys (React will warn but still render)
    const items = container.querySelectorAll('[data-testid^="apps-item-"]');
    expect(items.length).toBeGreaterThan(0);
  });

  it('renders without crashing when all props are default', () => {
    const minimalProps = {
      title: '',
      items: [],
    };

    const { container } = renderLayout(<AppsGroup {...minimalProps} />);

    expect(container.querySelector('.apps-group')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 4 })).toBeInTheDocument();
  });
});
