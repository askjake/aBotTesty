import { FC, LegacyRef, useMemo, useRef, useState } from 'react';
import { App, Button, Flex, InputRef, Skeleton, Tag, Tooltip } from 'antd';
import { MenuUnfoldOutlined } from '@ant-design/icons';
import dynamic from 'next/dynamic';
import { GrEdit } from 'react-icons/gr';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { updateChat } from '@shared/ui/services/chats.services';
import { setActiveChat, setChats } from '@shared/ui/store/chats/chats.slice';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import useClickOutside from '@shared/ui/hooks/useClickOutside.hook';
import { toggleSideBar } from '@shared/ui/store/settings/settings.slice';

import UserAvatar from '@shared/ui/components/atoms/Avatars/UserAvatar';
import {
  StyledCustomHeader,
  StyledCustomHeaderTitle,
  StyledCustomHeaderTitleWrapper,
  StyledEditTitleInput,
} from '@/components/organisms/Headers/CustomHeader/CustomHeader.styled';
import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';
const CreateChatButton = dynamic(
  () => import('@/components/molecules/Buttons/CreateChatButton'),
  {
    loading: () => (
      <Skeleton.Button
        active
        block
        shape='circle'
        style={{ marginTop: '1rem' }}
      />
    ),
    ssr: false,
  },
);
const UserMenu = dynamic(
  () => import('@shared/ui/components/molecules/Header/UserMenu'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Avatar
        active
        shape='circle'
        style={{ width: '40px', height: '40px', marginTop: '0.8rem' }}
      />
    ),
  },
);

import ThemeSwitcher from '@shared/ui/components/molecules/Switchers/ThemeSwitcher';

import { CustomHeaderProps } from '@/components/organisms/Headers/CustomHeader/CustomHeader.props';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';

const CustomHeader: FC<CustomHeaderProps> = ({
  className = '',
  showChats = false,
  ...props
}) => {
  const { message } = App.useApp();
  const handleError = useHandleError();
  const dispatch = useAppDispatch();
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const chats = useAppSelector((store) => store.chats.chats);
  const user = useAppSelector((store) => store.settings.user);
  const titleRef = useRef<InputRef>(null);
  const [openEditTitle, toggleOpenEditTitle] = useState(false);
  const [loading, setLoading] = useState(false);
  const isReadyOnlyChat = useMemo(
    () => activeChat?.status === ChatStatusEnum.READONLY,
    [activeChat],
  );

  useClickOutside(titleRef, () => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    const newTitle = titleRef?.current?.nativeElement?.value;
    if (newTitle?.length && activeChat) {
      onUpdateTitle({
        chat_id: activeChat.chat_id,
        title: newTitle,
      });
    }
  });

  const onUpdateTitle = async ({
    chat_id,
    title,
  }: {
    chat_id: string;
    title: string;
  }) => {
    try {
      setLoading(true);
      if (chat_id && title) {
        const getChat = chats.find((item) => item.chat_id === chat_id);
        if (getChat) {
          if (getChat?.title === title) return;
          await updateChat({
            id: chat_id,
            favorite: getChat.favorite,
            active: getChat.active,
            title,
            group_id: getChat.group_id,
          });
          dispatch(
            setChats(
              chats.map((data) => ({
                ...data,
                title: data.chat_id === chat_id ? title : data.title,
              })),
            ),
          );
          if (activeChat) {
            dispatch(
              setActiveChat({
                ...activeChat,
                title,
              }),
            );
          }
          message.success(`The chat's title has successfully updated`);
        }
      }
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
      toggleOpenEditTitle(false);
    }
  };

  return (
    <StyledCustomHeader
      data-testid='custom-header'
      className={`custom-header ${className}`}
      {...props}
    >
      <Flex align='center' gap={5}>
        {collapsedSidebar ? (
          <>
            <Tooltip title='Show sidebar'>
              <IconButton
                type='text'
                icon={<MenuUnfoldOutlined />}
                onClick={() => dispatch(toggleSideBar())}
              />
            </Tooltip>
            {showChats ? <CreateChatButton disabled={aiTyping} /> : null}
          </>
        ) : null}
        <StyledCustomHeaderTitleWrapper>
          {activeChat?.title?.length ? (
            openEditTitle ? (
              <StyledEditTitleInput
                defaultValue={activeChat.title}
                ref={titleRef as LegacyRef<InputRef>}
                maxLength={50}
                disabled={isReadyOnlyChat || loading}
              />
            ) : (
              <Flex align='center' gap={5}>
                <StyledCustomHeaderTitle>
                  {activeChat?.title}
                </StyledCustomHeaderTitle>
                {isReadyOnlyChat ? (
                  <Tag color='error'>Read-only</Tag>
                ) : (
                  <Tooltip title='Edit chat title'>
                    <Button
                      shape='circle'
                      color='default'
                      variant='text'
                      icon={<GrEdit />}
                      onClick={() => toggleOpenEditTitle(true)}
                      disabled={aiTyping}
                    />
                  </Tooltip>
                )}
              </Flex>
            )
          ) : (
            <div />
          )}
        </StyledCustomHeaderTitleWrapper>
      </Flex>
      <Flex justify='flex-end' align='center' gap={15}>
        <ThemeSwitcher />
        <UserMenu>
          <UserAvatar userEmail={user?.email} size='large' />
        </UserMenu>
      </Flex>
    </StyledCustomHeader>
  );
};

export default CustomHeader;
