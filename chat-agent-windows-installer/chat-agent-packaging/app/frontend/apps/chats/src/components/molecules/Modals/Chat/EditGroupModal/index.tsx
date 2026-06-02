import { FC, useEffect, useState } from 'react';
import { EditGroupModalProps } from '@/components/molecules/Modals/Chat/EditGroupModal/EditGroupModal.props';
import { App, Form, Input, Modal } from 'antd';
import { updateOrCreateChatGroupValidator } from '@/validators/chatsGroups.validators';
import { updateChatGroup } from '@/services/chatGroup.service';
import { setChatsGroups } from '@shared/ui/store/chatsGroups/chatsGroups.slice';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';

const EditGroupModal: FC<EditGroupModalProps> = ({
  className = '',
  group,
  setGroup,
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const [form] = Form.useForm();
  const { message } = App.useApp();

  const chatsGroups = useAppSelector((store) => store.chatsGroups.chatsGroups);

  const [isLoadingUpdate, setIsLoadingUpdate] = useState(false);
  const [showEdit, setShowEdit] = useState(false);

  useEffect(() => {
    const isShowModal = !!group;
    setShowEdit(isShowModal);
    if (isShowModal) {
      form.setFieldValue('title', group?.title);
    }
  }, [form, group]);

  const handleCancelEdit = () => {
    setGroup(null);
    setShowEdit(false);
  };

  const handleEditGroup = async () => {
    try {
      if (!group) return;
      setIsLoadingUpdate(true);
      const { title } = await form.validateFields();
      await updateChatGroup({
        title,
        id: group?.group_id as string,
      });
      dispatch(
        setChatsGroups(
          chatsGroups.map((item) => ({
            ...item,
            title: item.group_id === group?.group_id ? title : item.title,
          })),
        ),
      );
      message.success(`The group  has successfully updated`);
      handleCancelEdit();
    } catch (e) {
      handleError(e);
    } finally {
      setIsLoadingUpdate(false);
    }
  };
  return (
    <Modal
      centered
      open={showEdit}
      title='Edit the group title'
      okText='Save changes'
      onCancel={() => handleCancelEdit()}
      okButtonProps={{ autoFocus: true, htmlType: 'submit' }}
      modalRender={(dom) => (
        <Form
          layout='vertical'
          form={form}
          onFinish={handleEditGroup}
          scrollToFirstError
        >
          {dom}
        </Form>
      )}
      loading={isLoadingUpdate}
      destroyOnHidden
      className={`edit-group-modal ${className}`}
      {...props}
    >
      <Form.Item
        name='title'
        label='Title'
        normalize={(value) => value?.trim()}
        rules={[
          { required: true, message: 'Please enter the title' },
          {
            transform: (value) => value.trim(),
          },
          {
            validator: (_, value) => {
              const validateTitle = updateOrCreateChatGroupValidator.safeParse({
                title: value,
              });
              if (!validateTitle.success) {
                const formatedError = validateTitle.error.format();
                return Promise.reject(
                  formatedError.title?._errors?.map((item) => new Error(item)),
                );
              }
              return Promise.resolve();
            },
          },
        ]}
      >
        <Input />
      </Form.Item>
    </Modal>
  );
};

export default EditGroupModal;
