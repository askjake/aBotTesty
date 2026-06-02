import styled from 'styled-components';

export const StyledContactBlock = styled.a`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: ${({ theme }) => theme?.colors?.text || '#0d0d0d'};
`;
