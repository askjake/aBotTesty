import styled from 'styled-components';

export const StyledChatSenderWrapper = styled.div<{
  $collapsedSidebar: boolean;
}>`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: ${({ $collapsedSidebar = false }) =>
    $collapsedSidebar ? '95vw' : '75vw'};
  width: 100%;
`;
