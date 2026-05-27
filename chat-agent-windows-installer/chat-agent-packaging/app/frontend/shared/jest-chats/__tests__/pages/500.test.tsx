import React from 'react';
import { screen } from '@testing-library/react';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import InternalErrorPage from '@/pages/500';

// Mock Next.js navigation hook
const mockSearchParams = {
  get: jest.fn(),
};

jest.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}));

// Mock Next.js Head component
jest.mock('next/head', () => () => null);

// Mock the InternalErrorTemplate component
jest.mock(
  '@shared/ui/components/templates/InternalErrorTemplate',
  () =>
    ({ error }: { error: { type: string; message: string } }) => (
      <div data-testid='internal-error-template'>
        <div data-testid='error-type'>{error.type}</div>
        <div data-testid='error-message'>{error.message}</div>
      </div>
    ),
);

describe('InternalErrorPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render 500 internal error page with default empty error', () => {
    mockSearchParams.get.mockReturnValue(null);

    const store = mockStore();
    renderLayout(<InternalErrorPage />, { store });

    expect(screen.getByTestId('internal-error-template')).toBeInTheDocument();
    expect(screen.getByTestId('error-type')).toHaveTextContent('');
    expect(screen.getByTestId('error-message')).toHaveTextContent('');
  });

  it('should render with error details from search params', () => {
    mockSearchParams.get.mockImplementation((key: string) => {
      if (key === 'type') return 'Database Error';
      if (key === 'message') return 'Connection failed';
      return null;
    });

    const store = mockStore();
    renderLayout(<InternalErrorPage />, { store });

    expect(screen.getByTestId('internal-error-template')).toBeInTheDocument();
    expect(screen.getByTestId('error-type')).toHaveTextContent(
      'Database Error',
    );
    expect(screen.getByTestId('error-message')).toHaveTextContent(
      'Connection failed',
    );
  });
});
