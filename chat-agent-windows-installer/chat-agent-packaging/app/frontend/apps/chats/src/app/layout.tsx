'use client';

import { Provider } from 'react-redux';
import { ReactNode } from 'react';
import { ThemeLayout } from '@shared/ui/components/layouts/ThemeLayout';
import DeployNotifier from '@shared/ui/components/molecules/Notifiers/DeployNotifier';
import { makeStore } from '@shared/ui/store';

// Create store instance for App Router
// Note: This creates a single store instance per app load
// For SSR with state hydration, you'd need a more complex setup
const store = makeStore();

export default function RootLayout({ children }: { children: ReactNode }) {
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