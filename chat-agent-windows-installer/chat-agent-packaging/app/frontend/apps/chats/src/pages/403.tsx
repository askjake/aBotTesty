import { NextPage } from 'next';
import Head from 'next/head';

import ForbiddenTemplate from '@shared/ui/components/templates/ForbiddenTemplate';

const ForbiddenPage: NextPage = () => {
  return (
    <>
      <Head>
        <title>403</title>
      </Head>
      <ForbiddenTemplate />
    </>
  );
};

export default ForbiddenPage;
