import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { BETA_REPORTS_URL } from '@shared/ui/constants/env.constants';
import ReportsAccessBlock from '@/components/organisms/ReportsAccessBlock';

jest.mock('axios');
jest.mock('@shared/ui/hooks/useHandleError.hook');

const mockAxios = axios as jest.Mocked<typeof axios>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;

// Mock window.location.reload
delete (window as any).location;
window.location = { reload: jest.fn() } as any;

// Suppress act warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('ReportsAccessBlock Component', () => {
  const mockHandleError = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockAxios.post.mockResolvedValue({ data: { success: true } });
  });

  it('renders without crashing', () => {
    renderLayout(<ReportsAccessBlock />);
    expect(screen.getByText('Access denied')).toBeInTheDocument();
  });

  it('displays "Access denied" title', () => {
    renderLayout(<ReportsAccessBlock />);
    expect(screen.getByText('Access denied')).toBeInTheDocument();
  });

  it('renders password input field', () => {
    renderLayout(<ReportsAccessBlock />);
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
  });

  it('renders password input as password type', () => {
    renderLayout(<ReportsAccessBlock />);
    const passwordInput = screen.getByLabelText('Password');
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  it('renders submit button', () => {
    renderLayout(<ReportsAccessBlock />);
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument();
  });

  it('submit button has primary type', () => {
    renderLayout(<ReportsAccessBlock />);
    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toHaveClass('ant-btn-primary');
  });

  it('shows validation error when submitting empty form', async () => {
    renderLayout(<ReportsAccessBlock />);

    const submitButton = screen.getByRole('button', { name: /submit/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Please, input password')).toBeInTheDocument();
    });
  });

  it('does not call API when form validation fails', async () => {
    renderLayout(<ReportsAccessBlock />);

    const submitButton = screen.getByRole('button', { name: /submit/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Please, input password')).toBeInTheDocument();
    });

    expect(mockAxios.post).not.toHaveBeenCalled();
  });

  it('calls API with correct password when form is submitted', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockAxios.post).toHaveBeenCalledWith(
        `${BETA_REPORTS_URL}/api/access`,
        { password: 'test-password' },
      );
    });
  });

  it('reloads page after successful password submission', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'correct-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(window.location.reload).toHaveBeenCalled();
    });
  });

  it('shows loading state while submitting', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockAxios.post.mockReturnValue(promise as any);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(submitButton).toHaveClass('ant-btn-loading');
    });

    resolvePromise!({ data: { success: true } });
  });

  it('handles API errors gracefully', async () => {
    const error = new Error('Invalid password');
    mockAxios.post.mockRejectedValueOnce(error);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'wrong-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(error);
    });
  });

  it('does not reload page when API call fails', async () => {
    const error = new Error('Invalid password');
    mockAxios.post.mockRejectedValueOnce(error);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'wrong-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalled();
    });

    expect(window.location.reload).not.toHaveBeenCalled();
  });

  it('stops loading state after API error', async () => {
    const error = new Error('Invalid password');
    mockAxios.post.mockRejectedValueOnce(error);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'wrong-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(submitButton).not.toHaveClass('ant-btn-loading');
    });
  });

  it('renders form with inline layout', () => {
    const { container } = renderLayout(<ReportsAccessBlock />);

    const form = container.querySelector('.ant-form-inline');
    expect(form).toBeInTheDocument();
  });

  it('has autocomplete disabled on form', () => {
    const { container } = renderLayout(<ReportsAccessBlock />);

    const form = container.querySelector('form');
    expect(form).toHaveAttribute('autocomplete', 'off');
  });

  it('allows typing in password field', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;

    await userEvent.type(passwordInput, 'my-password');

    expect(passwordInput.value).toBe('my-password');
  });

  it('clears validation error when user starts typing', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    // Trigger validation error
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText('Please, input password')).toBeInTheDocument();
    });

    // Start typing
    await userEvent.type(passwordInput, 'test');

    await waitFor(() => {
      expect(
        screen.queryByText('Please, input password'),
      ).not.toBeInTheDocument();
    });
  });

  it('can submit form by pressing Enter in password field', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');

    await userEvent.type(passwordInput, 'test-password{Enter}');

    await waitFor(() => {
      expect(mockAxios.post).toHaveBeenCalledWith(
        `${BETA_REPORTS_URL}/api/access`,
        { password: 'test-password' },
      );
    });
  });

  it('applies custom styled component classes', () => {
    const { container } = renderLayout(<ReportsAccessBlock />);

    const card = container.querySelector('.ant-card');
    expect(card).toBeInTheDocument();
  });

  it('renders title as h1 element', () => {
    const { container } = renderLayout(<ReportsAccessBlock />);

    const heading = container.querySelector('h1');
    expect(heading).toBeInTheDocument();
    expect(heading).toHaveTextContent('Access denied');
  });

  it('password field is required', () => {
    const { container } = renderLayout(<ReportsAccessBlock />);

    const formItem = container.querySelector('.ant-form-item-required');
    expect(formItem).toBeInTheDocument();
  });

  it('handles network errors', async () => {
    const networkError = new Error('Network Error');
    mockAxios.post.mockRejectedValueOnce(networkError);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(networkError);
    });
  });

  it('handles 401 unauthorized errors', async () => {
    const unauthorizedError = {
      response: {
        status: 401,
        data: { message: 'Unauthorized' },
      },
    };
    mockAxios.post.mockRejectedValueOnce(unauthorizedError);

    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'wrong-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(unauthorizedError);
    });
  });

  it('uses correct API endpoint', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(mockAxios.post).toHaveBeenCalledWith(
        expect.stringContaining('/api/access'),
        expect.any(Object),
      );
    });
  });

  it('only reloads page once after successful submission', async () => {
    renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(window.location.reload).toHaveBeenCalledTimes(1);
    });
  });

  it('shows loading icon in button while submitting', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockAxios.post.mockReturnValue(promise as any);

    const { container } = renderLayout(<ReportsAccessBlock />);

    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /submit/i });

    await userEvent.type(passwordInput, 'test-password');
    await userEvent.click(submitButton);

    await waitFor(() => {
      const loadingIcon = container.querySelector('.ant-btn-loading-icon');
      expect(loadingIcon).toBeInTheDocument();
    });

    resolvePromise!({ data: { success: true } });
  });
});
