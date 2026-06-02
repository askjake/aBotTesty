import { FC, useEffect, useState } from 'react';
import { App, Modal } from 'antd';

import { getMessages } from '@shared/ui/services/messages.services';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import { transformMessagesToObject } from '@shared/ui/utils/messages.utils';
import { deleteChat, getChat } from '@shared/ui/services/chats.services';
import {
  setActiveChat,
  setChats,
  setHasMoreMessages,
  setTotalChats,
} from '@shared/ui/store/chats/chats.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

import { DeleteChatModalProps } from '@/components/molecules/Modals/Chat/DeleteChatModal/DeleteChatModal.props';
import { ChatType } from '@shared/ui/types/chats.types';

const DeleteChatModal: FC<DeleteChatModalProps> = ({
  className = '',
  deleteId,
  setDeleteId,
  onCloseCb = () => {},
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const { message } = App.useApp();

  const chats = useAppSelector((store) => store.chats.chats);
  const totalChats = useAppSelector((store) => store.chats.totalChats);

  const [showConfirmDelete, toggleShowConfirmDelete] = useState(false);
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);

  useEffect(() => {
    toggleShowConfirmDelete(!!deleteId?.length);
  }, [deleteId]);

  const handleCancelDelete = () => {
    setDeleteId(null);
    onCloseCb();
  };

  const handleDeleteChat = async () => {
    try {
      setIsDeleteLoading(true);
      if (deleteId) {
        const currentChat = chats.find((item) => item.chat_id === deleteId);
        if (currentChat) {
          await deleteChat(deleteId);
          if (currentChat.active) {
            const filteredChats = chats.filter(
              (item) => item.chat_id !== deleteId,
            );
            const prevChat = filteredChats.at(-1);
            if (prevChat) {
              dispatch(
                setChats(
                  chats.reduce((prev: ChatType[], item) => {
                    if (item.chat_id !== deleteId) {
                      prev.push({
                        ...item,
                        active: prevChat.chat_id === item.chat_id,
                      });
                    }
                    return prev;
                  }, []),
                ),
              );
              const currentChat = await getChat({
                id: prevChat.chat_id,
              });
              const { docs, hasNextPage } = await getMessages({
                chat_id: prevChat.chat_id,
                page: 1,
                limit: CHAT_MESSAGES_PAGE_SIZE,
              });
              dispatch(
                setActiveChat({
                  ...currentChat,
                  active: true,
                  messages: transformMessagesToObject(docs.reverse()),
                }),
              );
              dispatch(setHasMoreMessages(hasNextPage));
            } else {
              dispatch(setActiveChat(null));
              dispatch(
                setChats(chats.filter((item) => item.chat_id !== deleteId)),
              );
            }
          } else {
            dispatch(
              setChats(chats.filter((item) => item.chat_id !== deleteId)),
            );
          }
          dispatch(setTotalChats(totalChats - 1));
          message.success(
            `The chat "${currentChat.title}" has successfully deleted`,
          );
        }
      }
    } catch (e) {
      handleError(e);
    } finally {
      setIsDeleteLoading(false);
      handleCancelDelete();
    }
  };

  return (
    <Modal
      open={showConfirmDelete}
      title='Delete chat?'
      okType='danger'
      okText='Delete'
      cancelText='Cancel'
      onOk={() => handleDeleteChat()}
      onCancel={() => handleCancelDelete()}
      className={`delete-chat-modal ${className}`}
      loading={isDeleteLoading}
      destroyOnHidden
      {...props}
    >
      This will delete chat and its message&#39;s history
    </Modal>
  );
};

export default DeleteChatModal;
