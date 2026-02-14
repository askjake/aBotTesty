import { FC, useEffect, useMemo, useState } from 'react';
import { App, Form, Modal, Select } from 'antd';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { updateChat } from '@shared/ui/services/chats.services';
import { setActiveChat, setChats } from '@shared/ui/store/chats/chats.slice';
import { setActiveChatGroup } from '@shared/ui/store/chatsGroups/chatsGroups.slice';

import { AddChatToGroupModalProps } from '@/components/molecules/Modals/Chat/AddChatToGroupModal/AddChatToGroupModal.props';

const AddChatToGroupModal: FC<AddChatToGroupModalProps> = ({
  className = '',
  chat,
  setChat,
  onCloseCb = () => {},
  ...props
}) => {
  const dispatch = useAppDispatch();
  const [form] = Form.useForm();
  const handleError = useHandleError();
  const { message } = App.useApp();

  const chatsGroups = useAppSelector((store) => store.chatsGroups.chatsGroups);
  const activeChatGroup = useAppSelector(
    (store) => store.chatsGroups.activeChatGroup,
  );
  const chats = useAppSelector((store) => store.chats.chats);
  const activeChat = useAppSelector((store) => store.chats.activeChat);

  const [showMigrationModal, setShowMigrationModal] = useState(false);
  const [isMigrationLoading, setIsMigrationLoading] = useState(false);

  const chatsGroupsOptions = useMemo(
    () => [
      {
        value: null,
        label: 'Chats without group',
      },
      ...chatsGroups.map(({ group_id, title }) => ({
        label: title,
        value: group_id,
      })),
    ],
    [chatsGroups],
  );

  useEffect(() => {
    const isShowModal = !!chat;
    setShowMigrationModal(isShowModal);
    if (isShowModal) {
      form.setFieldValue('group_id', chat?.group_id);
    }
  }, [chat, form]);

  const handleCancelMigration = () => {
    setChat(null);
    setShowMigrationModal(false);
    onCloseCb();
  };

  const handleEditMigration = async () => {
    try {
      setIsMigrationLoading(true);
      const { group_id } = await form.validateFields();
      const getActiveChat = chats.find(
        (item) => item.chat_id === chat?.chat_id,
      );
      if (getActiveChat) {
        await updateChat({
          id: getActiveChat.chat_id,
          favorite: getActiveChat.favorite,
          active: getActiveChat.active,
          title: getActiveChat.title,
          group_id,
        });
        dispatch(
          setChats(
            chats
              .map(({ ...data }) => ({
                ...data,
                group_id:
                  data.chat_id === chat?.chat_id ? group_id : data.group_id,
              }))
              .filter((item) =>
                activeChatGroup === 'all'
                  ? true
                  : item.group_id === activeChatGroup,
              ),
          ),
        );
        if (getActiveChat.active && activeChat) {
          dispatch(setActiveChatGroup(group_id));
          dispatch(
            setActiveChat({
              ...activeChat,
              group_id,
            }),
          );
        }
        message.success(`The chat has successfully moved to the group`);
      }
      handleCancelMigration();
    } catch (e) {
      handleError(e);
    } finally {
      onCloseCb();
      setIsMigrationLoading(false);
    }
  };

  return (
    <Modal
      open={showMigrationModal}
      title='Move chat to the group'
      okText='Save changes'
      onCancel={() => handleCancelMigration()}
      okButtonProps={{ autoFocus: true, htmlType: 'submit' }}
      modalRender={(dom) => (
        <Form
          layout='vertical'
          form={form}
          onFinish={handleEditMigration}
          scrollToFirstError
        >
          {dom}
        </Form>
      )}
      loading={isMigrationLoading}
      destroyOnHidden
      className={`add-chat-to-group-modal ${className}`}
      centered
      {...props}
    >
      <Form.Item
        name='group_id'
        label='Select group'
        normalize={(value) => value?.trim()}
      >
        <Select
          showSearch={{
            optionFilterProp: 'label',
          }}
          options={chatsGroupsOptions}
        />
      </Form.Item>
    </Modal>
  );
};

export default AddChatToGroupModal;
