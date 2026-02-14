import { ReactNode, useMemo, useEffect, useState } from 'react';
import { App, ConfigProvider, theme } from 'antd';
import { ThemeProvider } from 'styled-components';
import dayjs from 'dayjs';
import 'dayjs/locale/en';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

import { useAppSelector } from '@shared/ui/store';
import {
  antdTheme,
  styledDarkTheme,
  styledLightTheme,
} from '@shared/ui/theme/theme.config';
import GlobalStyles from '@shared/ui/styles/GlobalStyles';

// Set global locale
dayjs.locale('en');

// Initialize dayjs plugins
dayjs.extend(utc);
dayjs.extend(timezone);

interface ThemeLayoutProps {
  children: ReactNode;
}

export const ThemeLayout = ({ children }: ThemeLayoutProps) => {
  // Provide fallback for theme mode if state is not initialized
  const themeMode = useAppSelector((state) => state?.settings?.themeMode || 'light');
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch by only rendering theme-dependent content after mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const styledTheme = useMemo(
    () => (themeMode === 'dark' ? styledDarkTheme : styledLightTheme),
    [themeMode],
  );

  const antdThemeConfig = useMemo(
    () => ({
      algorithm: themeMode === 'dark' ? theme.darkAlgorithm : theme.defaultAlgorithm,
      ...antdTheme,
    }),
    [themeMode],
  );

  return (
    <>
      {mounted && (
        <link
          data-testid='theme-styles'
          rel='stylesheet'
          href={themeMode === 'dark' ? '/github-dark.min.css' : '/github.min.css'}
        />
      )}
      <ConfigProvider theme={antdThemeConfig}>
        <ThemeProvider theme={styledTheme}>
          <GlobalStyles />
          <App>{children}</App>
        </ThemeProvider>
      </ConfigProvider>
    </>
  );
};
