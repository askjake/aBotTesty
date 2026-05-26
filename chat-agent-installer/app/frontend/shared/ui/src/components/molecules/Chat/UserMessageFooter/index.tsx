import { FC } from 'react';
import { Button, Flex, Tooltip } from 'antd';

import VersionsSwitcher from '@shared/ui/components/atoms/VersionsSwitcher';

import { UserMessageFooterProps } from '@shared/ui/components/molecules/Chat/UserMessageFooter/UserMessageFooter.props';
import { GrEdit } from 'react-icons/gr';
import { useAppSelector } from '@shared/ui/store';

const UserMessageFooter: FC<UserMessageFooterProps> = ({
  version_count,
  version_index,
  message_id,
  onChangeVersion,
  onToggleEdit,
  showEditBtn = false,
}) => {
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  return (
    <Flex gap='2' align='center'>
      {version_count > 1 && showEditBtn ? (
        <VersionsSwitcher
          totalVersions={version_count}
          currentIndex={version_index}
          updateCurrentVersion={(value) =>
            onChangeVersion({ message_id, version_index: value })
          }
        />
      ) : null}
      {showEditBtn ? (
        <Tooltip title='Edit message' placement='bottom'>
          <Button
            shape='circle'
            color='default'
            variant='text'
            size='small'
            icon={<GrEdit />}
            onClick={() => onToggleEdit(message_id)}
            disabled={aiTyping}
          />
        </Tooltip>
      ) : null}
    </Flex>
  );
};

export default UserMessageFooter;
