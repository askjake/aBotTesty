import React from 'react';
import { render, screen } from '@testing-library/react';
import VaultModeTemplate from '@/components/templates/VaultModeTemplate';

// Mock the store hook
const mockUseAppSelector = jest.fn();
jest.mock('@shared/ui/store', () => ({
  useAppSelector: () => mockUseAppSelector(),
}));

// Mock components with absolute paths
jest.mock(
  '@/components/templates/VaultModeTemplate/VaultModeTemplate.styled',
  () => ({
    StyledVaultModeContainer: ({
      children,
      variant,
    }: {
      children: React.ReactNode;
      variant?: string;
    }) => (
      <div data-testid='styled-vault-mode-container' data-variant={variant}>
        {children}
      </div>
    ),
  }),
);

jest.mock('@/components/containers/ContainerWithSidebar', () => {
  return ({ children }: { children: React.ReactNode }) => (
    <div data-testid='container-with-sidebar'>{children}</div>
  );
});

jest.mock('@/components/organisms/VaultMode/FAQVaultBlock', () => () => (
  <div data-testid='faq-vault-block'>FAQ Vault Block</div>
));

jest.mock('@/components/organisms/VaultMode/UpdateVaultForm', () => () => (
  <div data-testid='update-vault-form'>Update Vault Form</div>
));

jest.mock('@/components/organisms/VaultMode/SetupVaultForm', () => () => (
  <div data-testid='setup-vault-form'>Setup Vault Form</div>
));

describe('VaultModeTemplate', () => {
  it('should render with SetupVaultForm when not registered', () => {
    mockUseAppSelector.mockReturnValue(false);

    render(<VaultModeTemplate />);

    expect(screen.getByTestId('container-with-sidebar')).toBeInTheDocument();
    expect(screen.getByText('Vault Mode settings')).toBeInTheDocument();
    expect(screen.getByTestId('faq-vault-block')).toBeInTheDocument();
    expect(screen.getByTestId('setup-vault-form')).toBeInTheDocument();
    expect(screen.queryByTestId('update-vault-form')).not.toBeInTheDocument();
  });

  it('should render with UpdateVaultForm when registered', () => {
    mockUseAppSelector.mockReturnValue(true);

    render(<VaultModeTemplate />);

    expect(screen.getByTestId('container-with-sidebar')).toBeInTheDocument();
    expect(screen.getByText('Vault Mode settings')).toBeInTheDocument();
    expect(screen.getByTestId('faq-vault-block')).toBeInTheDocument();
    expect(screen.getByTestId('update-vault-form')).toBeInTheDocument();
    expect(screen.queryByTestId('setup-vault-form')).not.toBeInTheDocument();
  });

  it('should have correct component structure and props', () => {
    mockUseAppSelector.mockReturnValue(false);

    render(<VaultModeTemplate />);

    const styledContainer = screen.getByTestId('styled-vault-mode-container');
    expect(styledContainer).toHaveAttribute('data-variant', 'borderless');

    const title = screen.getByText('Vault Mode settings');
    expect(title.tagName).toBe('H2');
  });

  it('should handle state changes correctly', () => {
    mockUseAppSelector.mockReturnValue(false);
    const { rerender } = render(<VaultModeTemplate />);

    expect(screen.getByTestId('setup-vault-form')).toBeInTheDocument();

    mockUseAppSelector.mockReturnValue(true);
    rerender(<VaultModeTemplate />);

    expect(screen.getByTestId('update-vault-form')).toBeInTheDocument();
    expect(screen.queryByTestId('setup-vault-form')).not.toBeInTheDocument();
  });
});
