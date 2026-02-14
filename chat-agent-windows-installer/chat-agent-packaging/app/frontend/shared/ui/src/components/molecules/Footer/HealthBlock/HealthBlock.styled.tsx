import styled from 'styled-components';

export const StyledHealthBlock = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

export const StyledHealthBlockIcon = styled.div<{
  $hasError: boolean;
}>`
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 100%;
  background-color: ${({ $hasError = false, theme }) =>
    $hasError ? theme?.colors?.primary || '#fc1c39' : theme?.colors?.green || '#34d399'};
`;
