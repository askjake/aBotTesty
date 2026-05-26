// __tests__/components/organisms/Footers/CustomFooter/CustomFooter.test.tsx
import React from 'react';
import { screen } from '@testing-library/react';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import CustomFooter from '@shared/ui/components/organisms/Footers/CustomFooter';

// Mock the ContactBlock component
jest.mock('@shared/ui/components/molecules/Footer/ContactBlock', () => {
  const MockContactBlock = function MockContactBlock() {
    return <div data-testid='contact-block'>Contact Block Content</div>;
  };
  MockContactBlock.displayName = 'MockContactBlock';
  return MockContactBlock;
});

// Mock the HealthBlock component
jest.mock('@shared/ui/components/molecules/Footer/HealthBlock', () => {
  const MockHealthBlock = function MockHealthBlock() {
    return <div data-testid='health-block'>Health Block Content</div>;
  };
  MockHealthBlock.displayName = 'MockHealthBlock';
  return MockHealthBlock;
});

// Mock the ReleaseModal component
jest.mock('@shared/ui/components/molecules/Modals/ReleaseModal', () => {
  const MockReleaseModal = function MockReleaseModal() {
    return <div data-testid='release-modal'>Release Modal Content</div>;
  };
  MockReleaseModal.displayName = 'MockReleaseModal';
  return MockReleaseModal;
});

// Mock next/dynamic to return the mocked components
jest.mock('next/dynamic', () => {
  return (importFn: () => Promise<any>) => {
    const importPath = importFn.toString();

    if (importPath.includes('HealthBlock')) {
      const DynamicHealthBlock = function DynamicHealthBlock() {
        return <div data-testid='health-block'>Health Block Content</div>;
      };
      DynamicHealthBlock.displayName = 'DynamicHealthBlock';
      return DynamicHealthBlock;
    }

    if (importPath.includes('ReleaseModal')) {
      const DynamicReleaseModal = function DynamicReleaseModal() {
        return <div data-testid='release-modal'>Release Modal Content</div>;
      };
      DynamicReleaseModal.displayName = 'DynamicReleaseModal';
      return DynamicReleaseModal;
    }

    // Default fallback
    const DynamicComponent = function DynamicComponent() {
      return <div data-testid='dynamic-component'>Dynamic Component</div>;
    };
    DynamicComponent.displayName = 'DynamicComponent';
    return DynamicComponent;
  };
});

// Mock the styled component
jest.mock(
  '@shared/ui/components/organisms/Footers/CustomFooter/CustomFooter.styled',
  () => ({
    StyledCustomFooter: ({ children, ...props }: any) => (
      <footer data-testid='styled-custom-footer' {...props}>
        {children}
      </footer>
    ),
  }),
);

