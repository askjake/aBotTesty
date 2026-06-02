// __tests__/components/organisms/VaultMode/FAQVaultBlock/FAQVaultBlock.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from 'styled-components';
import FAQVaultBlock from '@/components/organisms/VaultMode/FAQVaultBlock';

// Mock theme for styled-components
const mockTheme = {
  colors: {
    primary: '#1890ff',
    text: '#000000',
  },
};

// Helper function to render with theme
const renderWithTheme = (component: React.ReactElement) => {
  return render(<ThemeProvider theme={mockTheme}>{component}</ThemeProvider>);
};

describe('FAQVaultBlock', () => {
  it('should render the FAQ collapse component', () => {
    renderWithTheme(<FAQVaultBlock />);

    // Check if the collapse component is rendered by its class
    const collapseElement = document.querySelector('.ant-collapse');
    expect(collapseElement).toBeInTheDocument();
  });

  it('should have correct default configuration', () => {
    renderWithTheme(<FAQVaultBlock />);

    const collapseElement = document.querySelector('.ant-collapse');
    expect(collapseElement).toHaveClass('ant-collapse-large');
  });

  it('should render both FAQ items', () => {
    renderWithTheme(<FAQVaultBlock />);

    // Check for the first FAQ item
    const vaultModeQuestion = screen.getByText('What is Vault Mode?');
    expect(vaultModeQuestion).toBeInTheDocument();

    // Check for the second FAQ item
    const passphraseQuestion = screen.getByText('Passphrase requirements');
    expect(passphraseQuestion).toBeInTheDocument();
  });

  it('should have both panels expanded by default', () => {
    renderWithTheme(<FAQVaultBlock />);

    // Both panels should be expanded by default (defaultActiveKey=['1', '2'])
    const firstPanelContent = screen.getByText(
      /Vault mode is a togglable mode/,
    );
    const secondPanelContent = screen.getByText(
      /Between 8 and 32 characters long/,
    );

    expect(firstPanelContent).toBeVisible();
    expect(secondPanelContent).toBeVisible();
  });

  it('should have correct ARIA attributes for expanded panels', () => {
    renderWithTheme(<FAQVaultBlock />);

    // Check for button elements (panel headers)
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);

    // Check that both panels are expanded
    buttons.forEach((button) => {
      expect(button).toHaveAttribute('aria-expanded', 'true');
    });
  });

  describe('Vault Mode FAQ Content', () => {
    it('should display vault mode explanation', () => {
      renderWithTheme(<FAQVaultBlock />);

      const explanation = screen.getByText(
        /Vault mode is a togglable mode that enables extra encryption/,
      );
      expect(explanation).toBeInTheDocument();
    });

    it('should display warning about losing passphrase', () => {
      renderWithTheme(<FAQVaultBlock />);

      const warning = screen.getByText(
        /However, if you lose your passphrase, all your data in vault will be lost/,
      );
      expect(warning).toBeInTheDocument();

      // Check if the warning text is bold/strong
      const strongElement = warning.closest('strong');
      expect(strongElement).toBeInTheDocument();
    });

    it('should display information about data encryption outside vault mode', () => {
      renderWithTheme(<FAQVaultBlock />);

      const encryptionInfo = screen.getByText(
        /Outside of vault mode, all data is still encrypted at rest/,
      );
      expect(encryptionInfo).toBeInTheDocument();
    });
  });

  describe('Passphrase Requirements Content', () => {
    it('should display length requirement', () => {
      renderWithTheme(<FAQVaultBlock />);

      const lengthReq = screen.getByText(/Between 8 and 32 characters long/);
      expect(lengthReq).toBeInTheDocument();
    });

    it('should display character type requirements', () => {
      renderWithTheme(<FAQVaultBlock />);

      const allowedChars = screen.getByText(
        /Contains only alphabets, numbers, and special characters/,
      );
      expect(allowedChars).toBeInTheDocument();
    });

    it('should display lowercase requirement', () => {
      renderWithTheme(<FAQVaultBlock />);

      const lowercaseReq = screen.getByText(
        /Contains at least 1 lower case alphabet/,
      );
      expect(lowercaseReq).toBeInTheDocument();
    });

    it('should display uppercase requirement', () => {
      renderWithTheme(<FAQVaultBlock />);

      const uppercaseReq = screen.getByText(
        /Contains at least 1 upper case alphabet/,
      );
      expect(uppercaseReq).toBeInTheDocument();
    });

    it('should display number requirement', () => {
      renderWithTheme(<FAQVaultBlock />);

      const numberReq = screen.getByText(/Contains at least 1 number/);
      expect(numberReq).toBeInTheDocument();
    });

    it('should display special character requirement', () => {
      renderWithTheme(<FAQVaultBlock />);

      const specialCharReq = screen.getByText(
        /Contains at least 1 special character in:/,
      );
      expect(specialCharReq).toBeInTheDocument();
    });

    it('should display allowed special characters', () => {
      renderWithTheme(<FAQVaultBlock />);

      // Check for the special characters - they appear twice in the content
      const specialCharsElements = screen.getAllByText(
        /[#$%&'()*+,\-./:;<=>?@[\]^_`{|}~]/,
      );
      expect(specialCharsElements.length).toBeGreaterThan(0);
    });

    it('should render all passphrase requirements as list items', () => {
      renderWithTheme(<FAQVaultBlock />);

      // Check for list items - there should be 7 total (1 in first panel, 6 in second panel)
      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(7);
    });
  });

  describe('Interaction', () => {
    it('should allow collapsing and expanding panels', async () => {
      const user = userEvent.setup();
      renderWithTheme(<FAQVaultBlock />);

      // Find the first panel header button
      const firstPanelButton = screen.getByRole('button', {
        name: /What is Vault Mode?/,
      });
      const firstPanelContent = screen.getByText(
        /Vault mode is a togglable mode/,
      );

      // Content should be visible initially
      expect(firstPanelContent).toBeVisible();
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'true');

      // Click to collapse
      await user.click(firstPanelButton);

      // Panel should be collapsed
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'false');

      // Click to expand again
      await user.click(firstPanelButton);

      // Panel should be expanded again
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'true');
    });

    it('should handle multiple panels independently', async () => {
      const user = userEvent.setup();
      renderWithTheme(<FAQVaultBlock />);

      const firstPanelButton = screen.getByRole('button', {
        name: /What is Vault Mode?/,
      });
      const secondPanelButton = screen.getByRole('button', {
        name: /Passphrase requirements/,
      });

      // Both should be expanded initially
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'true');
      expect(secondPanelButton).toHaveAttribute('aria-expanded', 'true');

      // Collapse first panel
      await user.click(firstPanelButton);

      // First should be collapsed, second should still be expanded
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'false');
      expect(secondPanelButton).toHaveAttribute('aria-expanded', 'true');

      // Collapse second panel
      await user.click(secondPanelButton);

      // Both should be collapsed
      expect(firstPanelButton).toHaveAttribute('aria-expanded', 'false');
      expect(secondPanelButton).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Accessibility', () => {
    it('should have proper keyboard navigation', async () => {
      const user = userEvent.setup();
      renderWithTheme(<FAQVaultBlock />);

      const firstButton = screen.getByRole('button', {
        name: /What is Vault Mode?/,
      });

      // Initially should be expanded
      expect(firstButton).toHaveAttribute('aria-expanded', 'true');

      // Focus and test Enter key
      firstButton.focus();
      await user.keyboard('{Enter}');

      // Wait a bit for the state to update
      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(firstButton).toHaveAttribute('aria-expanded', 'false');

      // Press Enter again to expand
      await user.keyboard('{Enter}');

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(firstButton).toHaveAttribute('aria-expanded', 'true');
    });

    it('should have proper tabindex for keyboard navigation', () => {
      renderWithTheme(<FAQVaultBlock />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        expect(button).toHaveAttribute('tabindex', '0');
      });
    });
  });

  describe('Content Structure', () => {
    it('should render content in proper structure', () => {
      renderWithTheme(<FAQVaultBlock />);

      // Check that we have the expected number of lists
      const lists = screen.getAllByRole('list');
      expect(lists).toHaveLength(2);
    });

    it('should have proper collapse item structure', () => {
      renderWithTheme(<FAQVaultBlock />);

      // Check for collapse items
      const collapseItems = document.querySelectorAll('.ant-collapse-item');
      expect(collapseItems).toHaveLength(2);

      // Both should be active (expanded)
      collapseItems.forEach((item) => {
        expect(item).toHaveClass('ant-collapse-item-active');
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle component unmounting gracefully', () => {
      const { unmount } = renderWithTheme(<FAQVaultBlock />);

      expect(() => unmount()).not.toThrow();
    });

    it('should render without theme provider', () => {
      expect(() => render(<FAQVaultBlock />)).not.toThrow();
    });

    it('should render all required content elements', () => {
      renderWithTheme(<FAQVaultBlock />);

      // Verify key content is present
      expect(screen.getByText('What is Vault Mode?')).toBeInTheDocument();
      expect(screen.getByText('Passphrase requirements')).toBeInTheDocument();
      expect(
        screen.getByText(/Vault mode is a togglable mode/),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Between 8 and 32 characters long/),
      ).toBeInTheDocument();
    });
  });
});
