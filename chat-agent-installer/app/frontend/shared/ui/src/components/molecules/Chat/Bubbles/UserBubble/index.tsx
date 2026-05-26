import { memo } from 'react';

import { renderUserInputInMessage } from '@shared/ui/utils/messages.utils';

import UserMessageFooter from '@shared/ui/components/molecules/Chat/UserMessageFooter';
import UserAvatar from '@shared/ui/components/atoms/Avatars/UserAvatar';
import EditUserMessageFooter from '@shared/ui/components/molecules/Chat/EditUserMessageFooter';
import CustomBubble from '@shared/ui/components/atoms/Bubbles/CustomBubble';

import { RenderUserMessagesResultType } from '@shared/ui/types/messages.types';
import { RoleEnum } from '@shared/ui/enums/chats.enums';

const UserBubble = memo(
  ({ bubble, user }: { bubble: RenderUserMessagesResultType; user: any }) => {
    const {
      version_count,
      version_index,
      key,
      edit = false,
      refInput,
      showEditBtn,
      onChangeVersion,
      onToggleEdit,
      onSaveEdit,
      onCancelEdit,
      content = {},
      readyOnlyChat = false,
    } = bubble;

    return (
      <CustomBubble
        role={RoleEnum.USER}
        placement='end'
        shape='corner'
        avatar={<UserAvatar userEmail={user.email} />}
        content={content[0]?.text || ''}
        contentRender={() =>
          renderUserInputInMessage({
            content: content[0]?.text || '',
            refInput,
            edit,
          })
        }
        footer={
          readyOnlyChat ? null : !edit ? (
            <UserMessageFooter
              version_count={version_count}
              version_index={version_index}
              message_id={key as string}
              onChangeVersion={onChangeVersion}
              onToggleEdit={onToggleEdit}
              showEditBtn={showEditBtn}
            />
          ) : (
            <EditUserMessageFooter
              message_id={key as string}
              onCancel={onCancelEdit}
              onSave={onSaveEdit}
            />
          )
        }
      />
    );
  },
);

export default UserBubble;
