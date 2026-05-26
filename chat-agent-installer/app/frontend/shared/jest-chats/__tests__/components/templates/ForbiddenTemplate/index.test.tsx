import React from 'react';
import { render, screen } from '@testing-library/react';
import ForbiddenTemplate from '@shared/ui/components/templates/ForbiddenTemplate';

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

describe('ForbiddenTemplate', () => {
  it('should render 403 error page with correct content', () => {
    render(<ForbiddenTemplate />);

    // Check container
    expect(screen.getByTestId('error-page-container')).toBeInTheDocument();

    // Check Result component content
    expect(screen.getByText('403')).toBeInTheDocument();
    expect(
      screen.getByText('Sorry, you are not authorized to access this page.'),
    ).toBeInTheDocument();

    // Check Result component structure
    const resultElement = document.querySelector('.ant-result-403');
    expect(resultElement).toBeInTheDocument();
  });

  it('should have proper accessibility structure', () => {
    render(<ForbiddenTemplate />);

    const title = screen.getByText('403');
    const subtitle = screen.getByText(
      'Sorry, you are not authorized to access this page.',
    );

    expect(title.closest('.ant-result-title')).toBeInTheDocument();
    expect(subtitle.closest('.ant-result-subtitle')).toBeInTheDocument();
  });
});
