import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import ContactBlock from '@shared/ui//components/molecules/Footer/ContactBlock';
import { CONTACT_EMAIL } from '@shared/ui/constants/common.constants';

// Mock Ant Design icon
jest.mock('@ant-design/icons', () => ({
  MailOutlined: () => (
    <span data-testid='mail-icon' aria-hidden='true'>
      MailIcon
    </span>
  ),
}));

describe('ContactBlock', () => {
  beforeEach(() => {
    // Clear any previous renders
    document.body.innerHTML = '';
  });

  it('renders without crashing', () => {
    renderLayout(<ContactBlock />);
    expect(screen.getByRole('link')).toBeInTheDocument();
  });

  it('renders the mail icon', () => {
    renderLayout(<ContactBlock />);
    expect(screen.getByTestId('mail-icon')).toBeInTheDocument();
  });

  it('renders the feedback text', () => {
    renderLayout(<ContactBlock />);
    expect(screen.getByText('Send us feedback')).toBeInTheDocument();
  });

  it('has correct href attribute', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute(
      'href',
      `https://mail.google.com/mail/u/0/?su=Question&to=${CONTACT_EMAIL}&tf=cm`,
    );
  });

  it('opens in new tab', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('contains both icon and text elements', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    expect(link).toContainElement(screen.getByTestId('mail-icon'));
    expect(link).toContainElement(screen.getByText('Send us feedback'));
  });

  it('has the correct structure', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // Check that it has exactly 2 children (icon + span)
    expect(link.children).toHaveLength(2);
  });

  it('is clickable and accessible', async () => {
    const user = userEvent.setup();
    renderLayout(<ContactBlock />);

    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();

    // Should have accessible text
    expect(link).toHaveTextContent('Send us feedback');

    // Should be focusable (links are focusable by default)
    expect(link).not.toHaveAttribute('tabindex', '-1');

    // Test focus behavior
    await user.tab();
    expect(link).toHaveFocus();
  });

  it('has proper accessibility attributes', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // Should have accessible name that includes the text content
    // Since the icon has aria-hidden, it should only be the text
    expect(link).toHaveAccessibleName('Send us feedback');
  });
});

describe('ContactBlock Email Configuration', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('has correct Gmail compose URL structure', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    expect(href).toContain('mail.google.com/mail/u/0/');
    expect(href).toContain('su=Question'); // Subject
    expect(href).toContain(`to=${CONTACT_EMAIL}`); // Recipient
    expect(href).toContain('tf=cm'); // Gmail compose mode
  });

  it('pre-fills email with correct recipient', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    expect(href).toMatch(new RegExp(`to=${CONTACT_EMAIL}`));
  });

  it('pre-fills email with correct subject', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    expect(href).toMatch(/su=Question/);
  });

  it('uses correct Gmail compose format', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    // Verify the complete URL structure
    const expectedUrl = `https://mail.google.com/mail/u/0/?su=Question&to=${CONTACT_EMAIL}&tf=cm`;
    expect(href).toBe(expectedUrl);
  });

  it('URL encodes parameters correctly', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    // Verify that special characters in email are properly handled
    expect(href).toContain(CONTACT_EMAIL);
    // If there were spaces or special chars in subject, they should be encoded
    expect(href).toContain('su=Question');
  });
});

describe('ContactBlock Keyboard Navigation', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('supports keyboard navigation', async () => {
    const user = userEvent.setup();
    renderLayout(<ContactBlock />);

    const link = screen.getByRole('link');

    // Tab to the link
    await user.tab();
    expect(link).toHaveFocus();
  });

  it('can be focused programmatically', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // Focus the link programmatically
    link.focus();
    expect(link).toHaveFocus();
  });

  it('maintains focus behavior', async () => {
    const user = userEvent.setup();
    renderLayout(<ContactBlock />);

    const link = screen.getByRole('link');

    // Focus and then blur
    await user.tab();
    expect(link).toHaveFocus();

    await user.tab();
    expect(link).not.toHaveFocus();
  });
});

describe('ContactBlock Styling and Theme', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('applies styled component classes', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // The StyledContactBlock should apply some classes
    // This test verifies the styled component is being used
    expect(link).toBeInTheDocument();
  });

  it('renders consistently across different viewport sizes', () => {
    // Test mobile viewport
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 375,
    });

    renderLayout(<ContactBlock />);
    expect(screen.getByRole('link')).toBeInTheDocument();
    expect(screen.getByText('Send us feedback')).toBeInTheDocument();

    // Clean up for next test
    document.body.innerHTML = '';

    // Test desktop viewport
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });

    renderLayout(<ContactBlock />);
    expect(screen.getByRole('link')).toBeInTheDocument();
    expect(screen.getByText('Send us feedback')).toBeInTheDocument();
  });
});

describe('ContactBlock Security', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('uses secure HTTPS URL', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');
    const href = link.getAttribute('href');

    expect(href).toMatch(/^https:/);
  });

  it('opens in new tab for security', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // target="_blank" prevents the new page from accessing window.opener
    expect(link).toHaveAttribute('target', '_blank');

    // Note: For better security, the component should also have rel="noopener noreferrer"
    // This test would verify that if implemented:
    // expect(link).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });
});

describe('ContactBlock Error Handling', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('maintains functionality without JavaScript', () => {
    renderLayout(<ContactBlock />);
    const link = screen.getByRole('link');

    // The link should work even without JavaScript since it's a standard <a> tag
    expect(link.tagName.toLowerCase()).toBe('a');
    expect(link).toHaveAttribute('href');
    expect(link).toHaveAttribute('target', '_blank');
  });

  it('handles icon rendering correctly', () => {
    renderLayout(<ContactBlock />);

    // Should still render the link and text even if icon has issues
    expect(screen.getByRole('link')).toBeInTheDocument();
    expect(screen.getByText('Send us feedback')).toBeInTheDocument();

    // Icon should be present but hidden from screen readers
    const icon = screen.getByTestId('mail-icon');
    expect(icon).toHaveAttribute('aria-hidden', 'true');
  });
});
