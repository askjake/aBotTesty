import { memo } from 'react';
import { Alert, Avatar } from 'antd';
import { BsRobot } from 'react-icons/bs';
import CustomBubble from '@shared/ui/components/atoms/Bubbles/CustomBubble';

const ErrorBubble = memo(({ bubble }: { bubble: any }) => {
  return (
    <CustomBubble
      role='error'
      placement='start'
      loading={bubble.loading}
      avatar={<Avatar icon={<BsRobot />} />}
      content=''
      contentRender={() => (
        <Alert description={bubble.content} type='warning' showIcon />
      )}
    />
  );
});

export default ErrorBubble;
