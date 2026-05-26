import { PlusOutlined } from '@ant-design/icons';
import { FC, useState } from 'react';
import { Tooltip } from 'antd';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { createChat } from '@shared/ui/services/chats.services';
import {
  setActiveChat,
  setChats,
  setTotalChats,
} from '@shared/ui/store/chats/chats.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { setActiveChatGroup } from '@shared/ui/store/chatsGroups/chatsGroups.slice';

import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';

import { CreateChatButtonProps } from '@/components/molecules/Buttons/CreateChatButton/CreateChatButton.props';

const CreateChatButton: FC<CreateChatButtonProps> = ({
  className = '',
  disabled = false,
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const totalChats = useAppSelector((store) => store.chats.totalChats);
  const chats = useAppSelector((store) => store.chats.chats);
  const [loading, setLoading] = useState(false);

  const createNewChat = async () => {
    try {
      setLoading(true);
      const chat = await createChat({
        namespace: 'generic',
      });
      dispatch(
        setChats([
          { ...chat, active: true, messages: {} },
          ...chats.map((item) => ({
            ...item,
            active: false,
          })),
        ]),
      );
      dispatch(setActiveChat({ ...chat, active: true, messages: {} }));
      dispatch(setTotalChats(totalChats + 1));
      dispatch(setActiveChatGroup('all'));
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Tooltip title='Create a new chat'>
      <IconButton
        className={`create-chat-button ${className}`}
        onClick={() => createNewChat()}
        disabled={disabled}
        type='text'
        icon={<PlusOutlined />}
        loading={loading}
        {...props}
      />
    </Tooltip>
  );
};

export default CreateChatButton;
