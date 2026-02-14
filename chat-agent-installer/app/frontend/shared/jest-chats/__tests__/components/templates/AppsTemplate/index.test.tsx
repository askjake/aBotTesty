// AppsTemplate.test.tsx
import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import AppsTemplate from '@/components/templates/AppsTemplate';
import { APPS_NAVIGATION } from '@/constants/apps.constants';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock the constants
jest.mock('@/constants/apps.constants', () => ({
  APPS_NAVIGATION: [
    {
      name: 'Workflows',
      apps: [
        {
          name: 'Beta Report Analysis',
          path: '/beta-reports',
          image: '/img/beta-reports.png',
        },
        {
          name: 'Alpha Testing',
          path: '/alpha-testing',
          image: '/img/alpha-testing.png',
        },
      ],
    },
    {
      name: 'Tools',
      apps: [
        {
          name: 'Dashboard',
          path: '/dashboard',
          image: '/img/dashboard.png',
        },
        {
          name: 'Analytics',
          path: '/analytics',
          image: '/img/analytics.png',
        },
      ],
    },
  ],
}));

// Mock child components
jest.mock('@/components/organisms/Apps/AppsGroup', () => ({
  __esModule: true,
  default: ({ title, items }: any) => (
    <div data-testid={`apps-group-${title}`}>
      <h4>{title}</h4>
      <div data-testid={`apps-count-${title}`}>{items.length}</div>
      {items.map((item: any) => (
        <div key={item.name} data-testid={`app-item-${item.name}`}>
          {item.name}
        </div>
      ))}
    </div>
  ),
}));

jest.mock('@/components/containers/ContainerWithSidebar', () => ({
  __esModule: true,
  default: ({ children }: any) => (
    <div data-testid='container-with-sidebar'>{children}</div>
  ),
}));

