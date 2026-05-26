import styled from 'styled-components';
import { Conversations } from '@ant-design/x';

export const StyledConversations = styled(Conversations)`
  &.ant-conversations {
    padding-left: 0;
    padding-right: 0;
    padding-top: 0;
  }
`;

export const StyledSidebarBody = styled.div`
  overflow-y: auto;
`;
