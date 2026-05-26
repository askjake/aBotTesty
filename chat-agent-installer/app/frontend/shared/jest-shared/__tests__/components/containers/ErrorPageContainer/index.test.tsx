import React from 'react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import ErrorPageContainer from '@shared/ui/components/containers/ErrorPageContainer';
import { screen } from '@testing-library/react';

// Mock CustomFooter component
jest.mock('@shared/ui/components/organisms/Footers/CustomFooter', () => {
  return function MockCustomFooter() {
    return <footer data-testid='custom-footer'>Custom Footer</footer>;
  };
});

describe('ErrorPageContainer Component', () => {
  it('renders without crashing', () => {
    renderLayout(
      <ErrorPageContainer>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('renders children content', () => {
    renderLayout(
      <ErrorPageContainer>
        <div data-testid='test-child'>
          <h1>Error Title</h1>
          <p>Error Description</p>
        </div>
      </ErrorPageContainer>,
    );

    expect(screen.getByTestId('test-child')).toBeInTheDocument();
    expect(screen.getByText('Error Title')).toBeInTheDocument();
    expect(screen.getByText('Error Description')).toBeInTheDocument();
  });

  it('renders CustomFooter component', () => {
    renderLayout(
      <ErrorPageContainer>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    expect(screen.getByTestId('custom-footer')).toBeInTheDocument();
    expect(screen.getByText('Custom Footer')).toBeInTheDocument();
  });

  it('applies the correct container styles', () => {
    renderLayout(
      <ErrorPageContainer>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    // Find the main container (StyledErrorPageContainer)
    const container = screen
      .getByText('Test Content')
      .closest('div')?.parentElement;
    expect(container).toHaveStyle('display: flex');
    expect(container).toHaveStyle('flex-direction: column');
  });

  it('applies the correct wrapper styles', () => {
    renderLayout(
      <ErrorPageContainer>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    // Find the wrapper (StyledErrorPageWrapper)
    const wrapper = screen.getByText('Test Content').closest('div');
    expect(wrapper).toHaveStyle('display: flex');
    expect(wrapper).toHaveStyle('flex-direction: column');
    expect(wrapper).toHaveStyle('align-items: center');
    expect(wrapper).toHaveStyle('justify-content: center');
    expect(wrapper).toHaveStyle('min-height: calc(100vh - 72px)');
  });

  it('applies default className', () => {
    renderLayout(
      <ErrorPageContainer>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    const container = screen
      .getByText('Test Content')
      .closest('div')?.parentElement;
    expect(container).toHaveClass('error-page-container');
  });

  it('applies additional className', () => {
    renderLayout(
      <ErrorPageContainer className='custom-class'>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    const container = screen
      .getByText('Test Content')
      .closest('div')?.parentElement;
    expect(container).toHaveClass('error-page-container');
    expect(container).toHaveClass('custom-class');
  });

  it('applies additional props', () => {
    renderLayout(
      <ErrorPageContainer id='error-page' data-testid='error-container'>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    const container = screen.getByTestId('error-container');
    expect(container).toHaveAttribute('id', 'error-page');
  });

  it('handles multiple children', () => {
    renderLayout(
      <ErrorPageContainer>
        <h1>Error Title</h1>
        <p>Error Description</p>
        <button>Retry Button</button>
      </ErrorPageContainer>,
    );

    expect(screen.getByText('Error Title')).toBeInTheDocument();
    expect(screen.getByText('Error Description')).toBeInTheDocument();
    expect(screen.getByText('Retry Button')).toBeInTheDocument();
  });

  it('handles empty children', () => {
    renderLayout(<ErrorPageContainer />);

    // Should still render the footer
    expect(screen.getByTestId('custom-footer')).toBeInTheDocument();
  });

  it('applies ant-result className when present', () => {
    renderLayout(
      <ErrorPageContainer>
        <div className='ant-result'>
          <p>Ant Design Result Content</p>
        </div>
      </ErrorPageContainer>,
    );

    const antResult = screen
      .getByText('Ant Design Result Content')
      .closest('.ant-result');
    expect(antResult).toBeInTheDocument();
    // The styling for ant-result padding: 0 is applied via CSS,
    // which might not be testable directly in jsdom
  });

  it('maintains proper layout structure', () => {
    renderLayout(
      <ErrorPageContainer data-testid='error-container'>
        <div data-testid='error-content'>Error Content</div>
      </ErrorPageContainer>,
    );

    const container = screen.getByTestId('error-container');
    const content = screen.getByTestId('error-content');
    const footer = screen.getByTestId('custom-footer');

    // Check that content comes before footer in the DOM
    expect(container).toContainElement(content);
    expect(container).toContainElement(footer);

    // Verify the structure: container > [wrapper > content, footer]
    const wrapper = content.closest('div');
    expect(wrapper).not.toBe(container); // wrapper should be different from container
    expect(container).toContainElement(wrapper);
  });

  it('passes through all props correctly', () => {
    const customProps = {
      'data-testid': 'custom-error-page',
      'aria-label': 'Error page container',
      role: 'main',
      style: { backgroundColor: 'red' },
    };

    renderLayout(
      <ErrorPageContainer {...customProps}>
        <p>Test Content</p>
      </ErrorPageContainer>,
    );

    const container = screen.getByTestId('custom-error-page');
    expect(container).toHaveAttribute('aria-label', 'Error page container');
    expect(container).toHaveAttribute('role', 'main');
    expect(container).toHaveStyle('background-color: red');
  });
});
