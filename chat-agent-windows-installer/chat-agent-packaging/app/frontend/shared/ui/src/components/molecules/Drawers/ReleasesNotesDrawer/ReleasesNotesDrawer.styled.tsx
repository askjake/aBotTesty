import styled from 'styled-components';
import { Button, Drawer, Empty } from 'antd';

export const StyledReleasesDrawer = styled(Drawer)`
  &.ant-drawer-body {
    overflow: hidden;
  }
`;

export const StyledReleasesNotesContainer = styled.div`
  overflow: hidden scroll;
  contain: strict;
  margin-top: 1rem;
  height: calc(100vh - 69px - 32px - 55px);

  & .infinite-scroll-component {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    overflow-x: hidden !important;
  }
`;

export const StyledReleaseDrawerList = styled.ul`
  padding-left: 1rem;
  li:not(:last-of-type) {
    margin-bottom: 0.5rem;
  }
`;

export const StyledReleaseDrawerFeedbackButton = styled(Button)`
  &.ant-btn {
    color: ${({ theme }) => theme?.colors?.text || '#0d0d0d'};
  }
`;

export const StyledReleaseDrawerEmpty = styled(Empty)`
  &.ant-empty {
    height: calc(100vh - 69px - 32px - 50px);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    & .ant-empty-image {
      height: auto;
    }
    & .anticon {
      font-size: 2.5rem;
    }
  }
`;
