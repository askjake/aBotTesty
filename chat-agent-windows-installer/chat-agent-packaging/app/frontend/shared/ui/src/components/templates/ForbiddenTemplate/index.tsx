import { Result } from 'antd';
import dynamic from 'next/dynamic';

const ErrorPageContainer = dynamic(
  () => import('@shared/ui/components/containers/ErrorPageContainer'),
);

const ForbiddenTemplate = () => {
  return (
    <ErrorPageContainer>
      <Result
        status='403'
        title='403'
        subTitle='Sorry, you are not authorized to access this page.'
      />
    </ErrorPageContainer>
  );
};

export default ForbiddenTemplate;
