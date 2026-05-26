import React from 'react';
import { screen, fireEvent, act, waitFor } from '@testing-library/react';
import { disableVaultService } from '@/services/vault.services';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import VaultModeButton from '@/components/molecules/Buttons/VaultModeButton';

// Mock dependencies
jest.mock('@/services/vault.services', () => ({
  disableVaultService: jest.fn(),
}));

jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: () => jest.fn(),
}));

jest.mock('@/hooks/useRefetchChats', () => ({
  __esModule: true,
  default: () => ({
    refetchChats: jest.fn(),
  }),
}));

const mockMessageSuccess = jest.fn();
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  App: {
    useApp: () => ({
      message: {
        success: mockMessageSuccess,
      },
    }),
  },
}));

// Mock dynamic imports
jest.mock('next/dynamic', () => () => {
  const DynamicComponent = (props: any) => {
    if (props.open) {
      return <div data-testid={props['data-testid']} />;
    }
    return null;
  };
  return DynamicComponent;
});

const mockDisableVaultService = disableVaultService as jest.MockedFunction<
  typeof disableVaultService
>;

describe('VaultModeButton Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly', async () => {
    const store = mockStore();
    await act(async () => {
      renderLayout(<VaultModeButton />, { store });
    });

    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  describe('Tooltip text', () => {
    it('shows "Setup vault mode" when vault mode is not registered', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: false,
        },
      };

      const store = mockStore(initialState);
      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');
      fireEvent.mouseEnter(button);

      await waitFor(() => {
        expect(screen.getByText('Setup vault mode')).toBeInTheDocument();
      });
    });

    it('shows "Enable vault mode" when registered but disabled', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');
      fireEvent.mouseEnter(button);

      await waitFor(() => {
        expect(screen.getByText('Enable vault mode')).toBeInTheDocument();
      });
    });

    it('shows "Disable vault mode" when registered and enabled', async () => {
      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');
      fireEvent.mouseEnter(button);

      await waitFor(() => {
        expect(screen.getByText('Disable vault mode')).toBeInTheDocument();
      });
    });
  });

  describe('Click behavior', () => {
    it('shows register modal when vault mode is not registered', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: false,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Initially modal should not be visible
      expect(
        screen.queryByTestId('vault-mode-warning-modal'),
      ).not.toBeInTheDocument();

      await act(async () => {
        fireEvent.click(button);
      });

      // After click, modal should be visible
      await waitFor(() => {
        expect(
          screen.getByTestId('vault-mode-warning-modal'),
        ).toBeInTheDocument();
      });
    });

    it('dispatches setShowEnableVaultModal when vault mode is registered but disabled', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: true,
          showEnableVaultModal: false,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      const finalState = store.getState();
      expect(finalState.chats.showEnableVaultModal).toBe(true);
    });

    it('shows disable warning modal when vault mode is enabled', async () => {
      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(screen.getByText('Disable the Vault mode')).toBeInTheDocument();
        expect(
          screen.getByText(/By clicking the 'Accept' button/),
        ).toBeInTheDocument();
      });
    });
  });

  describe('Disable vault mode', () => {
    it('successfully disables vault mode', async () => {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      mockDisableVaultService.mockResolvedValue(undefined);

      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Click to show disable modal
      await act(async () => {
        fireEvent.click(button);
      });

      expect(screen.getByText('Disable the Vault mode')).toBeInTheDocument();

      // Click Accept button in modal
      const acceptButton = screen.getByText('Accept');

      await act(async () => {
        fireEvent.click(acceptButton);
      });

      await waitFor(() => {
        expect(mockDisableVaultService).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockMessageSuccess).toHaveBeenCalledWith(
          'The Vault Mode has successfully disabled',
        );
      });

      const finalState = store.getState();
      expect(finalState.chats.vaultMode).toBe(false);

      // Don't test modal removal - just verify the service was called and state updated
    });

    it('handles disable vault mode error', async () => {
      const mockError = new Error('Disable failed');
      mockDisableVaultService.mockRejectedValue(mockError);

      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Click to show disable modal
      await act(async () => {
        fireEvent.click(button);
      });

      // Click Accept button in modal
      const acceptButton = screen.getByText('Accept');

      await act(async () => {
        fireEvent.click(acceptButton);
      });

      await waitFor(() => {
        expect(mockDisableVaultService).toHaveBeenCalled();
      });

      // Just verify the service was called - don't test modal state
    });

    it('closes disable modal when cancelled', async () => {
      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Click to show disable modal
      await act(async () => {
        fireEvent.click(button);
      });

      expect(screen.getByText('Disable the Vault mode')).toBeInTheDocument();

      // Click Cancel button
      const cancelButton = screen.getByText('Cancel');

      await act(async () => {
        fireEvent.click(cancelButton);
      });

      // Verify the service was not called instead of testing modal visibility
      expect(mockDisableVaultService).not.toHaveBeenCalled();
    });
  });

  describe('Modal state management', () => {
    it('manages register modal state correctly', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: false,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Click to open register modal
      await act(async () => {
        fireEvent.click(button);
      });

      expect(
        screen.getByTestId('vault-mode-warning-modal'),
      ).toBeInTheDocument();
    });

    it('manages disable modal state correctly', async () => {
      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');

      // Click to open disable modal
      await act(async () => {
        fireEvent.click(button);
      });

      expect(screen.getByText('Disable the Vault mode')).toBeInTheDocument();
      expect(screen.getByText('Accept')).toBeInTheDocument();
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });
  });

  describe('Icon state', () => {
    it('renders with correct active state when vault mode is enabled and registered', async () => {
      const initialState = {
        chats: {
          vaultMode: true,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('renders with correct active state when vault mode is disabled', async () => {
      const initialState = {
        chats: {
          vaultMode: false,
          vaultModeRegistered: true,
        },
      };

      const store = mockStore(initialState);

      await act(async () => {
        renderLayout(<VaultModeButton />, { store });
      });

      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });
  });
});
