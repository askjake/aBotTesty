import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';

import VaultModeWarningRegisterModal from '@/components/molecules/Modals/VaultMode/VaultModeWarningRegisterModal';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock Next.js router
const mockPush = jest.fn();
const mockRouter = {
  push: mockPush,
  pathname: '/',
  query: {},
  asPath: '/',
};

jest.mock('next/router', () => ({
  useRouter: jest.fn(),
}));

const mockUseRouter = useRouter as jest.MockedFunction<typeof useRouter>;

describe('VaultModeWarningRegisterModal', () => {
  const mockOnCancel = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
  });

  it('renders modal with correct title and content', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    expect(
      screen.getByText('Register the Vault Mode required'),
    ).toBeInTheDocument();
    expect(screen.getByText('Register the Vault Mode')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Register the Vault mode first, before enabling this mode',
      ),
    ).toBeInTheDocument();
  });

  it('does not render modal when open is false', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={false} onCancel={mockOnCancel} />,
    );

    expect(
      screen.queryByText('Register the Vault Mode required'),
    ).not.toBeInTheDocument();
  });

  it('navigates to vault-mode page when OK button is clicked', async () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    const okButton = screen.getByText('Register the Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
    });
  });

  it('calls onCancel when cancel button is clicked', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('calls onCancel when X button is clicked', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('handles case when onCancel is not provided', () => {
    renderLayout(<VaultModeWarningRegisterModal open={true} />);

    const cancelButton = screen.getByRole('button', { name: /cancel/i });

    // Should not throw error when onCancel is undefined
    expect(() => {
      fireEvent.click(cancelButton);
    }).not.toThrow();
  });

  it('forwards additional modal props correctly', () => {
    renderLayout(
      <VaultModeWarningRegisterModal
        open={true}
        onCancel={mockOnCancel}
        width={800}
        centered
        destroyOnHidden
        data-testid='custom-modal'
      />,
    );

    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveStyle('width: 800px');
  });

  it('overrides onOk prop with router navigation', async () => {
    const customOnOk = jest.fn();

    renderLayout(
      <VaultModeWarningRegisterModal
        open={true}
        onCancel={mockOnCancel}
        onOk={customOnOk}
      />,
    );

    const okButton = screen.getByText('Register the Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
    });

    // Custom onOk should not be called since it's overridden
    expect(customOnOk).not.toHaveBeenCalled();
  });

  it('handles multiple rapid OK clicks gracefully', async () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    const okButton = screen.getByText('Register the Vault Mode');

    // Click multiple times rapidly
    fireEvent.click(okButton);
    fireEvent.click(okButton);
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledTimes(3);
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
    });
  });

  it('has correct accessibility attributes', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('renders with correct button text', () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    expect(
      screen.getByRole('button', { name: 'Register the Vault Mode' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
  });

  it('maintains modal functionality with custom props', () => {
    renderLayout(
      <VaultModeWarningRegisterModal
        open={true}
        onCancel={mockOnCancel}
        maskClosable={false}
        keyboard={false}
        closable={false}
      />,
    );

    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();

    // Modal should still render with custom props
    expect(
      screen.getByText('Register the Vault Mode required'),
    ).toBeInTheDocument();
  });

  it('handles router push with different paths', async () => {
    renderLayout(
      <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
    );

    const okButton = screen.getByText('Register the Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
      expect(mockPush).toHaveBeenCalledTimes(1);
    });
  });

  describe('Modal behavior', () => {
    it('displays correct modal structure', () => {
      renderLayout(
        <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
      );

      // Check modal structure
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(
        screen.getByText('Register the Vault Mode required'),
      ).toBeInTheDocument();
      expect(
        screen.getByText(
          'Register the Vault mode first, before enabling this mode',
        ),
      ).toBeInTheDocument();
    });

    it('handles modal visibility correctly', () => {
      const { rerender } = renderLayout(
        <VaultModeWarningRegisterModal open={false} onCancel={mockOnCancel} />,
      );

      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

      rerender(
        <VaultModeWarningRegisterModal open={true} onCancel={mockOnCancel} />,
      );

      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  describe('Props handling', () => {
    it('spreads all props to Modal component', () => {
      const customProps = {
        className: 'custom-modal',
        'data-testid': 'register-modal',
        width: 600,
        centered: true,
      };

      renderLayout(
        <VaultModeWarningRegisterModal
          open={true}
          onCancel={mockOnCancel}
          {...customProps}
        />,
      );

      const modal = screen.getByRole('dialog');
      expect(modal).toHaveStyle('width: 600px');
      expect(modal).toHaveClass('custom-modal');
    });

    it('uses passed title and okText props instead of hardcoded values', () => {
      renderLayout(
        <VaultModeWarningRegisterModal
          open={true}
          onCancel={mockOnCancel}
          title='Different Title'
          okText='Different OK Text'
        />,
      );

      // Component actually uses the passed props, not hardcoded values
      expect(screen.getByText('Different Title')).toBeInTheDocument();
      expect(screen.getByText('Different OK Text')).toBeInTheDocument();
      expect(
        screen.queryByText('Register the Vault Mode required'),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText('Register the Vault Mode'),
      ).not.toBeInTheDocument();
    });
  });
});
