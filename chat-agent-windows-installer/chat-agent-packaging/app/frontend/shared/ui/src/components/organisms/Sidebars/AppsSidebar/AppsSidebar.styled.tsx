import styled from 'styled-components';
import { Layout, Menu } from 'antd';

export const StyledAppsSidebar = styled(Layout.Sider)`
  &.ant-layout-sider {
    overflow: hidden;
    background: ${({ theme }) => theme?.colors?.grey || '#f9f9f9'};
    position: sticky;
    height: 100vh;
    inset-inline-start: 0;
    top: 0;
    bottom: 0;
    &:not(.ant-layout-sider-collapsed) {
      padding: 1rem 0.5rem !important;
    }

    & .ant-conversations {
      padding-left: 0;
      padding-right: 0;
    }

    @media (max-width: ${({ theme }) => theme?.screens?.md}) {
      position: fixed;
      z-index: 2;
    }
  }
`;

export const StyledAppsSidebarWrapper = styled.div<{ $isCollapsed: boolean }>`
  display: ${({ $isCollapsed }) => ($isCollapsed ? 'none' : 'flex')};
  transition: all 500ms ease-in-out;
  flex-direction: column;
  height: calc(100vh - 85px);
  justify-content: space-between;

  & .user-menu {
    margin-top: auto;
    cursor: pointer;
  }
`;

export const StyledAppsSidebarMenu = styled(Menu)`
  &.ant-menu {
    background: ${({ theme }) => theme?.colors?.grey || '#f9f9f9'};
    border: none;
    border-inline-end: none !important;
  }
`;
