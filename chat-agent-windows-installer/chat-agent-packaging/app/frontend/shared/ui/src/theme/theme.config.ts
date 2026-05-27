import type { ThemeConfig } from 'antd';
import { IThemeType } from '@shared/ui/interfaces/theme.interfaces';

export const antdTheme: ThemeConfig = {
  token: {
    colorPrimary: '#ff0000',
    fontSize: 16,
  },
};

const themeScreens = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
};

export const themeGeneralColors = {
  primary: '#fc1c39',
  green: '#34d399',
  darkGreen: '#3f8600',
};

export const styledLightTheme: IThemeType = {
  colors: {
    text: '#0d0d0d',
    grey: '#f9f9f9',
    light: '#f3f4f6',
    codeText: '#24292e',
    ...themeGeneralColors,
  },
  screens: themeScreens,
};

export const styledDarkTheme: IThemeType = {
  colors: {
    text: '#fff',
    grey: '#171717',
    light: '#212121',
    codeText: 'rgb(165, 214, 255)',
    ...themeGeneralColors,
  },
  screens: themeScreens,
};
