import { Button, Result } from 'antd';
import dynamic from 'next/dynamic';
import { FC } from 'react';

const ErrorPageContainer = dynamic(
  () => import('@shared/ui/components/containers/ErrorPageContainer'),
);

import { TemplateErrorProps } from '@shared/ui/interfaces/templates.interfaces';

const InternalErrorTemplate: FC<TemplateErrorProps> = ({ error }) => {
  return (
    <ErrorPageContainer>
      <Result
        status='500'
        title={error?.type?.length ? error.type : '500'}
        subTitle={
          error?.message?.length
            ? error?.message
            : 'Something went wrong. Please, try again later.'
        }
        extra={
          <Button type='primary' href='/'>
            Back Home
          </Button>
        }
      />
    </ErrorPageContainer>
  );
};

export default InternalErrorTemplate;
