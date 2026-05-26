'use client';

import { Provider } from 'react-redux';
import { ReactNode, useMemo } from 'react';
import { ThemeLayout } from '@shared/ui/components/layouts/ThemeLayout';
import DeployNotifier from '@shared/ui/components/molecules/Notifiers/DeployNotifier';
import { makeStore } from '@shared/ui/store';

export default function RootLayout({ children }: { children: ReactNode }) {
  // Create store instance with empty context for client-side rendering
  const store = useMemo(() => makeStore({} as any), []);
  
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>
        <Provider store={store}>
          <ThemeLayout>
            {children}
            <DeployNotifier />
          </ThemeLayout>
        </Provider>
      </body>
    </html>
  );
}
