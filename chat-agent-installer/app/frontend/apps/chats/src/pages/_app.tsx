import { Provider } from 'react-redux';
import type { AppProps } from 'next/app';
import { FC } from 'react';
import Head from 'next/head';

import { ThemeLayout } from '@shared/ui/components/layouts/ThemeLayout';
import DeployNotifier from '@shared/ui/components/molecules/Notifiers/DeployNotifier';

import { wrapper } from '@shared/ui/store';

const MainApp: FC<AppProps> = ({ Component, ...rest }) => {
  const { store, props } = wrapper.useWrappedStore(rest);

  return (
    <>
      <Head>
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        <link rel='icon' href='/favicon.ico' />
      </Head>

      <Provider store={store}>
        <ThemeLayout>
          <Component {...props} />
          <DeployNotifier />
        </ThemeLayout>
      </Provider>
    </>
  );
};

export default MainApp;
