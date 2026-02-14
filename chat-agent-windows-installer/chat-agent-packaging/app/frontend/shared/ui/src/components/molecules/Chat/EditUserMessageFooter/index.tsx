import { FC } from 'react';
import { Button, Flex } from 'antd';

import { EditUserMessageFooterProps } from '@shared/ui/components/molecules/Chat/EditUserMessageFooter/EditUserMessageFooter.props';

const EditUserMessageFooter: FC<EditUserMessageFooterProps> = ({
  message_id,
  onSave,
  onCancel,
}) => {
  return (
    <Flex gap={4} align='center' justify='flex-end'>
      <Button size='small' onClick={() => onCancel(message_id)}>
        Cancel
      </Button>
      <Button size='small' type='primary' onClick={() => onSave(message_id)}>
        Save
      </Button>
    </Flex>
  );
};

export default EditUserMessageFooter;
