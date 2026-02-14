import { FC, useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Skeleton } from 'antd';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { getChats } from '@shared/ui/services/chats.services';
import { setChats, setHasMoreChats } from '@shared/ui/store/chats/chats.slice';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { MENU_ITEMS, MenuItemWithValue } from '@shared/ui/constants/menu.constants';
import { sortChats } from '@/utils/chats.utils';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';

import {
  StyledCustomSidebar,
  StyledSidebarMenu,
  StyledSidebarWrapper,
} from '@/components/organisms/Sidebars/CustomSidebar/CustomSidebar.styled';
import CustomSidebarHeader from '@/components/molecules/Sidebars/CustomSidebarHeader';
const CustomSidebarChats = dynamic(
  () => import('@/components/molecules/Sidebars/CustomSidebarChats'),
  {
    ssr: false,
    loading: () => (
      <Skeleton
        active
        paragraph={{ rows: 12 }}
        style={{ height: 'calc(100vh - 89px - 160px)' }}
      />
    ),
  },
);
const ChatsGroupFilter = dynamic(
  () => import('@/components/molecules/ChatsGroupsFilter'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Input
        active
        block
        style={{ marginBottom: '0.5rem', height: '32px' }}
      />
    ),
  },
);

import { CustomSidebarProps } from '@/components/organisms/Sidebars/CustomSidebar/CustomSidebar.props';
import { CHATS_PAGE_SIZE } from '@shared/ui/constants/common.constants';

const CustomSidebar: FC<CustomSidebarProps> = ({
  showChats = true,
  className = '',
  ...props
}) => {
  const pathname = usePathname();
  const handleError = useHandleError();

  const dispatch = useAppDispatch();
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );
  const activeChatGroup = useAppSelector(
    (store) => store.chatsGroups.activeChatGroup,
  );
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const chats = useAppSelector((store) => store.chats.chats);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const selectedKeys = useMemo(() => {
    const item = MENU_ITEMS.find((item: MenuItemWithValue) => item.value === pathname);
    return [item?.key || ''];
  }, [pathname]);
  const prevActiveChatGroup = usePrevious(activeChatGroup);

  useEffect(() => {
    if (prevActiveChatGroup && activeChatGroup !== prevActiveChatGroup) {
      onLoadMore(true);
    }
  }, [activeChatGroup]);

  const onLoadMore = async (resetData = false) => {
    try {
      if (loading) {
        return;
      }
      setLoading(true);
      const nextPage = resetData ? 1 : currentPage + 1;
      const { docs = [], hasNextPage = false } = await getChats({
        page: nextPage,
        group_id: activeChatGroup,
        limit: CHATS_PAGE_SIZE,
      });
      const newChats = docs.map((item) => ({
        ...item,
        active: item.chat_id === activeChat?.chat_id,
      }));

      if (nextPage > 1) {
        dispatch(setChats(sortChats([...chats, ...newChats])));
      } else {
        dispatch(setChats(sortChats([...newChats])));
      }
      dispatch(setHasMoreChats(hasNextPage));
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <StyledCustomSidebar
      data-testid='custom-sidebar'
      width={320}
      className={`custom-sidebar ${className}`}
      collapsible
      collapsed={collapsedSidebar}
      trigger={null}
      collapsedWidth={0}
      {...props}
    >
      <StyledSidebarWrapper $isCollapsed={collapsedSidebar}>
        <CustomSidebarHeader showChats={showChats} />
        {showChats ? (
          <>
            <ChatsGroupFilter />
            <CustomSidebarChats onLoadMore={onLoadMore} />
          </>
        ) : null}
        <StyledSidebarMenu items={MENU_ITEMS as any} selectedKeys={selectedKeys} />
      </StyledSidebarWrapper>
    </StyledCustomSidebar>
  );
};

export default CustomSidebar;
