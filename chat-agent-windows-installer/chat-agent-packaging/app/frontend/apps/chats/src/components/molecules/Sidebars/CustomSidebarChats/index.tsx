import { FC, LegacyRef, useEffect, useRef, useState } from 'react';
import InfiniteScroll from 'react-infinite-scroll-component';
import { App, GetProp, Input, InputRef, Spin } from 'antd';
import {
  DeleteOutlined,
  DoubleRightOutlined,
  EditOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import { type ConversationsProps } from '@ant-design/x';
import dynamic from 'next/dynamic';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import useClickOutside from '@shared/ui/hooks/useClickOutside.hook';
import { getChat, updateChat } from '@shared/ui/services/chats.services';
import {
  setActiveChat,
  setChats,
  setHasMoreMessages,
} from '@shared/ui/store/chats/chats.slice';
import { defineGroup, sortChats } from '@/utils/chats.utils';
import {
  groupable,
  transformMessagesToObject,
} from '@shared/ui/utils/messages.utils';
import { getMessages } from '@shared/ui/services/messages.services';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';

import {
  StyledConversations,
  StyledSidebarBody,
} from './CustomSidebarChats.styled';
const VaultModeWarningModal = dynamic(
  () => import('@/components/molecules/Modals/VaultMode/VaultModeWarningModal'),
  { ssr: false },
);
const DeleteChatModal = dynamic(
  () => import('@/components/molecules/Modals/Chat/DeleteChatModal'),
  {
    ssr: false,
  },
);
const AddChatToGroupModal = dynamic(
  () => import('@/components/molecules/Modals/Chat/AddChatToGroupModal'),
  {
    ssr: false,
  },
);
import FavoriteIcon from '@/components/atoms/Icons/FavoriteIcon';
import EmptyChats from '@/components/molecules/Empty/EmptyChats';

import { CustomSidebarChatsProps } from '@/components/molecules/Sidebars/CustomSidebarChats/CustomSidebarChats.props';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { AddChatToGroupType } from '@/types/common.types';

const CustomSidebarChats: FC<CustomSidebarChatsProps> = ({
  onLoadMore,
  className = '',
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const { message } = App.useApp();
  const hasMoreChats = useAppSelector((store) => store.chats.hasMoreChats);
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const vaultMode = useAppSelector((store) => store.chats.vaultMode);
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const chats = useAppSelector((store) => store.chats.chats);

  const [conversationsMenu, setConversationsMenu] = useState<
    GetProp<ConversationsProps, 'items'>
  >([]);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [editChat, setEditChat] = useState<AddChatToGroupType | null>(null);
  const [showVaultModeWarning, setShowVaultModeWarning] = useState(false);
  const clickInDropDown = useRef(false);
  const conversationRef = useRef<InputRef>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setConversationsMenu(
      sortChats(chats).map(
        ({
          chat_id,
          title,
          vault_mode = false,
          favorite = false,
          active = false,
          group_id = false,
          last_message_at,
          status,
        }) => ({
          key: chat_id,
          label: title,
          title,
          disabledByVault: vault_mode && (!vaultModeRegistered || !vaultMode),
          favorite,
          active,
          status,
          group_id,
          icon: <FavoriteIcon active={favorite} />,
          group: defineGroup({
            last_message_at,
            favorite,
            active,
          }),
        }),
      ),
    );
  }, [chats, vaultMode, vaultModeRegistered]);

  useClickOutside(conversationRef, () => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    const newTitle = conversationRef?.current?.nativeElement?.value;
    if (newTitle?.length && editId?.length) {
      onUpdateTitle({
        chat_id: editId,
        title: newTitle,
      });
    }
    clickInDropDown.current = false;
  });

  const menuConfig: ConversationsProps['menu'] = (conversation) => ({
    items: [
      {
        label: 'Edit',
        key: 'edit',
        icon: <EditOutlined />,
        disabled: conversation.disabled,
      },
      {
        label: 'Add to group',
        key: 'addToGroup',
        icon: <DoubleRightOutlined />,
      },
      {
        label: conversation?.favorite
          ? 'Remove from Favorite'
          : 'Add to Favorite',
        key: 'favorite',
        icon: <FavoriteIcon active={!conversation?.favorite} />,
      },
      {
        label: 'Delete',
        key: 'delete',
        icon: <DeleteOutlined />,
        danger: true,
        disabled: conversation.disabled,
      },
    ],
    onClick: async (menuInfo) => {
      if (
        conversation.status === ChatStatusEnum.READONLY &&
        menuInfo.key !== 'delete'
      ) {
        message.error(
          `This chat has the "read only" status. Please, choose another chat.`,
        );
        return;
      }
      if (conversation.disabledByVault) {
        setShowVaultModeWarning(true);
        return;
      }
      if (aiTyping) {
        message.error(
          `Before doing this action, please, wait until the assistant will finish generating the message`,
        );
        return;
      }
      clickInDropDown.current = true;
      if (menuInfo.key === 'delete') {
        onConfirmDelete(conversation.key);
      } else if (menuInfo.key === 'edit') {
        setConversationsMenu((prev) =>
          prev.map((item) => ({
            ...item,
            ...('title' in item && {
              label:
                item.key === conversation.key ? (
                  <Input
                    defaultValue={item?.title as string}
                    ref={conversationRef as LegacyRef<InputRef>}
                  />
                ) : (
                  (item?.title as string)
                ),
            }),
          })),
        );
        setEditId(conversation.key);
      } else if (menuInfo.key === 'favorite') {
        await onChangeFavorite({
          chat_id: conversation.key,
          favorite: !conversation.favorite,
        });
      } else if (menuInfo.key === 'addToGroup') {
        handleOpenMigration({
          group_id: conversation?.group_id as string,
          chat_id: conversation.key,
        });
      }
    },
  });

  const onChangeFavorite = async ({ chat_id = '', favorite = false }) => {
    try {
      const getCurrentChat = chats.find((item) => item.chat_id === chat_id);
      if (getCurrentChat) {
        await updateChat({
          id: chat_id,
          favorite,
          active: getCurrentChat.active,
          title: getCurrentChat.title,
          group_id: getCurrentChat.group_id,
        });
        dispatch(
          setChats(
            sortChats(
              chats.map((data) => ({
                ...data,
                favorite: data.chat_id === chat_id ? favorite : data.favorite,
              })),
            ),
          ),
        );
        message.success(
          `The chat "${getCurrentChat.title}" has successfully ${favorite ? 'added to' : 'deleted from'} the favorite list`,
        );
      }
    } catch (e) {
      handleError(e);
    } finally {
      clickInDropDown.current = false;
    }
  };

  const onConfirmDelete = (chat_id: string) => {
    if (chat_id) {
      setDeleteId(chat_id);
    }
  };

  const onChangeActive = async (chat_id: string) => {
    try {
      if (clickInDropDown.current) return;
      if (aiTyping) {
        message.error(
          `Before doing this action, please, wait until the assistant will finish generating the message`,
        );
        return;
      }
      const getActiveChat = chats.find((item) => item.chat_id === chat_id);
      if (getActiveChat) {
        if (
          getActiveChat.vault_mode &&
          getActiveChat.vault_mode !== vaultMode
        ) {
          setShowVaultModeWarning(true);
          return;
        }
        await updateChat({
          id: chat_id,
          favorite: getActiveChat.favorite,
          active: true,
          title: getActiveChat.title,
          group_id: getActiveChat.group_id,
        });

        dispatch(
          setChats(
            sortChats(
              chats.map(({ ...data }) => ({
                ...data,
                active: data.chat_id === chat_id,
              })),
            ),
          ),
        );

        const currentChat = await getChat({
          id: getActiveChat.chat_id,
        });
        const { docs, hasNextPage } = await getMessages({
          chat_id: getActiveChat.chat_id,
          page: 1,
          limit: CHAT_MESSAGES_PAGE_SIZE,
        });
        dispatch(
          setActiveChat({
            ...currentChat,
            active: true,
            messages: transformMessagesToObject(docs.reverse()),
          }),
        );
        dispatch(setHasMoreMessages(hasNextPage));
      }
    } catch (e) {
      handleError(e);
      clickInDropDown.current = false;
    }
  };

  const onUpdateTitle = async ({
    chat_id,
    title,
  }: {
    chat_id: string;
    title: string;
  }) => {
    try {
      if (chat_id && title) {
        const getActiveChat = chats.find((item) => item.chat_id === chat_id);
        if (getActiveChat) {
          await updateChat({
            id: chat_id,
            favorite: getActiveChat.favorite,
            active: getActiveChat.active,
            title,
            group_id: getActiveChat.group_id,
          });
          dispatch(
            setChats(
              chats.map(({ ...data }) => ({
                ...data,
                title: data.chat_id === chat_id ? title : data.title,
              })),
            ),
          );
          if (getActiveChat.active && activeChat) {
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
      setEditId(null);
      clickInDropDown.current = false;
    }
  };

  const handleOpenMigration = (data: AddChatToGroupType) => {
    if (!data) return;
    setEditChat(data);
  };

  useEffect(() => {
    const checkAndLoadMore = () => {
      const container = scrollContainerRef.current;
      const menu = menuRef.current;

      if (!container || !menu || !hasMoreChats) {
        return;
      }

      const containerHeight = container.clientHeight;
      const menuHeight = menu.scrollHeight || menu.clientHeight;
      const freeSpace = containerHeight - menuHeight;
      const freeSpacePercentage = (freeSpace / containerHeight) * 100;

      if (freeSpacePercentage > 0) {
        onLoadMore(false);
      } else {
      }
    };

    let timeoutId: NodeJS.Timeout;
    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        checkAndLoadMore();
      }, 150);
    };

    const initTimer = setTimeout(() => {
      checkAndLoadMore();
    }, 100);

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(initTimer);
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
    };
  }, [hasMoreChats]);

  return (
    <>
      <StyledSidebarBody
        className={`custom-sidebar-chats ${className}`}
        id='sidebar-body'
        ref={scrollContainerRef}
        {...props}
      >
        {!chats.length ? (
          <EmptyChats />
        ) : (
          <InfiniteScroll
            dataLength={chats.length}
            next={onLoadMore}
            hasMore={hasMoreChats}
            height='calc(100vh - 89px - 160px)'
            loader={
              <div style={{ textAlign: 'center' }}>
                <Spin indicator={<RedoOutlined spin />} size='small' />
              </div>
            }
            scrollableTarget='sidebar-body'
          >
            <div ref={menuRef}>
              <StyledConversations
                activeKey={activeChat?.chat_id}
                menu={menuConfig}
                items={conversationsMenu}
                onActiveChange={(key) => onChangeActive(key)}
                groupable={groupable()}
              />
            </div>
          </InfiniteScroll>
        )}
      </StyledSidebarBody>
      <DeleteChatModal
        deleteId={deleteId}
        setDeleteId={setDeleteId}
        onCloseCb={() => (clickInDropDown.current = false)}
      />

      <AddChatToGroupModal
        chat={editChat}
        setChat={setEditChat}
        onCloseCb={() => (clickInDropDown.current = false)}
      />

      <VaultModeWarningModal
        open={showVaultModeWarning}
        onCancel={() => setShowVaultModeWarning(false)}
      />
    </>
  );
};

export default CustomSidebarChats;
