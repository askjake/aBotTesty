import styled from 'styled-components';
import { Card, Input } from 'antd';

export const StyledAppsContainer = styled(Card)`
  &.ant-card {
    margin: 2rem;
  }
`;

export const StyledAppsWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
`;

export const StyledAppsInput = styled(Input)`
  &.ant-input-group-wrapper {
    margin-bottom: 2.5rem;
  }
`;
