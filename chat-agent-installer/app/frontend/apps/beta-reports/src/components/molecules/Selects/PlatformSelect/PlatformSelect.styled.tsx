import { Select } from 'antd';
import styled from 'styled-components';

export const StyledPlatformSelect = styled(Select)`
  &.ant-select {
    min-width: 150px;
  }
` as typeof Select;
