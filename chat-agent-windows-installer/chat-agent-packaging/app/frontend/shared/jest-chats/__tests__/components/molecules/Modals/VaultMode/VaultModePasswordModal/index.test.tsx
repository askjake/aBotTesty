import React from 'react';
import { screen, waitFor, fireEvent } from '@testing-library/react';

import { enableVaultService } from '@/services/vault.services';
import { setupVaultValidator } from '@/validators/vault.validators';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import useRefetchChats from '@/hooks/useRefetchChats';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import VaultModePasswordModal from '@/components/molecules/Modals/VaultMode/VaultModePasswordModal';

// Mock dependencies
jest.mock('@/services/vault.services');
jest.mock('@/validators/vault.validators');
jest.mock('@shared/ui/hooks/useHandleError.hook');
jest.mock('@/hooks/useRefetchChats');

// Mock Ant Design App hook
const mockMessage = {
  success: jest.fn(),
  error: jest.fn(),
};

jest.mock('antd', () => {
  const originalAntd = jest.requireActual('antd');
  return {
    ...originalAntd,
    App: {
      ...originalAntd.App,
      useApp: () => ({
        message: mockMessage,
      }),
    },
  };
});

const mockEnableVaultService = enableVaultService as jest.MockedFunction<
  typeof enableVaultService
>;
const mockSetupVaultValidator = setupVaultValidator as jest.Mocked<
  typeof setupVaultValidator
>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;
const mockUseRefetchChats = useRefetchChats as jest.MockedFunction<
  typeof useRefetchChats
>;

describe('VaultModePasswordModal', () => {
  const mockHandleError = jest.fn();
  const mockRefetchChats = jest.fn();

  const defaultState = {
    chats: {
      showEnableVaultModal: true,
      vaultModeRegistered: true,
      vaultMode: false,
    },
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockUseRefetchChats.mockReturnValue({ refetchChats: mockRefetchChats });
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    mockSetupVaultValidator.safeParse.mockReturnValue({ success: true });
  });

  it('renders modal when showEnableVaultModal is true', () => {
    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    expect(screen.getByText('Vault Mode required')).toBeInTheDocument();
    expect(screen.getByText('Enable Vault Mode')).toBeInTheDocument();
    expect(screen.getByLabelText('Password:')).toBeInTheDocument();
  });

  it('does not render modal when showEnableVaultModal is false', () => {
    const state = {
      chats: { ...defaultState.chats, showEnableVaultModal: false },
    };
    const store = mockStore(state);

    renderLayout(<VaultModePasswordModal />, { store });

    expect(screen.queryByText('Vault Mode required')).not.toBeInTheDocument();
  });

  it('shows validation error for empty password', async () => {
    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText('Please enter your password'),
      ).toBeInTheDocument();
    });
  });

  it('shows validation error from setupVaultValidator', async () => {
    mockSetupVaultValidator.safeParse.mockReturnValue({
      success: false,
      error: {
        format: () => ({
          password: {
            _errors: ['Password must be at least 8 characters'],
          },
        }),
      },
    } as any);

    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const passwordInput = screen.getByLabelText('Password:');
    fireEvent.change(passwordInput, { target: { value: 'weak' } });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText('Password must be at least 8 characters'),
      ).toBeInTheDocument();
    });
  });

  it('successfully enables vault mode with valid password', async () => {
    mockEnableVaultService.mockResolvedValue({ success: true });

    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const passwordInput = screen.getByLabelText('Password:');
    fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockEnableVaultService).toHaveBeenCalledWith({
        password: 'ValidPass123!',
      });
      expect(mockRefetchChats).toHaveBeenCalled();
      expect(mockMessage.success).toHaveBeenCalledWith(
        'The Vault Mode has successfully enabled',
      );
    });

    // Check store state
    await waitFor(() => {
      const state = store.getState();
      expect(state.chats.vaultMode).toBe(true);
      expect(state.chats.showEnableVaultModal).toBe(false);
    });
  });

  it('handles service error during vault enablement', async () => {
    const serviceError = new Error('Service error');
    mockEnableVaultService.mockRejectedValue(serviceError);

    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const passwordInput = screen.getByLabelText('Password:');
    fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(serviceError);
    });
  });

  it('does not call enableVaultService when vault is not registered', async () => {
    const state = {
      chats: { ...defaultState.chats, vaultModeRegistered: false },
    };

    const store = mockStore(state);

    renderLayout(<VaultModePasswordModal />, { store });

    // Fill in a valid password to bypass form validation
    const passwordInput = screen.getByLabelText('Password:');
    fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockEnableVaultService).not.toHaveBeenCalled();
    });

    // Check that modal closes by checking store state
    await waitFor(() => {
      const finalState = store.getState();
      expect(finalState.chats.showEnableVaultModal).toBe(false);
    });
  });

  it('does not call enableVaultService when vault is already enabled', async () => {
    const state = {
      chats: { ...defaultState.chats, vaultMode: true },
    };

    const store = mockStore(state);

    renderLayout(<VaultModePasswordModal />, { store });

    // Fill in a valid password to bypass form validation
    const passwordInput = screen.getByLabelText('Password:');
    fireEvent.change(passwordInput, { target: { value: 'ValidPass123!' } });

    const submitButton = screen.getByText('Enable Vault Mode');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockEnableVaultService).not.toHaveBeenCalled();
    });

    // Check that modal closes by checking store state
    await waitFor(() => {
      const finalState = store.getState();
      expect(finalState.chats.showEnableVaultModal).toBe(false);
    });
  });

  it('closes modal when cancel button is clicked', async () => {
    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    await waitFor(() => {
      const state = store.getState();
      expect(state.chats.showEnableVaultModal).toBe(false);
    });
  });

  it('toggles password visibility when eye icon is clicked', async () => {
    const store = mockStore(defaultState);

    renderLayout(<VaultModePasswordModal />, { store });

    const passwordInput = screen.getByLabelText('Password:');
    expect(passwordInput).toHaveAttribute('type', 'password');

    const eyeIcon = screen.getByRole('img', { name: /eye-invisible/i });
    fireEvent.click(eyeIcon);

    await waitFor(() => {
      expect(passwordInput).toHaveAttribute('type', 'text');
    });
  });
});
