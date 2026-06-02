import { Button, Result } from 'antd';
import dynamic from 'next/dynamic';

const ErrorPageContainer = dynamic(
  () => import('@shared/ui/components/containers/ErrorPageContainer'),
);

const NotFoundTemplate = () => {
  return (
    <ErrorPageContainer>
      <Result
        status='404'
        title='404'
        subTitle='Sorry, the page you visited does not exist.'
        extra={
          <Button type='primary' href='/'>
            Back Home
          </Button>
        }
      />
    </ErrorPageContainer>
  );
};

export default NotFoundTemplate;
