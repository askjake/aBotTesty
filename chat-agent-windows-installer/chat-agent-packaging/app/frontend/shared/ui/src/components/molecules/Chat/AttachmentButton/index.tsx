import { FC } from 'react';
import { Badge, Button } from 'antd';
import { PaperClipOutlined } from '@ant-design/icons';

import { AttachmentButtonProps } from '@shared/ui/components/molecules/Chat/AttachmentButton/AttachmentButton.props';

const AttachmentButton: FC<AttachmentButtonProps> = ({
  setHeaderOpen,
  headerOpen = false,
  hasFiles = false,
  ...props
}) => {
  return (
    <Badge dot={hasFiles && !headerOpen}>
      <Button
        type='text'
        shape='circle'
        icon={<PaperClipOutlined />}
        onClick={() => setHeaderOpen(!headerOpen)}
        {...props}
      />
    </Badge>
  );
};

export default AttachmentButton;
