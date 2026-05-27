import styled from 'styled-components';

export const StyledCustomSidebarHeader = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-bottom: 1px solid ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  padding: 0.5rem 0;
  position: sticky;
`;

export const StyledCustomSidebarHeaderWrapper = styled.div`
  position: sticky;
`;

export const StyledCustomSidebarButtonsList = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
`;
