import styled from 'styled-components';
import { Empty } from 'antd';

export const StyledEmptyChats = styled(Empty)`
  &.ant-empty {
    height: calc(100vh - 89px - 160px);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-content: center;
    & .ant-empty-image {
      height: auto;
    }
    & .anticon {
      font-size: 2.5rem;
    }
  }
`;
