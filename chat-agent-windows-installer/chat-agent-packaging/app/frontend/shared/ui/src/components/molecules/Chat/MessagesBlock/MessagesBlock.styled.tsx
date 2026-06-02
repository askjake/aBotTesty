import styled from 'styled-components';
import { Bubble } from '@ant-design/x';
import { Image } from 'antd';

export const StyledMessagesBlock = styled.div<{
  $collapsedSidebar: boolean;
  $customHeight: string;
}>`
  width: 100%;
  max-width: ${({ $collapsedSidebar = false }) =>
    $collapsedSidebar ? '95vw' : '75vw'};
  overflow: auto;
  display: flex;
  flex-direction: column-reverse;
  height: ${({ $customHeight = 'calc(100vh - 64px - 96px - 72px - 3.2rem)' }) =>
    $customHeight};
`;

export const StyledMessagesList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 15px;
`;