describe('CustomFooter', () => {
  let store: ReturnType<typeof mockStore>;

  beforeEach(() => {
    store = mockStore();
  });

  it('should render the footer with correct test id', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');
    expect(footer).toBeInTheDocument();
  });

  it('should have the correct CSS class', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');
    expect(footer).toHaveClass('custom-footer');
  });

  it('should render the HealthBlock component', () => {
    renderLayout(<CustomFooter />, { store });

    const healthBlock = screen.getByTestId('health-block');
    expect(healthBlock).toBeInTheDocument();
    expect(healthBlock).toHaveTextContent('Health Block Content');
  });

  it('should render the ContactBlock component', () => {
    renderLayout(<CustomFooter />, { store });

    const contactBlock = screen.getByTestId('contact-block');
    expect(contactBlock).toBeInTheDocument();
    expect(contactBlock).toHaveTextContent('Contact Block Content');
  });

  it('should render the ReleaseModal component', () => {
    renderLayout(<CustomFooter />, { store });

    const releaseModal = screen.getByTestId('release-modal');
    expect(releaseModal).toBeInTheDocument();
    expect(releaseModal).toHaveTextContent('Release Modal Content');
  });

  it('should render all three components: HealthBlock, ContactBlock, and ReleaseModal', () => {
    renderLayout(<CustomFooter />, { store });

    const healthBlock = screen.getByTestId('health-block');
    const contactBlock = screen.getByTestId('contact-block');
    const releaseModal = screen.getByTestId('release-modal');

    expect(healthBlock).toBeInTheDocument();
    expect(contactBlock).toBeInTheDocument();
    expect(releaseModal).toBeInTheDocument();
  });

  it('should be a footer element', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');
    expect(footer.tagName).toBe('FOOTER');
  });

  it('should contain all child components within the footer', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');
    const healthBlock = screen.getByTestId('health-block');
    const contactBlock = screen.getByTestId('contact-block');
    const releaseModal = screen.getByTestId('release-modal');

    expect(footer).toContainElement(healthBlock);
    expect(footer).toContainElement(contactBlock);
    expect(footer).toContainElement(releaseModal);
  });

  it('should render correctly with dark theme', () => {
    renderLayout(<CustomFooter />, { store, theme: 'dark' });

    const footer = screen.getByTestId('custom-footer');
    const healthBlock = screen.getByTestId('health-block');
    const contactBlock = screen.getByTestId('contact-block');
    const releaseModal = screen.getByTestId('release-modal');

    expect(footer).toBeInTheDocument();
    expect(footer).toHaveClass('custom-footer');
    expect(healthBlock).toBeInTheDocument();
    expect(contactBlock).toBeInTheDocument();
    expect(releaseModal).toBeInTheDocument();
  });

  it('should render correctly with light theme', () => {
    renderLayout(<CustomFooter />, { store, theme: 'light' });

    const footer = screen.getByTestId('custom-footer');
    const healthBlock = screen.getByTestId('health-block');
    const contactBlock = screen.getByTestId('contact-block');
    const releaseModal = screen.getByTestId('release-modal');

    expect(footer).toBeInTheDocument();
    expect(footer).toHaveClass('custom-footer');
    expect(healthBlock).toBeInTheDocument();
    expect(contactBlock).toBeInTheDocument();
    expect(releaseModal).toBeInTheDocument();
  });

  it('should have correct component structure', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');

    // Should have exactly 3 children (HealthBlock, ContactBlock, and ReleaseModal)
    expect(footer.children).toHaveLength(3);
  });

  it('should render components in correct order', () => {
    renderLayout(<CustomFooter />, { store });

    const footer = screen.getByTestId('custom-footer');
    const children = Array.from(footer.children);

    // HealthBlock should be first
    expect(children[0]).toHaveAttribute('data-testid', 'health-block');
    // ContactBlock should be second
    expect(children[1]).toHaveAttribute('data-testid', 'contact-block');
    // ReleaseModal should be third
    expect(children[2]).toHaveAttribute('data-testid', 'release-modal');
  });

  it('should match snapshot with light theme', () => {
    const { container } = renderLayout(<CustomFooter />, {
      store,
      theme: 'light',
    });
    expect(container.firstChild).toMatchSnapshot();
  });

  it('should match snapshot with dark theme', () => {
    const { container } = renderLayout(<CustomFooter />, {
      store,
      theme: 'dark',
    });
    expect(container.firstChild).toMatchSnapshot();
  });
});

describe('CustomFooter Dynamic Import', () => {
  it('should handle HealthBlock as a dynamic import', () => {
    renderLayout(<CustomFooter />, { store: mockStore() });

    // The HealthBlock should still render even though it's dynamically imported
    const healthBlock = screen.getByTestId('health-block');
    expect(healthBlock).toBeInTheDocument();
  });

  it('should handle ReleaseModal as a dynamic import', () => {
    renderLayout(<CustomFooter />, { store: mockStore() });

    // The ReleaseModal should still render even though it's dynamically imported
    const releaseModal = screen.getByTestId('release-modal');
    expect(releaseModal).toBeInTheDocument();
  });

  it('should render ContactBlock as a regular import', () => {
    renderLayout(<CustomFooter />, { store: mockStore() });

    // The ContactBlock should render as a regular import
    const contactBlock = screen.getByTestId('contact-block');
    expect(contactBlock).toBeInTheDocument();
  });

  it('should handle multiple dynamic imports correctly', () => {
    renderLayout(<CustomFooter />, { store: mockStore() });

    // Both dynamic imports should work
    const healthBlock = screen.getByTestId('health-block');
    const releaseModal = screen.getByTestId('release-modal');

    expect(healthBlock).toBeInTheDocument();
    expect(releaseModal).toBeInTheDocument();
  });
});
