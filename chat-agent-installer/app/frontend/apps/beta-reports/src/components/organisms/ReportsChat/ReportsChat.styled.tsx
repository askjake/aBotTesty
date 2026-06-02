import styled from 'styled-components';

export const StyledReportsChatContainer = styled.div<{
  $hasMessages: boolean;
}>`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
  height: calc(100vh - 48px - 50px - 153px);
  justify-content: ${({ $hasMessages = false }) =>
    $hasMessages ? 'flex-end' : 'center'};
  & .ant-bubble {
    justify-content: ${({ $hasMessages = false }) =>
      $hasMessages ? 'inherit' : 'center'};
  }
`;
