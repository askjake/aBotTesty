import React from 'react';
import { render, screen } from '@testing-library/react';
import NotFoundTemplate from '@shared/ui/components/templates/NotFoundTemplate';

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

describe('NotFoundTemplate', () => {
  it('should render 404 error page with correct content', () => {
    render(<NotFoundTemplate />);

    // Check container
    expect(screen.getByTestId('error-page-container')).toBeInTheDocument();

    // Check Result component content
    expect(screen.getByText('404')).toBeInTheDocument();
    expect(
      screen.getByText('Sorry, the page you visited does not exist.'),
    ).toBeInTheDocument();

    // Check Result component structure
    const resultElement = document.querySelector('.ant-result-404');
    expect(resultElement).toBeInTheDocument();

    // Check Back Home button
    const backHomeButton = screen.getByRole('link', { name: /Back Home/ });
    expect(backHomeButton).toBeInTheDocument();
    expect(backHomeButton).toHaveAttribute('href', '/');
  });

  it('should render button with correct styling and attributes', () => {
    render(<NotFoundTemplate />);

    const button = screen.getByRole('link', { name: /Back Home/ });
    expect(button).toHaveClass('ant-btn-primary');
    expect(button).toHaveAttribute('href', '/');
  });
});
