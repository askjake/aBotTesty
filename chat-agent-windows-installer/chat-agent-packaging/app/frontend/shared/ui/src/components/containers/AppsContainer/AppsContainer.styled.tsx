import styled from 'styled-components';
import { Layout } from 'antd';

const { Content } = Layout;

export const StyledAppsContainer = styled(Layout)`
  &.ant-layout {
    background: ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  }
`;

export const StyledAppsContainerContent = styled(Content)`
  &.ant-layout-content {
    background: ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  }
`;
