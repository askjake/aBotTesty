import { useSearchParams } from 'next/navigation';
import { useMemo } from 'react';
import Head from 'next/head';

import InternalErrorTemplate from '@shared/ui/components/templates/InternalErrorTemplate';

const InternalErrorPage = () => {
  const searchParams = useSearchParams();
  const error = useMemo(
    () => ({
      type: searchParams.get('type') || '',
      message: searchParams.get('message') || '',
    }),
    [searchParams],
  );
  return (
    <>
      <Head>
        <title>500</title>
      </Head>
      <InternalErrorTemplate error={error} />
    </>
  );
};

export default InternalErrorPage;
