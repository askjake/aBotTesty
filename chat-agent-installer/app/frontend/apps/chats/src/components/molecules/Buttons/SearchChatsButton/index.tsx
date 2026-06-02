import { FC, useEffect, useMemo, useState } from 'react';
import { SearchOutlined } from '@ant-design/icons';
import { Tooltip } from 'antd';
import dynamic from 'next/dynamic';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { setActiveChat, setChats } from '@shared/ui/store/chats/chats.slice';
import useDebouncedCallback from '@shared/ui/hooks/useDebounceCallback.hook';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';
import {
  getChat,
  getChats,
  updateChat,
} from '@shared/ui/services/chats.services';
import { defineGroup, sortChats } from '@/utils/chats.utils';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { CHATS_PAGE_SIZE } from '@shared/ui/constants/common.constants';

import FavoriteIcon from '@/components/atoms/Icons/FavoriteIcon';
import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';
const SearchModal = dynamic(
  () => import('@/components/molecules/Modals/SearchModal'),
  {
    ssr: false,
  },
);
const VaultModeWarningModal = dynamic(
  () => import('@/components/molecules/Modals/VaultMode/VaultModeWarningModal'),
  {
    ssr: false,
  },
);

import { SearchButtonProps } from '@/components/molecules/Buttons/SearchChatsButton/SearchChatsButton.props';
import { ChatType } from '@shared/ui/types/chats.types';

const SearchChatsButton: FC<SearchButtonProps> = (props) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();

  const [showSearchModal, setSearchModal] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMoreData, setHasMoreData] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showVaultModeWarning, setShowVaultModeWarning] = useState(false);
  const [data, setData] = useState<ChatType[]>([]);
  const prevSearchText = usePrevious(searchText);
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const vaultMode = useAppSelector((store) => store.chats.vaultMode);
  const chats = useAppSelector((store) => store.chats.chats);
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const activeChatGroup = useAppSelector(
    (store) => store.chatsGroups.activeChatGroup,
  );

  const chatsList = useMemo(
    () =>
      sortChats(data).map(
        ({
          chat_id,
          title,
          vault_mode = false,
          favorite = false,
          active = false,
          last_message_at,
          status,
        }) => ({
          key: chat_id,
          label: title,
          disabledByVault: vault_mode && (!vaultModeRegistered || !vaultMode),
          favorite,
          active,
          status,
          icon: <FavoriteIcon active={favorite} />,
          group: defineGroup({
            last_message_at,
            favorite,
            active,
          }),
        }),
      ),
    [data, vaultMode, vaultModeRegistered],
  );

  const onDebouncedSearch = useDebouncedCallback(() => {
    setCurrentPage(1);
    onLoadMore(true);
  }, 500);

  useEffect(() => {
    if (showSearchModal) {
      onLoadMore(true);
    }
  }, [showSearchModal]);

  useEffect(() => {
    if (prevSearchText !== null && searchText !== prevSearchText) {
      onDebouncedSearch();
    }
  }, [searchText]);

  const onLoadMore = async (isSearch = false) => {
    try {
      if (loading || !showSearchModal) {
        return;
      }
      setLoading(true);
      const nextPage = isSearch ? 1 : currentPage + 1;
      const { docs = [], hasNextPage = false } = await getChats({
        page: nextPage,
        search: searchText,
        group_id: activeChatGroup,
        limit: CHATS_PAGE_SIZE,
      });
      const newChats = docs.map((item) => ({
        ...item,
        active: activeChat?.chat_id === item.chat_id,
      }));
      if (nextPage > 1) {
        setData((prev) =>
          sortChats(
            [...prev, ...newChats].map((item) => ({
              ...item,
              active: item.chat_id === activeChat?.chat_id,
            })),
          ),
        );
      } else {
        setData(sortChats(newChats));
      }
      setHasMoreData(hasNextPage);
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };
  const onChangeActive = async (chat_id: string) => {
    try {
      const getActiveChat = data.find((item) => item.chat_id === chat_id);
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

        const { messages = {}, ...data } = await getChat({
          id: getActiveChat.chat_id,
        });
        dispatch(
          setActiveChat({
            ...data,
            active: true,
            messages,
          }),
        );
      }
    } catch (e) {
      handleError(e);
    } finally {
      setSearchModal(false);
    }
  };
  const handleCloseSearchModal = () => {
    setSearchModal(false);
    setSearchText('');
    setData([]);
    setHasMoreData(false);
    setCurrentPage(0);
  };
  return (
    <>
      <Tooltip title='Search chats'>
        <IconButton
          type='text'
          onClick={() => setSearchModal((prev) => !prev)}
          icon={<SearchOutlined />}
          {...props}
        />
      </Tooltip>
      <SearchModal
        customSearchPlaceholder='Search chats...'
        open={showSearchModal}
        items={chatsList}
        hasMoreData={hasMoreData}
        activeKey={activeChat?.chat_id}
        onActiveKeyChange={(value) => onChangeActive(value)}
        onCancel={handleCloseSearchModal}
        onSearchChange={(value) => setSearchText(value)}
        onLoadMore={onLoadMore}
        destroyOnHidden
      />
      <VaultModeWarningModal
        open={showVaultModeWarning}
        onCancel={() => setShowVaultModeWarning(false)}
      />
    </>
  );
};

export default SearchChatsButton;
