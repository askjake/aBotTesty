import React from 'react';

import ThemeLayout from '@shared/ui/components/layouts/ThemeLayout';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { screen } from '@testing-library/react';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';

describe('ThemeLayout Component', () => {
  it(' renderLayouts without crashing', () => {
    renderLayout(
      <ThemeLayout>
        <p>Test Content</p>
      </ThemeLayout>,
    );
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('applies light theme by default', () => {
    const initialState = {
      settings: {
        themeMode: 'light',
      },
    };
    // @ts-ignore
    const store = mockStore(initialState);

    renderLayout(
      <ThemeLayout>
        <p>Test Content</p>
      </ThemeLayout>,
      { store },
    );
    const linkElement = screen.getByTestId('theme-styles');
    expect(linkElement).toHaveAttribute('href', '/github.min.css');
  });

  it('applies dark theme when themeMode is dark', () => {
    const initialState = {
      settings: {
        themeMode: 'dark',
      },
    };
    // @ts-ignore
    const store = mockStore(initialState);

    renderLayout(
      <ThemeLayout>
        <p>Test Content</p>
      </ThemeLayout>,
      { store },
    );
    const linkElement = screen.getByTestId('theme-styles');
    expect(linkElement).toHaveAttribute('href', '/github-dark.min.css');
  });
});
