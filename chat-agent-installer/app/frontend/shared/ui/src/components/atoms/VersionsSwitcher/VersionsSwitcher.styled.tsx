import styled from 'styled-components';

export const StyledVersionsSwitcherContainer = styled.div<{
  $disableLeftBtn: boolean;
  $disableRightBtn: boolean;
}>`
  width: max-content;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  color: ${({ theme }) => theme?.colors?.text || '#0d0d0d'};
  & .anticon-left {
    filter: ${({ $disableLeftBtn = false }) =>
      $disableLeftBtn ? 'brightness(15)' : 'none'};
    cursor: ${({ $disableLeftBtn = false }) =>
      $disableLeftBtn ? 'not-allowed' : 'pointer'};
  }

  & .anticon-right {
    filter: ${({ $disableRightBtn = false }) =>
      $disableRightBtn ? 'brightness(15)' : 'none'};
    cursor: ${({ $disableRightBtn = false }) =>
      $disableRightBtn ? 'not-allowed' : 'pointer'};
  }
`;
