import { Button, Form, Input, Typography } from 'antd';
import axios from 'axios';
const { Title } = Typography;
import { useState } from 'react';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { BETA_REPORTS_URL } from '@shared/ui/constants/env.constants';

import { StyledReportsAccessBlock } from '@/components/organisms/ReportsAccessBlock/ReportsAccessBlock.styled';

const ReportsAccessBlock = () => {
  const handleError = useHandleError();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const checkPassword = async () => {
    try {
      setLoading(true);
      const { password } = await form.validateFields();
      await axios.post(`${BETA_REPORTS_URL}/api/access`, {
        password,
      });
      window.location.reload();
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };
  return (
    <StyledReportsAccessBlock>
      <Title>Access denied</Title>
      <Form
        form={form}
        autoComplete='off'
        layout='inline'
        onFinish={checkPassword}
      >
        <Form.Item
          label='Password'
          name='password'
          rules={[{ required: true, message: 'Please, input password' }]}
        >
          <Input.Password />
        </Form.Item>
        <Form.Item label={null}>
          <Button type='primary' htmlType='submit' loading={loading}>
            Submit
          </Button>
        </Form.Item>
      </Form>
    </StyledReportsAccessBlock>
  );
};

export default ReportsAccessBlock;