describe('AppsTemplate Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with all elements', () => {
    renderLayout(<AppsTemplate />);

    // Check if main title is rendered
    expect(screen.getByText('Applications')).toBeInTheDocument();

    // Check if search input is rendered
    const searchInput = screen.getByPlaceholderText('Search app by name');
    expect(searchInput).toBeInTheDocument();

    // Check if ContainerWithSidebar is rendered
    expect(screen.getByTestId('container-with-sidebar')).toBeInTheDocument();
  });

  it('renders all app groups from APPS_NAVIGATION', () => {
    renderLayout(<AppsTemplate />);

    // Check if all groups are rendered
    expect(screen.getByTestId('apps-group-Workflows')).toBeInTheDocument();
    expect(screen.getByTestId('apps-group-Tools')).toBeInTheDocument();
  });

  it('renders all apps initially', () => {
    renderLayout(<AppsTemplate />);

    // Check Workflows apps
    expect(
      screen.getByTestId('app-item-Beta Report Analysis'),
    ).toBeInTheDocument();
    expect(screen.getByTestId('app-item-Alpha Testing')).toBeInTheDocument();

    // Check Tools apps
    expect(screen.getByTestId('app-item-Dashboard')).toBeInTheDocument();
    expect(screen.getByTestId('app-item-Analytics')).toBeInTheDocument();
  });

  it('filters apps based on search text', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Type in search input
    fireEvent.change(searchInput, { target: { value: 'beta' } });

    await waitFor(() => {
      // Should show Beta Report Analysis
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();

      // Should not show other apps
      expect(
        screen.queryByTestId('app-item-Alpha Testing'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Dashboard'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Analytics'),
      ).not.toBeInTheDocument();
    });
  });

  it('search is case-insensitive', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Type uppercase
    fireEvent.change(searchInput, { target: { value: 'BETA' } });

    await waitFor(() => {
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
    });

    // Type lowercase
    fireEvent.change(searchInput, { target: { value: 'beta' } });

    await waitFor(() => {
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
    });

    // Type mixed case
    fireEvent.change(searchInput, { target: { value: 'BeTa' } });

    await waitFor(() => {
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
    });
  });

  it('shows no apps when search matches nothing', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    fireEvent.change(searchInput, { target: { value: 'nonexistent app' } });

    await waitFor(() => {
      expect(
        screen.queryByTestId('app-item-Beta Report Analysis'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Alpha Testing'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Dashboard'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Analytics'),
      ).not.toBeInTheDocument();
    });

    // Groups should still be rendered but with 0 apps
    expect(screen.getByTestId('apps-count-Workflows')).toHaveTextContent('0');
    expect(screen.getByTestId('apps-count-Tools')).toHaveTextContent('0');
  });

  it('filters apps across multiple groups', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Search for 'a' which appears in multiple apps
    fireEvent.change(searchInput, { target: { value: 'a' } });

    await waitFor(() => {
      // Should show apps containing 'a'
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Alpha Testing')).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Dashboard')).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Analytics')).toBeInTheDocument();
    });
  });

  it('clears search and shows all apps', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Type search text
    fireEvent.change(searchInput, { target: { value: 'beta' } });

    await waitFor(() => {
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Dashboard'),
      ).not.toBeInTheDocument();
    });

    // Clear search
    fireEvent.change(searchInput, { target: { value: '' } });

    await waitFor(() => {
      // All apps should be visible again
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Alpha Testing')).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Dashboard')).toBeInTheDocument();
      expect(screen.getByTestId('app-item-Analytics')).toBeInTheDocument();
    });
  });

  it('search input value updates correctly', () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText(
      'Search app by name',
    ) as HTMLInputElement;

    expect(searchInput.value).toBe('');

    fireEvent.change(searchInput, { target: { value: 'test search' } });

    expect(searchInput.value).toBe('test search');
  });

  it('renders search icon in input', () => {
    const { container } = renderLayout(<AppsTemplate />);

    const searchIcon = container.querySelector('.anticon-search');
    expect(searchIcon).toBeInTheDocument();
  });

  it('filters by partial match', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Search for partial word
    fireEvent.change(searchInput, { target: { value: 'dash' } });

    await waitFor(() => {
      expect(screen.getByTestId('app-item-Dashboard')).toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Beta Report Analysis'),
      ).not.toBeInTheDocument();
    });
  });

  it('maintains correct app count per group after filtering', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Initially should have 2 apps in Workflows and 2 in Tools
    expect(screen.getByTestId('apps-count-Workflows')).toHaveTextContent('2');
    expect(screen.getByTestId('apps-count-Tools')).toHaveTextContent('2');

    // Filter to show only Beta Report Analysis
    fireEvent.change(searchInput, { target: { value: 'beta' } });

    await waitFor(() => {
      expect(screen.getByTestId('apps-count-Workflows')).toHaveTextContent('1');
      expect(screen.getByTestId('apps-count-Tools')).toHaveTextContent('0');
    });
  });

  it('renders all groups even when they have no matching apps', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Search for something that only exists in one group
    fireEvent.change(searchInput, { target: { value: 'dashboard' } });

    await waitFor(() => {
      // Both groups should still be rendered
      expect(screen.getByTestId('apps-group-Workflows')).toBeInTheDocument();
      expect(screen.getByTestId('apps-group-Tools')).toBeInTheDocument();

      // But only Tools should have apps
      expect(screen.getByTestId('apps-count-Workflows')).toHaveTextContent('0');
      expect(screen.getByTestId('apps-count-Tools')).toHaveTextContent('1');
    });
  });

  it('handles rapid search input changes', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    // Rapidly change search text
    fireEvent.change(searchInput, { target: { value: 'b' } });
    fireEvent.change(searchInput, { target: { value: 'be' } });
    fireEvent.change(searchInput, { target: { value: 'bet' } });
    fireEvent.change(searchInput, { target: { value: 'beta' } });

    await waitFor(() => {
      expect(
        screen.getByTestId('app-item-Beta Report Analysis'),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId('app-item-Dashboard'),
      ).not.toBeInTheDocument();
    });
  });

  it('preserves group order after filtering', async () => {
    renderLayout(<AppsTemplate />);

    const searchInput = screen.getByPlaceholderText('Search app by name');

    fireEvent.change(searchInput, { target: { value: 'a' } });

    await waitFor(() => {
      const groups = screen.getAllByTestId(/^apps-group-/);
      expect(groups[0]).toHaveAttribute('data-testid', 'apps-group-Workflows');
      expect(groups[1]).toHaveAttribute('data-testid', 'apps-group-Tools');
    });
  });
});
