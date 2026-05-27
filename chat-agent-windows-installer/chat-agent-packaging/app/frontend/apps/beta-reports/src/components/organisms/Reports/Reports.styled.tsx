import styled from 'styled-components';
import { Table, Typography } from 'antd';

export const StyledReportsTable = styled(Table)`
  & .ant-table-body {
    overflow: auto !important;
    height: calc(100vh - 48px - 50px - 330px);
  }
` as typeof Table;

export const StyledReportsText = styled(Typography.Paragraph)`
  &.ant-typography {
    white-space: break-spaces;
  }
`;
