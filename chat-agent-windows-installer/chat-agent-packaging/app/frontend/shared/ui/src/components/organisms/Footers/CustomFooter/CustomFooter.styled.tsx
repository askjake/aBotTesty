import { Layout } from 'antd';
import styled from 'styled-components';

const { Footer } = Layout;

export const StyledCustomFooter = styled(Footer)`
  &.ant-layout-footer {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: transparent;
    background: ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  }
`;
