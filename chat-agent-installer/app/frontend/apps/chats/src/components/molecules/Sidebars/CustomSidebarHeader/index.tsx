import { FC } from 'react';
import { Skeleton, Tooltip } from 'antd';
import dynamic from 'next/dynamic';
import { MenuFoldOutlined } from '@ant-design/icons';

import { toggleSideBar } from '@shared/ui/store/settings/settings.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';

const CreateChatButton = dynamic(
  () => import('@/components/molecules/Buttons/CreateChatButton'),
  {
    loading: () => <Skeleton.Button active shape='circle' />,
    ssr: false,
  },
);
const VaultModeButton = dynamic(
  () => import('@/components/molecules/Buttons/VaultModeButton'),
  {
    loading: () => <Skeleton.Button active shape='circle' />,
    ssr: false,
  },
);
const SearchChatsButton = dynamic(
  () => import('@/components/molecules/Buttons/SearchChatsButton'),
  {
    loading: () => <Skeleton.Button active shape='circle' />,
    ssr: false,
  },
);
import {
  StyledCustomSidebarButtonsList,
  StyledCustomSidebarHeader,
  StyledCustomSidebarHeaderWrapper,
} from '@/components/molecules/Sidebars/CustomSidebarHeader/CustomSidebarHeader.styled';
import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';

import { CustomSidebarHeaderProps } from '@/components/molecules/Sidebars/CustomSidebarHeader/CustomSidebarHeader.props';

const CustomSidebarHeader: FC<CustomSidebarHeaderProps> = ({
  showChats = false,
  className = '',
  ...props
}) => {
  const dispatch = useAppDispatch();
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);

  return (
    <StyledCustomSidebarHeaderWrapper
      className={`custom-sidebar-header ${className}`}
      {...props}
    >
      <StyledCustomSidebarHeader>
        <Tooltip title='Hide sidebar'>
          <IconButton
            type='text'
            icon={<MenuFoldOutlined />}
            onClick={() => dispatch(toggleSideBar())}
          />
        </Tooltip>
        <StyledCustomSidebarButtonsList>
          {showChats ? (
            <>
              <SearchChatsButton disabled={aiTyping} />
              <VaultModeButton disabled={aiTyping} />
              <CreateChatButton disabled={aiTyping} />
            </>
          ) : null}
        </StyledCustomSidebarButtonsList>
      </StyledCustomSidebarHeader>
    </StyledCustomSidebarHeaderWrapper>
  );
};

export default CustomSidebarHeader;
