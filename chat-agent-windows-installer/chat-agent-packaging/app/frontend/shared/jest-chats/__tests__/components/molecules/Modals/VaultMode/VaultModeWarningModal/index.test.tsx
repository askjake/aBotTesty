import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { useRouter } from 'next/router';

import VaultModeWarningModal from '@/components/molecules/Modals/VaultMode/VaultModeWarningModal';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
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

describe('VaultModeWarningModal', () => {
  const mockOnCancel = jest.fn();

  const defaultState = {
    chats: {
      vaultModeRegistered: true,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseRouter.mockReturnValue(mockRouter as any);
  });

  it('renders modal with correct title and content', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    expect(screen.getByText('Vault Mode required')).toBeInTheDocument();
    expect(screen.getByText('Enable Vault Mode')).toBeInTheDocument();
    expect(
      screen.getByText('For choosing this chat, please, enable the Vault mode'),
    ).toBeInTheDocument();
  });

  it('does not render modal when open is false', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={false} onCancel={mockOnCancel} />,
      { store },
    );

    expect(screen.queryByText('Vault Mode required')).not.toBeInTheDocument();
  });

  it('dispatches setShowEnableVaultModal and calls onCancel when vault is registered and OK is clicked', async () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const okButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      const state = store.getState();
      expect(state.chats.showEnableVaultModal).toBe(true);
    });

    expect(mockOnCancel).toHaveBeenCalled();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it('navigates to vault-mode page when vault is not registered and OK is clicked', async () => {
    const state = {
      chats: { vaultModeRegistered: false },
    };
    const store = mockStore(state);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const okButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
    });

    expect(mockOnCancel).not.toHaveBeenCalled();

    // Should not dispatch setShowEnableVaultModal
    const finalState = store.getState();
    expect(finalState.chats.showEnableVaultModal).toBeUndefined();
  });

  it('calls onCancel when cancel button is clicked', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('calls onCancel when X button is clicked', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const closeButton = screen.getByRole('button', { name: /close/i });
    fireEvent.click(closeButton);

    expect(mockOnCancel).toHaveBeenCalled();
  });

  it('handles case when onCancel is not provided', async () => {
    const store = mockStore(defaultState);

    renderLayout(<VaultModeWarningModal open={true} />, { store });

    const okButton = screen.getByText('Enable Vault Mode');

    // Should not throw error when onCancel is undefined
    expect(() => {
      fireEvent.click(okButton);
    }).not.toThrow();

    await waitFor(() => {
      const state = store.getState();
      expect(state.chats.showEnableVaultModal).toBe(true);
    });
  });

  it('forwards additional modal props correctly', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal
        open={true}
        onCancel={mockOnCancel}
        width={800}
        centered
        destroyOnHidden
        data-testid='custom-modal'
      />,
      { store },
    );

    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();
    expect(modal).toHaveStyle('width: 800px');
  });

  it('handles OK click with event parameter correctly', async () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const okButton = screen.getByText('Enable Vault Mode');
    const clickEvent = new MouseEvent('click', { bubbles: true });

    fireEvent.click(okButton, clickEvent);

    await waitFor(() => {
      expect(mockOnCancel).toHaveBeenCalledWith(expect.any(Object));
    });
  });

  it('has correct accessibility attributes', () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
  });

  it('dispatches action when vault is registered', async () => {
    const stateWithRegistered = {
      chats: { vaultModeRegistered: true },
    };

    const storeRegistered = mockStore(stateWithRegistered);
    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store: storeRegistered },
    );

    const okButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(okButton);

    expect(mockPush).not.toHaveBeenCalled();

    await waitFor(() => {
      const state = storeRegistered.getState();
      expect(state.chats.showEnableVaultModal).toBe(true);
    });
  });

  it('navigates to vault-mode when vault is not registered', async () => {
    const stateWithoutRegistered = {
      chats: { vaultModeRegistered: false },
    };

    const storeUnregistered = mockStore(stateWithoutRegistered);
    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store: storeUnregistered },
    );

    const okButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(okButton);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/vault-mode');
    });
  });

  it('handles multiple rapid OK clicks gracefully', async () => {
    const store = mockStore(defaultState);

    renderLayout(
      <VaultModeWarningModal open={true} onCancel={mockOnCancel} />,
      { store },
    );

    const okButton = screen.getByText('Enable Vault Mode');

    // Click multiple times rapidly
    fireEvent.click(okButton);
    fireEvent.click(okButton);
    fireEvent.click(okButton);

    await waitFor(() => {
      const state = store.getState();
      expect(state.chats.showEnableVaultModal).toBe(true);
    });

    // onCancel should be called for each click
    expect(mockOnCancel).toHaveBeenCalledTimes(3);
  });
});
