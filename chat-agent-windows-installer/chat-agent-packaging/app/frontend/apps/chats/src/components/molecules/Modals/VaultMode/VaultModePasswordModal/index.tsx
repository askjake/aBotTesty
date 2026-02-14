import {
  setShowEnableVaultModal,
  setVaultMode,
} from '@shared/ui/store/chats/chats.slice';
import { App, Form, Input, Modal } from 'antd';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { enableVaultService } from '@/services/vault.services';
import { setupVaultValidator } from '@/validators/vault.validators';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import useRefetchChats from '@/hooks/useRefetchChats';
import { useState } from 'react';

const VaultModePasswordModal = () => {
  const dispatch = useAppDispatch();
  const showEnableVaultModal = useAppSelector(
    (store) => store.chats.showEnableVaultModal,
  );
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const vaultModeEnabled = useAppSelector((store) => store.chats.vaultMode);
  const [form] = Form.useForm();
  const handleError = useHandleError();
  const { message } = App.useApp();
  const { refetchChats } = useRefetchChats();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      if (!vaultModeRegistered || vaultModeEnabled) {
        dispatch(setShowEnableVaultModal(false));
        setLoading(false);
        return;
      }
      const { password } = await form.validateFields();
      await enableVaultService({
        password,
      });
      dispatch(setVaultMode(true));
      await refetchChats();
      message.success(`The Vault Mode has successfully enabled`);
      dispatch(setShowEnableVaultModal(false));
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      open={showEnableVaultModal}
      centered
      title='Vault Mode required'
      okText='Enable Vault Mode'
      onCancel={() => dispatch(setShowEnableVaultModal(false))}
      okButtonProps={{ autoFocus: true, htmlType: 'submit' }}
      destroyOnHidden
      modalRender={(dom) => (
        <Form
          layout='vertical'
          form={form}
          clearOnDestroy
          onFinish={handleSubmit}
          scrollToFirstError
        >
          {dom}
        </Form>
      )}
      loading={loading}
    >
      <Form.Item
        name='password'
        label='Password:'
        normalize={(value) => value?.trim()}
        rules={[
          { required: true, message: 'Please enter your password' },
          {
            transform: (value) => value.trim(),
          },
          {
            validator: (_, value) => {
              const validatePassword = setupVaultValidator.safeParse({
                password: value,
              });
              if (!validatePassword.success) {
                const formatedError = validatePassword.error.format();
                return Promise.reject(
                  formatedError.password?._errors?.map(
                    (item) => new Error(item),
                  ),
                );
              }
              return Promise.resolve();
            },
          },
        ]}
      >
        <Input.Password
          iconRender={(visible) =>
            visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
          }
        />
      </Form.Item>
    </Modal>
  );
};

export default VaultModePasswordModal;
