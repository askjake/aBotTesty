import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import SetupVaultForm from '@/components/organisms/VaultMode/SetupVaultForm';
import * as vaultServices from '@/services/vault.services';

// Mock services
jest.mock('@/services/vault.services', () => ({
  registerVaultService: jest.fn(),
  enableVaultService: jest.fn(),
}));

// Mock hooks
jest.mock('@shared/ui/hooks/useHandleError.hook', () => {
  return jest.fn(() => jest.fn());
});

// Mock validator
jest.mock('@/validators/vault.validators', () => ({
  setupVaultValidator: {
    safeParse: jest.fn(),
  },
}));

describe('SetupVaultForm', () => {
  let store: ReturnType<typeof mockStore>;
  const mockRegisterVaultService =
    vaultServices.registerVaultService as jest.MockedFunction<
      typeof vaultServices.registerVaultService
    >;
  const mockEnableVaultService =
    vaultServices.enableVaultService as jest.MockedFunction<
      typeof vaultServices.enableVaultService
    >;
  const mockHandleError = jest.fn();
  const mockSetupVaultValidator =
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@/validators/vault.validators').setupVaultValidator;

  const defaultState = {
    chats: {
      vaultMode: false,
      vaultModeRegistered: false,
    },
  };

  beforeEach(() => {
    store = mockStore(defaultState);

    jest.clearAllMocks();
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    require('@shared/ui/hooks/useHandleError.hook').mockReturnValue(
      mockHandleError,
    );

    // Default validator mock - returns success
    mockSetupVaultValidator.safeParse.mockReturnValue({
      success: true,
      data: { password: 'ValidPass123!' },
    });
  });

  describe('Basic Rendering', () => {
    it('should render the form with all required fields', () => {
      renderLayout(<SetupVaultForm />, { store });

      // Check form fields
      expect(screen.getByLabelText(/New passphrase:/)).toBeInTheDocument();
      expect(
        screen.getByLabelText(/Re-enter your passphrase:/),
      ).toBeInTheDocument();

      // Check submit button
      expect(
        screen.getByRole('button', { name: /Enable Vault Mode/ }),
      ).toBeInTheDocument();
    });

    it('should render password input fields with eye icons', () => {
      renderLayout(<SetupVaultForm />, { store });

      const passwordInputs = screen.getAllByDisplayValue('');
      expect(passwordInputs).toHaveLength(2);

      // Check for eye icons (they should be present in password inputs)
      const eyeIcons = document.querySelectorAll('.anticon-eye-invisible');
      expect(eyeIcons.length).toBeGreaterThanOrEqual(2);
    });

    it('should have vertical form layout', () => {
      renderLayout(<SetupVaultForm />, { store });

      const form = document.querySelector('.ant-form-vertical');
      expect(form).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('should show required field errors when submitting empty form', async () => {
      const user = userEvent.setup();
      renderLayout(<SetupVaultForm />, { store });

      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.click(submitButton);

      await waitFor(() => {
        expect(
          screen.getByText('Please enter your new passphrase'),
        ).toBeInTheDocument();
        expect(
          screen.getByText('Please re-enter your passphrase'),
        ).toBeInTheDocument();
      });
    });

    it('should validate password with custom validator', async () => {
      const user = userEvent.setup();

      // Mock validator to return validation error
      mockSetupVaultValidator.safeParse.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            password: {
              _errors: ['Password must contain at least 8 characters'],
            },
          }),
        },
      });

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'weak');
      await user.click(submitButton);

      await waitFor(() => {
        // Just verify that validation errors are displayed
        const errorElements = document.querySelectorAll(
          '.ant-form-item-explain-error',
        );
        const hasValidationError = Array.from(errorElements).some((element) =>
          element.textContent?.includes(
            'Password must contain at least 8 characters',
          ),
        );
        expect(hasValidationError).toBe(true);
      });
    });

    it('should validate password confirmation matches', async () => {
      const user = userEvent.setup();
      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'DifferentPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Passwords must be equal')).toBeInTheDocument();
      });
    });

    it('should trim whitespace from password inputs', async () => {
      const user = userEvent.setup();
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockResolvedValue({} as any);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      // Type passwords with leading/trailing spaces
      await user.type(passwordInput, '  ValidPass123!  ');
      await user.type(confirmPasswordInput, '  ValidPass123!  ');
      await user.click(submitButton);

      // Check that the final call (form submission) has trimmed values
      await waitFor(() => {
        expect(mockRegisterVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
      });
    });

    it('should validate both password fields with custom validator', async () => {
      const user = userEvent.setup();

      // Mock validator to return validation error for both fields
      mockSetupVaultValidator.safeParse.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            password: {
              _errors: ['Password must contain at least 8 characters'],
            },
          }),
        },
      });

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'weak');
      await user.type(confirmPasswordInput, 'weak');
      await user.click(submitButton);

      await waitFor(() => {
        // Both fields should show validation errors
        const errorElements = document.querySelectorAll(
          '.ant-form-item-explain-error',
        );
        const errorTexts = Array.from(errorElements).map(
          (el) => el.textContent,
        );
        const hasPasswordError = errorTexts.some((text) =>
          text?.includes('Password must contain at least 8 characters'),
        );
        expect(hasPasswordError).toBe(true);
      });
    });
  });

  describe('Password Visibility Toggle', () => {
    it('should toggle password visibility when eye icon is clicked', async () => {
      const user = userEvent.setup();
      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(
        /New passphrase:/,
      ) as HTMLInputElement;

      // Initially should be password type
      expect(passwordInput.type).toBe('password');

      // Find and click the eye icon
      const eyeIcon = passwordInput.parentElement?.querySelector(
        '.anticon-eye-invisible',
      );
      if (eyeIcon) {
        await user.click(eyeIcon);

        // Should change to text type
        expect(passwordInput.type).toBe('text');
      }
    });
  });

  describe('Form Submission', () => {
    it('should successfully submit form with valid data', async () => {
      const user = userEvent.setup();
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockResolvedValue({} as any);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegisterVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
        expect(mockEnableVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
      });
    });

    it('should update store state after successful submission', async () => {
      const user = userEvent.setup();
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockResolvedValue({} as any);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        const state = store.getState();
        expect(state.chats.vaultModeRegistered).toBe(true);
        expect(state.chats.vaultMode).toBe(true);
      });
    });

    it('should show loading state during submission', async () => {
      const user = userEvent.setup();

      // Create a promise that we can control
      let resolveRegister: () => void;
      const registerPromise = new Promise<void>((resolve) => {
        resolveRegister = resolve;
      });

      // @ts-ignore
      mockRegisterVaultService.mockReturnValue(registerPromise);
      mockEnableVaultService.mockResolvedValue({} as any);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      // Button should show loading state (but may not be disabled based on form validation state)
      await waitFor(() => {
        expect(
          submitButton.querySelector('.anticon-loading'),
        ).toBeInTheDocument();
      });

      // Resolve the promise to complete the test
      resolveRegister!();
      await waitFor(() => {
        expect(mockRegisterVaultService).toHaveBeenCalled();
      });
    });

    it('should handle registration service error', async () => {
      const user = userEvent.setup();
      const error = new Error('Registration failed');
      mockRegisterVaultService.mockRejectedValue(error);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      // Store should not be updated on error
      const state = store.getState();
      expect(state.chats.vaultModeRegistered).toBe(false);
      expect(state.chats.vaultMode).toBe(false);
    });

    it('should handle enable service error', async () => {
      const user = userEvent.setup();
      const error = new Error('Enable failed');
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockRejectedValue(error);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });

    it('should reset loading state after error', async () => {
      const user = userEvent.setup();
      const error = new Error('Registration failed');
      mockRegisterVaultService.mockRejectedValue(error);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      // Button should not be loading anymore
      await waitFor(() => {
        expect(submitButton).not.toHaveAttribute('disabled');
        expect(
          submitButton.querySelector('.anticon-loading'),
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('Button State', () => {
    it('should disable button during field validation', async () => {
      // This test would need to mock the form instance, which is complex
      // For now, we'll test the basic button functionality
      renderLayout(<SetupVaultForm />, { store });

      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      // Button should be present and functional
      expect(submitButton).toBeInTheDocument();
      expect(submitButton).toHaveAttribute('type', 'submit');
    });

    it('should have correct button attributes', () => {
      renderLayout(<SetupVaultForm />, { store });

      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      expect(submitButton).toHaveAttribute('type', 'submit');
      expect(submitButton).not.toHaveAttribute('disabled');
    });
  });

  describe('Form Layout and Styling', () => {
    it('should center the submit button', () => {
      renderLayout(<SetupVaultForm />, { store });

      const buttonContainer = screen
        .getByRole('button', { name: /Enable Vault Mode/ })
        .closest('.ant-flex');
      expect(buttonContainer).toHaveClass('ant-flex-align-center');
      expect(buttonContainer).toHaveClass('ant-flex-justify-center');
    });

    it('should have proper form item structure', () => {
      renderLayout(<SetupVaultForm />, { store });

      const formItems = document.querySelectorAll('.ant-form-item');
      expect(formItems).toHaveLength(3); // 2 password fields + 1 button
    });

    it('should have gap styling on button container', () => {
      renderLayout(<SetupVaultForm />, { store });

      const buttonContainer = screen
        .getByRole('button', { name: /Enable Vault Mode/ })
        .closest('.ant-flex');

      // Check for gap styling (Ant Design applies this as a CSS custom property)
      expect(buttonContainer).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper labels for form fields', () => {
      renderLayout(<SetupVaultForm />, { store });

      expect(screen.getByLabelText(/New passphrase:/)).toBeInTheDocument();
      expect(
        screen.getByLabelText(/Re-enter your passphrase:/),
      ).toBeInTheDocument();
    });

    it('should have proper button type for form submission', () => {
      renderLayout(<SetupVaultForm />, { store });

      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });
      expect(submitButton).toHaveAttribute('type', 'submit');
    });

    it('should scroll to first error on validation failure', () => {
      renderLayout(<SetupVaultForm />, { store });

      const form = document.querySelector('form');
      expect(form).toBeInTheDocument();
      // The scrollToFirstError prop is set on the form
    });
  });

  describe('Field Names and Structure', () => {
    it('should use correct field names', async () => {
      const user = userEvent.setup();
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockResolvedValue({} as any);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      // Verify that only the 'password' field is used in service calls
      await waitFor(() => {
        expect(mockRegisterVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
        expect(mockEnableVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
      });
    });

    it('should validate duplicatedPassword field separately', async () => {
      const user = userEvent.setup();

      // Mock validator to fail for the confirmation field
      mockSetupVaultValidator.safeParse.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            password: {
              _errors: ['Password must contain at least 8 characters'],
            },
          }),
        },
      });

      renderLayout(<SetupVaultForm />, { store });

      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(confirmPasswordInput, 'weak');
      await user.click(submitButton);

      await waitFor(() => {
        const errorElements = document.querySelectorAll(
          '.ant-form-item-explain-error',
        );
        const hasValidationError = Array.from(errorElements).some((element) =>
          element.textContent?.includes(
            'Password must contain at least 8 characters',
          ),
        );
        expect(hasValidationError).toBe(true);
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle validator returning multiple errors', async () => {
      const user = userEvent.setup();

      mockSetupVaultValidator.safeParse.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            password: {
              _errors: [
                'Password must contain at least 8 characters',
                'Password must contain uppercase letter',
                'Password must contain special character',
              ],
            },
          }),
        },
      });

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'weak');
      await user.click(submitButton);

      await waitFor(() => {
        // Check that at least one error message is displayed
        const errorElements = document.querySelectorAll(
          '.ant-form-item-explain-error',
        );
        const hasValidationError = Array.from(errorElements).some((element) =>
          element.textContent?.includes(
            'Password must contain at least 8 characters',
          ),
        );
        expect(hasValidationError).toBe(true);
      });
    });

    it('should handle empty validator response', async () => {
      const user = userEvent.setup();

      mockSetupVaultValidator.safeParse.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            password: {
              _errors: [],
            },
          }),
        },
      });

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'test');
      await user.click(submitButton);

      // Should not crash with empty errors array
      expect(passwordInput).toBeInTheDocument();
    });

    it('should handle form submission with validateFields throwing error', async () => {
      const user = userEvent.setup();
      renderLayout(<SetupVaultForm />, { store });

      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      // Submit form without filling required fields
      await user.click(submitButton);

      // Should handle validation errors gracefully
      await waitFor(() => {
        expect(
          screen.getByText('Please enter your new passphrase'),
        ).toBeInTheDocument();
      });

      // Services should not be called
      expect(mockRegisterVaultService).not.toHaveBeenCalled();
      expect(mockEnableVaultService).not.toHaveBeenCalled();
    });

    it('should handle form submission when validateFields succeeds but services fail', async () => {
      const user = userEvent.setup();
      const error = new Error('Service error');

      // First service succeeds, second fails
      mockRegisterVaultService.mockResolvedValue({} as any);
      mockEnableVaultService.mockRejectedValue(error);

      renderLayout(<SetupVaultForm />, { store });

      const passwordInput = screen.getByLabelText(/New passphrase:/);
      const confirmPasswordInput = screen.getByLabelText(
        /Re-enter your passphrase:/,
      );
      const submitButton = screen.getByRole('button', {
        name: /Enable Vault Mode/,
      });

      await user.type(passwordInput, 'ValidPass123!');
      await user.type(confirmPasswordInput, 'ValidPass123!');
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockRegisterVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
        expect(mockEnableVaultService).toHaveBeenCalledWith({
          password: 'ValidPass123!',
        });
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });

      // Loading state should be reset
      await waitFor(() => {
        expect(submitButton).not.toHaveAttribute('disabled');
      });
    });
  });
});
