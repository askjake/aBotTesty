import { FC } from 'react';
import { Tooltip } from 'antd';
import { MenuFoldOutlined, MenuUnfoldOutlined } from '@ant-design/icons';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';

import { toggleSideBar } from '@shared/ui/store/settings/settings.slice';

import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';
import {
  StyledAppsSidebarHeader,
  StyledAppsSidebarHeaderWrapper,
} from '@shared/ui/components/molecules/Sidebars/AppsSidebarHeader/AppsSidebarHeader.styled';

import { AppsSidebarHeaderProps } from '@shared/ui/components/molecules/Sidebars/AppsSidebarHeader/AppsSidebarHeader.props';
import ThemeSwitcher from '@shared/ui/components/molecules/Switchers/ThemeSwitcher';

const AppsSidebarHeader: FC<AppsSidebarHeaderProps> = ({
  className = '',
  ...props
}) => {
  const dispatch = useAppDispatch();
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );

  return (
    <StyledAppsSidebarHeaderWrapper
      className={`apps-sidebar-header ${className}`}
      {...props}
    >
      <StyledAppsSidebarHeader $isCollapsed={collapsedSidebar}>
        {!collapsedSidebar ? <ThemeSwitcher /> : null}

        <Tooltip title={`${collapsedSidebar ? 'Show' : 'Hide'} sidebar`}>
          <IconButton
            type='text'
            icon={
              collapsedSidebar ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />
            }
            onClick={() => dispatch(toggleSideBar())}
          />
        </Tooltip>
      </StyledAppsSidebarHeader>
    </StyledAppsSidebarHeaderWrapper>
  );
};

export default AppsSidebarHeader;
