import styled from 'styled-components';
import { Layout } from 'antd';

export const StyledHomeLayout = styled(Layout)`
  &.ant-layout {
    margin: 0 auto;
    height: 100%;
    overflow: hidden;
    background: ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  }
`;
