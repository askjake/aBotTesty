import React, { JSX } from 'react';
import { render as rtlRender } from '@testing-library/react';
import { ThemeProvider } from 'styled-components';
import { Provider } from 'react-redux';
import { mockStore } from '../store/mockStore';
import {
  styledDarkTheme,
  styledLightTheme,
} from '@shared/ui/theme/theme.config';

const renderLayout = (
  ui: React.ReactElement,
  {
    theme = 'light',
    store = mockStore(),
    ...renderOptions
  }: {
    store?: any;
    theme?: 'light' | 'dark';
  } = {},
) => {
  function Wrapper({ children }: { children: React.ReactNode }): JSX.Element {
    return (
      <Provider store={store}>
        <ThemeProvider
          theme={theme === 'light' ? styledLightTheme : styledDarkTheme}
        >
          {children}
        </ThemeProvider>
      </Provider>
    );
  }

  return rtlRender(ui, { wrapper: Wrapper, ...renderOptions });
};

export default renderLayout;
