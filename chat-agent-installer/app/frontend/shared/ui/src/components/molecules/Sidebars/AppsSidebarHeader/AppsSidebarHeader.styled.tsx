import styled from 'styled-components';

export const StyledAppsSidebarHeader = styled.header<{ $isCollapsed: boolean }>`
  display: flex;
  align-items: center;
  justify-content: ${({ $isCollapsed }) =>
    $isCollapsed ? 'center' : 'space-between'};
  gap: 1rem;
  border-bottom: 1px solid ${({ theme }) => theme?.colors?.light || '#f3f4f6'};
  padding: 0.5rem 0;
  position: sticky;
`;

export const StyledAppsSidebarHeaderWrapper = styled.div`
  position: sticky;
`;

export const StyledAppsSidebarButtonsList = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
`;
