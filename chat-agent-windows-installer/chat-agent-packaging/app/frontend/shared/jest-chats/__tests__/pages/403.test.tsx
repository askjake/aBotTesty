import React from 'react';
import { screen } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import ForbiddenPage from '@/pages/403';

// Mock Next.js Head component
jest.mock('next/head', () => () => null);

// Mock the ForbiddenTemplate component
jest.mock('@shared/ui/components/templates/ForbiddenTemplate', () => () => (
  <div data-testid='forbidden-template'>403 Forbidden</div>
));

describe('ForbiddenPage', () => {
  it('should render 403 forbidden page', () => {
    const store = mockStore();
    renderLayout(<ForbiddenPage />, { store });

    expect(screen.getByTestId('forbidden-template')).toBeInTheDocument();
  });
});
