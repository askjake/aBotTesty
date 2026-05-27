import { FC, useState } from 'react';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { createChat } from '@shared/ui/services/chats.services';
import {
  setActiveChat,
  setChats,
  setTotalChats,
} from '@shared/ui/store/chats/chats.slice';
import { setActiveChatGroup } from '@shared/ui/store/chatsGroups/chatsGroups.slice';

import { StyledEmptyChats } from '@/components/molecules/Empty/EmptyChats/EmptyChats.styled';

import { EmptyChatsProps } from '@/components/molecules/Empty/EmptyChats/EmptyChats.props';
import { Button } from 'antd';
import { SearchOutlined } from '@ant-design/icons';

const EmptyChats: FC<EmptyChatsProps> = ({ className = '', ...props }) => {
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
    <StyledEmptyChats
      className={`empty-chats ${className}`}
      description='No chats were found'
      image={<SearchOutlined />}
      {...props}
    >
      <Button onClick={createNewChat} loading={loading}>
        Create chat
      </Button>
    </StyledEmptyChats>
  );
};

export default EmptyChats;
