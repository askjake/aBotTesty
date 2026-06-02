import styled from 'styled-components';
import { Card, Typography } from 'antd';

export const StyledActiveIssues = styled(Card)`
  &.ant-card {
    & > .ant-card-body {
      overflow: hidden scroll;
      contain: strict;
      margin-top: 1rem;
      height: calc(100vh - 48px - 50px - 177px);

      & .infinite-scroll-component {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        overflow-x: hidden !important;
      }
    }
  }
`;

export const StyledActiveIssueText = styled(Typography.Paragraph)`
  &.ant-typography {
    white-space: break-spaces;
  }
`;
