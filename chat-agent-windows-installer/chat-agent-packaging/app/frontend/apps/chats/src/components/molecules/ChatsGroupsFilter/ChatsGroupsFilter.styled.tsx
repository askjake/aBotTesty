import styled from 'styled-components';
import { Select } from 'antd';

export const StyledChatsGroupsFilterContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
`;

export const StyledChatsGroupsFilterSelect = styled(Select)`
  &.ant-select {
    width: 100%;
  }
`;
