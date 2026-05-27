import React from 'react';
import { render, screen } from '@testing-library/react';
import InternalErrorTemplate from '@shared/ui/components/templates/InternalErrorTemplate';
import { TemplateErrorProps } from '@shared/ui/interfaces/templates.interfaces';

// Mock the dynamic import
jest.mock('next/dynamic', () => {
  return jest.fn(() => {
    const MockedErrorPageContainer = ({
      children,
    }: {
      children: React.ReactNode;
    }) => <div data-testid='error-page-container'>{children}</div>;
    return MockedErrorPageContainer;
  });
});

describe('InternalErrorTemplate', () => {
  it('should render with default error content', () => {
    render(<InternalErrorTemplate />);

    expect(screen.getByTestId('error-page-container')).toBeInTheDocument();
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(
      screen.getByText('Something went wrong. Please, try again later.'),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Back Home/ })).toHaveAttribute(
      'href',
      '/',
    );
  });

  it('should render with custom error content', () => {
    const error: TemplateErrorProps['error'] = {
      type: 'Custom Error',
      message: 'Custom error message',
    };

    render(<InternalErrorTemplate error={error} />);

    expect(screen.getByText('Custom Error')).toBeInTheDocument();
    expect(screen.getByText('Custom error message')).toBeInTheDocument();
    expect(screen.queryByText('500')).not.toBeInTheDocument();
  });

  it('should use defaults for empty error strings', () => {
    const error: TemplateErrorProps['error'] = {
      type: '',
      message: '',
    };

    render(<InternalErrorTemplate error={error} />);

    expect(screen.getByText('500')).toBeInTheDocument();
    expect(
      screen.getByText('Something went wrong. Please, try again later.'),
    ).toBeInTheDocument();
  });

  it('should have correct Result component structure', () => {
    render(<InternalErrorTemplate />);

    const resultElement = document.querySelector('.ant-result-500');
    expect(resultElement).toBeInTheDocument();
  });
});
