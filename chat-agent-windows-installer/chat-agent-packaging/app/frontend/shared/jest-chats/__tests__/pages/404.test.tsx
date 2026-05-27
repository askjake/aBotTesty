import React from 'react';
import { screen } from '@testing-library/react';
import NotFoundPage from '@/pages/404';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock Next.js Head component
jest.mock('next/head', () => () => null);

// Mock the NotFoundTemplate component
jest.mock('@shared/ui/components/templates/NotFoundTemplate', () => () => (
  <div data-testid='not-found-template'>404 Not Found</div>
));

describe('NotFoundPage', () => {
  it('should render 404 not found page', () => {
    const store = mockStore();
    renderLayout(<NotFoundPage />, { store });

    expect(screen.getByTestId('not-found-template')).toBeInTheDocument();
  });
});
