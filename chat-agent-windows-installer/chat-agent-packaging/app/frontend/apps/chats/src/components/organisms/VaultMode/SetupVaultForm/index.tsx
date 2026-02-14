import { Button, Flex, Form, Input } from 'antd';
import { EyeInvisibleOutlined, EyeTwoTone } from '@ant-design/icons';

import { setupVaultValidator } from '@/validators/vault.validators';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch } from '@shared/ui/store';
import {
  setVaultMode,
  setVaultModeRegistered,
} from '@shared/ui/store/chats/chats.slice';
import {
  enableVaultService,
  registerVaultService,
} from '@/services/vault.services';
import { useState } from 'react';

const SetupVaultForm = () => {
  const [form] = Form.useForm();
  const handleError = useHandleError();
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const { password } = await form.validateFields();
      await registerVaultService({
        password,
      });
      await enableVaultService({
        password,
      });
      dispatch(setVaultModeRegistered(true));
      dispatch(setVaultMode(true));
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      onFinish={handleSubmit}
      scrollToFirstError
      layout='vertical'
    >
      <Form.Item
        name='password'
        label='New passphrase:'
        normalize={(value) => value?.trim()}
        rules={[
          { required: true, message: 'Please enter your new passphrase' },
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
        name='duplicatedPassword'
        label='Re-enter your passphrase:'
        normalize={(value) => value?.trim()}
        rules={[
          { required: true, message: 'Please re-enter your passphrase' },
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
              if (value !== getFieldValue('password')) {
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
            htmlType='submit'
            disabled={form.isFieldsValidating() && form.isFieldsTouched()}
            loading={loading}
          >
            Enable Vault Mode
          </Button>
        </Flex>
      </Form.Item>
    </Form>
  );
};

export default SetupVaultForm;
