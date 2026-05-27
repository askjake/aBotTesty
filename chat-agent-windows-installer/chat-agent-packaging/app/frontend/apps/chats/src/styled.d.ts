import 'styled-components';

// and extend them!
declare module 'styled-components' {
  export interface DefaultTheme {
    colors: {
      [key: string]: string;
    };
    screens: {
      [key: string]: string;
    };
  }
}
