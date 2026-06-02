import { Input, Layout, Typography } from 'antd';
import styled from 'styled-components';

const { Header } = Layout;
const { Title } = Typography;

export const StyledCustomHeader = styled(Header)`
  &.ant-layout-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
    padding-top: 0.8rem;
    padding-left: 1rem;
    position: sticky;
    top: 0;
    z-index: 1;
    & .user-avatar {
      cursor: pointer;
    }
  }
`;

export const StyledCustomHeaderTitle = styled(Title)`
  &.ant-typography {
    margin-bottom: 0 !important;
    font-size: 2rem !important;
    text-overflow: ellipsis;
    text-wrap: nowrap;
    max-width: 35vw;
    overflow: hidden;
  }
`;

export const StyledEditTitleInput = styled(Input)`
  &.ant-input {
    background: none !important;
    border: none;
    font-size: 2rem !important;
    font-weight: bold;
    outline: none;
    padding: 0;
    box-shadow: none !important;
    width: 35vw;
  }
`;

export const StyledCustomHeaderTitleWrapper = styled.div`
  @media (max-width: 465px) {
    display: none;
  }
`;
