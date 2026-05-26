import { NextPage } from 'next';
import Head from 'next/head';

import NotFoundTemplate from '@shared/ui/components/templates/NotFoundTemplate';

const NotFoundPage: NextPage = () => {
  return (
    <>
      <Head>
        <title>404</title>
      </Head>
      <NotFoundTemplate />
    </>
  );
};

export default NotFoundPage;
