import { FC, useMemo } from 'react';
import { usePathname } from 'next/navigation';
import { Typography, Flex } from 'antd';
const { Text } = Typography;

import { useAppSelector } from '@shared/ui/store';

import {
  StyledAppsSidebar,
  StyledAppsSidebarMenu,
  StyledAppsSidebarWrapper,
} from '@shared/ui/components/organisms/Sidebars/AppsSidebar/AppsSidebar.styled';
import AppsSidebarHeader from '@shared/ui/components/molecules/Sidebars/AppsSidebarHeader';
import UserAvatar from '@shared/ui/components/atoms/Avatars/UserAvatar';
import UserMenu from '@shared/ui/components/molecules/Header/UserMenu';

import { AppsSidebarProps } from '@shared/ui/components/organisms/Sidebars/AppsSidebar/AppsSidebar.props';

const AppsSidebar: FC<AppsSidebarProps> = ({
  className,
  menuItems = [],
  ...props
}) => {
  const user = useAppSelector((store) => store.settings.user);
  const pathname = usePathname();
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );
  const selectedKeys = useMemo(
    () => [menuItems.find(({ value }) => value === pathname)?.key || ''],
    [pathname],
  );
  return (
    <StyledAppsSidebar
      data-testid='apps-sidebar'
      width={320}
      className={`apps-sidebar ${className}`}
      collapsible
      collapsed={collapsedSidebar}
      trigger={null}
      {...props}
    >
      <AppsSidebarHeader />
      <StyledAppsSidebarWrapper $isCollapsed={collapsedSidebar}>
        <StyledAppsSidebarMenu
          items={menuItems}
          selectedKeys={selectedKeys as string[]}
        />
        <UserMenu placement='top'>
          <Flex align='center' gap={6}>
            <UserAvatar userEmail={user?.email} size='large' />
            <Text strong ellipsis>
              {user?.email}
            </Text>
          </Flex>
        </UserMenu>
      </StyledAppsSidebarWrapper>
    </StyledAppsSidebar>
  );
};

export default AppsSidebar;
