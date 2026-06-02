import { App, Button, Flex, Form, Input } from 'antd';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';
import dynamic from 'next/dynamic';

import { useState } from 'react';
import { setupVaultValidator } from '@/validators/vault.validators';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import {
  enableVaultService,
  updatePasswordVaultService,
} from '@/services/vault.services';
import { useAppDispatch } from '@shared/ui/store';
import { setVaultMode } from '@shared/ui/store/chats/chats.slice';
import useRefetchChats from '@/hooks/useRefetchChats';

const VaultModeResetPasswordModal = dynamic(
  () =>
    import('@/components/molecules/Modals/VaultMode/VaultModeResetPasswordModal'),
  {
    ssr: false,
  },
);

const UpdateVaultForm = () => {
  const [form] = Form.useForm();
  const handleError = useHandleError();
  const dispatch = useAppDispatch();
  const { refetchChats } = useRefetchChats();
  const { message } = App.useApp();
  const [showWarnModal, setShowWarnModal] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const { newPassword, oldPassword } = await form.validateFields();
      await updatePasswordVaultService({
        newPassword,
        oldPassword,
      });
      await enableVaultService({
        password: newPassword,
      });
      dispatch(setVaultMode(true));
      await refetchChats();
      message.success(
        `The password has updated and the Vault Mode has successfully enabled`,
      );
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Form
        form={form}
        onFinish={handleSubmit}
        scrollToFirstError
        layout='vertical'
      >
        <Form.Item
          name='oldPassword'
          label='Old password:'
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
        <Form.Item
          name='newPassword'
          label='New password:'
          normalize={(value) => value?.trim()}
          rules={[
            { required: true, message: 'Please enter your password' },
            {
              transform: (value) => value.trim(),
            },
            ({ getFieldValue }) => ({
              validator(_, value) {
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
                if (value === getFieldValue('oldPassword')) {
                  return Promise.reject(
                    new Error(`Passwords must not be equal`),
                  );
                }
                return Promise.resolve();
              },
            }),
          ]}
        >
          <Input.Password
            iconRender={(visible) =>
              visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
            }
          />
        </Form.Item>
        <Form.Item
          name='duplicatedPassword'
          label='Re-enter your new passphrase:'
          normalize={(value) => value?.trim()}
          rules={[
            { required: true, message: 'Please enter your password' },
            {
              transform: (value) => value.trim(),
            },
            ({ getFieldValue }) => ({
              validator(_, value) {
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
                if (value !== getFieldValue('newPassword')) {
                  return Promise.reject(new Error(`Passwords must be equal`));
                }
                return Promise.resolve();
              },
            }),
          ]}
        >
          <Input.Password
            iconRender={(visible) =>
              visible ? <EyeTwoTone /> : <EyeInvisibleOutlined />
            }
          />
        </Form.Item>
        <Form.Item>
          <Flex align='center' justify='center' gap={6}>
            <Button
              type='primary'
              color='danger'
              onClick={() => setShowWarnModal(true)}
              loading={loading}
            >
              Reset password
            </Button>
            <Button
              variant='outlined'
              htmlType='submit'
              disabled={form.isFieldsValidating() && form.isFieldsTouched()}
              loading={loading}
            >
              Update password
            </Button>
          </Flex>
        </Form.Item>
      </Form>
      <VaultModeResetPasswordModal
        open={showWarnModal}
        title='Reset password'
        okText='Accept'
        onCloseCb={() => setShowWarnModal(false)}
      />
    </>
  );
};

export default UpdateVaultForm;
