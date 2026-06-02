import { FC, useEffect, useState } from 'react';
import { App, Modal } from 'antd';

import {
  setActiveChatGroup,
  setChatsGroups,
} from '@shared/ui/store/chatsGroups/chatsGroups.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { deleteChatGroup } from '@/services/chatGroup.service';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

import { DeleteGroupModalProps } from '@/components/molecules/Modals/Chat/DeleteGroupModal/DeleteGroupModal.props';

const DeleteGroupModal: FC<DeleteGroupModalProps> = ({
  className = '',
  deleteId,
  setDeleteId,
  ...props
}) => {
  const dispatch = useAppDispatch();
  const { message } = App.useApp();
  const handleError = useHandleError();

  const chatsGroups = useAppSelector((store) => store.chatsGroups.chatsGroups);

  const [isLoadingDelete, setIsLoadingDelete] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    setShowDelete(!!deleteId);
  }, [deleteId]);

  const handleCancelDelete = () => {
    setDeleteId(null);
    setIsLoadingDelete(false);
  };

  const handleDeleteChatGroup = async () => {
    try {
      if (!deleteId) return;
      setIsLoadingDelete(true);
      await deleteChatGroup(deleteId);
      dispatch(
        setChatsGroups(
          chatsGroups.filter((item) => item.group_id !== deleteId),
        ),
      );
      dispatch(setActiveChatGroup('all'));
      message.success(`The group has successfully deleted`);
    } catch (e) {
      handleError(e);
    } finally {
      handleCancelDelete();
    }
  };
  return (
    <Modal
      open={showDelete}
      title='Delete group?'
      okType='danger'
      okText='Delete'
      cancelText='Cancel'
      onOk={() => handleDeleteChatGroup()}
      onCancel={() => handleCancelDelete()}
      loading={isLoadingDelete}
      centered
      destroyOnHidden
      className={`delete-group-modal ${className}`}
      {...props}
    >
      This will delete the group, but the chats will remain
    </Modal>
  );
};

export default DeleteGroupModal;
