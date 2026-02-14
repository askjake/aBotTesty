import { Layout, Menu } from 'antd';
import styled from 'styled-components';

export const StyledCustomSidebar = styled(Layout.Sider)`
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

export const StyledSidebarWrapper = styled.div<{ $isCollapsed: boolean }>`
  display: ${({ $isCollapsed }) => ($isCollapsed ? 'none' : 'block')};
  transition: all 500ms ease-in-out;
`;

export const StyledSidebarMenu = styled(Menu)`
  &.ant-menu {
    background: ${({ theme }) => theme?.colors?.grey || '#f9f9f9'};
    border: none;
    border-inline-end: none !important;
  }
`;
