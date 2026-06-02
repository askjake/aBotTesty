import React from 'react';
import { screen, waitFor } from '@testing-library/react';

import { getHealth } from '@shared/ui/services/health.services';
import { HealthStatusEnum } from '@shared/ui/enums/health.enums';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock the health service
jest.mock('@shared/ui/services/health.services', () => ({
  getHealth: jest.fn(),
}));

// Mock the styled components
jest.mock(
  '@shared/ui/components/molecules/Footer/HealthBlock/HealthBlock.styled',
  () => ({
    StyledHealthBlock: ({ children, ...props }: any) => (
      <div data-testid='health-block' {...props}>
        {children}
      </div>
    ),
    StyledHealthBlockIcon: ({ $hasError, ...props }: any) => (
      <div data-testid='health-icon' data-has-error={$hasError} {...props} />
    ),
  }),
);

import HealthBlock from '@shared/ui/components/molecules/Footer/HealthBlock';

const mockGetHealth = getHealth as jest.MockedFunction<typeof getHealth>;

// Suppress console errors
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

describe('HealthBlock', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders with correct structure', () => {
    mockGetHealth.mockResolvedValue({
      status: HealthStatusEnum.HEALTHY,
      version: '2.1.0',
      timestamp: '2024-01-01T00:00:00Z',
    });

    renderLayout(<HealthBlock />);

    expect(screen.getByTestId('health-block')).toBeInTheDocument();
    expect(screen.getByTestId('health-icon')).toBeInTheDocument();
    expect(screen.getByTestId('health-block')).toHaveClass('health-block');
  });

  it('shows healthy status when API call succeeds', async () => {
    mockGetHealth.mockResolvedValue({
      status: HealthStatusEnum.HEALTHY,
      version: '2.1.0',
      timestamp: '2024-01-01T00:00:00Z',
    });

    renderLayout(<HealthBlock />);

    await waitFor(() => {
      expect(screen.getByText('API v2.1.0')).toBeInTheDocument();
    });

    const healthIcon = screen.getByTestId('health-icon');
    expect(healthIcon).toHaveAttribute('data-has-error', 'false');
  });

  it('shows error state when API returns unhealthy status', async () => {
    mockGetHealth.mockResolvedValue({
      status: HealthStatusEnum.UNHEALTHY,
      version: '2.1.0',
      timestamp: '2024-01-01T00:00:00Z',
    });

    renderLayout(<HealthBlock />);

    await waitFor(() => {
      expect(screen.getByText('API v2.1.0')).toBeInTheDocument();
    });

    const healthIcon = screen.getByTestId('health-icon');
    expect(healthIcon).toHaveAttribute('data-has-error', 'true');
  });

  it('shows error state when API call fails', async () => {
    mockGetHealth.mockRejectedValue(new Error('Network error'));

    renderLayout(<HealthBlock />);

    await waitFor(() => {
      const healthIcon = screen.getByTestId('health-icon');
      expect(healthIcon).toHaveAttribute('data-has-error', 'true');
    });

    expect(screen.getByText('API v1.0.0')).toBeInTheDocument();
  });

  it('displays default version initially', () => {
    mockGetHealth.mockImplementation(() => new Promise(() => {})); // Never resolves

    renderLayout(<HealthBlock />);

    expect(screen.getByText('API v1.0.0')).toBeInTheDocument();
    expect(screen.getByTestId('health-icon')).toHaveAttribute(
      'data-has-error',
      'false',
    );
  });
});
