import styled from 'styled-components';
import { Card } from 'antd';

export const StyledReportsAccessBlock = styled(Card)`
  &.ant-card {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 1rem;
    justify-content: center;
    align-items: center;
    min-height: calc(100vh - 2rem);
    & h1 {
      text-align: center;
    }
  }
`;
