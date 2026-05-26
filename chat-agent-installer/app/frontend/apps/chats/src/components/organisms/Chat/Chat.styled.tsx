import styled from 'styled-components';

export const StyledChatContainer = styled.div<{
  $hasMessages: boolean;
  $disabledByVault: boolean;
}>`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2.5rem;
  height: 100%;
  justify-content: ${({ $hasMessages = false, $disabledByVault = false }) =>
    $hasMessages && !$disabledByVault ? 'flex-end' : 'center'};
  & .ant-bubble {
    justify-content: ${({ $hasMessages = false }) =>
      $hasMessages ? 'inherit' : 'center'};
  }
`;
