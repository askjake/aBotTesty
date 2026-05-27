import styled from 'styled-components';

export const StyledErrorPageContainer = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100vh;

  & .custom-footer {
    flex: 1 0 0;
  }
`;

export const StyledErrorPageWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 72px);
  &.ant-result {
    padding: 0;
  }
`;
