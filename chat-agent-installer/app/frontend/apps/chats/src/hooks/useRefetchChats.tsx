import { getChat, getChats } from '@shared/ui/services/chats.services';
import {
  setActiveChat,
  setChats,
  setHasMoreChats,
  setHasMoreMessages,
  setTotalChats,
} from '@shared/ui/store/chats/chats.slice';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import {
  CHAT_MESSAGES_PAGE_SIZE,
  CHATS_PAGE_SIZE,
} from '@shared/ui/constants/common.constants';
import { getMessages } from '@shared/ui/services/messages.services';
import { transformMessagesToObject } from '@shared/ui/utils/messages.utils';

const useRefetchChats = () => {
  const dispatch = useAppDispatch();
  const vaultMode = useAppSelector((store) => store.chats.vaultMode);
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const activeChatGroup = useAppSelector(
    (store) => store.chatsGroups.activeChatGroup,
  );

  const refetchChats = async () => {
    const {
      docs = [],
      hasNextPage = false,
      active_chat_id,
      totalDocs = 0,
    } = await getChats({
      page: 1,
      limit: CHATS_PAGE_SIZE,
      group_id: activeChatGroup,
    });
    const chats = docs.map((item) => ({
      ...item,
      active: active_chat_id === item.chat_id,
    }));
    dispatch(
      setChats(
        chats.map((item) => ({
          ...item,
          active: item.chat_id === active_chat_id,
        })),
      ),
    );
    dispatch(setHasMoreChats(hasNextPage));
    dispatch(setTotalChats(totalDocs));
    if (active_chat_id) {
      const activeChat = await getChat({
        id: active_chat_id,
      });
      const { docs, hasNextPage } = await getMessages({
        chat_id: active_chat_id,
        page: 1,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });
      dispatch(
        setActiveChat({
          ...activeChat,
          messages: !activeChat.vault_mode
            ? transformMessagesToObject(docs.reverse())
            : vaultModeRegistered && vaultMode
              ? transformMessagesToObject(docs.reverse())
              : {},

          active: true,
        }),
      );
      dispatch(setHasMoreMessages(hasNextPage));
    }
  };

  return { refetchChats };
};

export default useRefetchChats;
