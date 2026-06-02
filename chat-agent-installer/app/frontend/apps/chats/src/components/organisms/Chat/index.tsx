// apps/chats/src/components/organisms/Chat/index.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import dynamic from 'next/dynamic';
import { Skeleton } from 'antd';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import {
  handleMessageSend,
  transformMessagesToObject,
  transformToMessages,
} from '@shared/ui/utils/messages.utils';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import {
  changeMessageVersion,
  getMessages,
} from '@shared/ui/services/messages.services';
import {
  setActiveChat,
  setAiTyping,
  setChats,
  setHasMoreMessages,
  setTotalChats,
} from '@shared/ui/store/chats/chats.slice';
import { setActiveChatGroup } from '@shared/ui/store/chatsGroups/chatsGroups.slice';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';

import { StyledChatContainer } from '@/components/organisms/Chat/Chat.styled';

const MessagesBlock = dynamic(
  () => import('@shared/ui/components/molecules/Chat/MessagesBlock'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Node
        active
        style={{
          width: '75vw',
          height: 'calc(100vh - 64px - 96px - 72px - 5.5rem)',
          borderRadius: '1rem',
        }}
      />
    ),
  },
);

const ChatSender = dynamic(
  () => import('@shared/ui/components/molecules/Chat/ChatSender'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Node
        active
        style={{ height: '106px', width: '75vw', borderRadius: '1rem' }}
      />
    ),
  },
);

const WelcomeBlock = dynamic(
  () => import('@shared/ui/components/molecules/Chat/WelcomeBlock'),
  {
    ssr: false,
  },
);

const Result = dynamic(() => import('antd').then((mod) => mod.Result), {
  ssr: false,
});

const ChatSettings = dynamic(
  () => import('@/components/organisms/ChatSettings'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Button
        active
        shape="circle"
        style={{
          position: 'fixed',
          bottom: '50%',
          insetInlineEnd: 'var(--ant-margin-lg)',
          width: '40px',
          height: '40px',
        }}
      />
    ),
  },
);

import {
  ChangeVersionType,
  RawMessageType,
} from '@shared/ui/types/messages.types';
import { TextAreaRef } from 'antd/es/input/TextArea';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { MessagesBlockRef } from '@shared/ui/components/molecules/Chat/MessagesBlock/MessagesBlock.props';

const Chat = () => {
  const dispatch = useAppDispatch();

  const vaultMode = useAppSelector((store) => store.chats.vaultMode);
  const vaultModeRegistered = useAppSelector(
    (store) => store.chats.vaultModeRegistered,
  );
  const activeChat = useAppSelector((store) => store.chats.activeChat);
  const chats = useAppSelector((store) => store.chats.chats);
  const totalChats = useAppSelector((store) => store.chats.totalChats);
  const messageRef = useRef<TextAreaRef>(null);
  const handleError = useHandleError();
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef<MessagesBlockRef>(null);

  useEffect(() => {
    setCurrentPage(1);
    if (messagesRef?.current) {
      messagesRef.current.scrollBottom();
    }
  }, [activeChat?.chat_id]);

  const disabledByVault = useMemo(
    () => (activeChat?.vault_mode ? !vaultModeRegistered || !vaultMode : false),
    [vaultMode, vaultModeRegistered, activeChat],
  );

  const onCancelEdit = useCallback(
    (message_id: string) => {
      if (message_id && activeChat) {
        dispatch(
          setActiveChat({
            ...activeChat,
            messages: Object.fromEntries(
              Object.entries(activeChat.messages).map(([key, value]) => [
                key,
                { ...value, edit: false },
              ]),
            ),
          }),
        );
      }
    },
    [activeChat, dispatch],
  );

  const onSaveEdit = useCallback(
    async (message_id: string) => {
      if (message_id && activeChat) {
        const newContent =
          messageRef?.current?.resizableTextArea?.textArea?.value;
        if (
          newContent?.length &&
          newContent !== activeChat?.messages[message_id]?.content[0]?.text
        ) {
          await handleMessageSend({
            content: newContent,
            message_id,
            setAiTyping: (value) => dispatch(setAiTyping(value)),
            setActiveChat: (value) => dispatch(setActiveChat(value)),
            setTotalChats: (value) => dispatch(setTotalChats(value)),
            setActiveChatGroup: (value) => dispatch(setActiveChatGroup(value)),
            setChats: (value) => dispatch(setChats(value)),
            activeChat,
            chats,
            totalChats,
            handleError,
          });
        }
      }
    },
    [activeChat, chats, dispatch, handleError, totalChats],
  );

  const onToggleEdit = useCallback(
    (message_id: string) => {
      if (message_id && activeChat) {
        dispatch(
          setActiveChat({
            ...activeChat,
            messages: Object.entries(activeChat.messages).reduce(
              (prev: RawMessageType, [key, value]) => {
                prev[key] = {
                  ...value,
                  edit: key === message_id ? !value?.edit : false,
                };
                return prev;
              },
              {} as RawMessageType,
            ),
          }),
        );
      }
    },
    [activeChat, dispatch],
  );

  const onChangeVersion: ChangeVersionType = useCallback(
    async ({ message_id, version_index }) => {
      try {
        if (activeChat) {
          const currentMessage = activeChat.messages[message_id];
          if (currentMessage) {
            const { branched_history = {} } = await changeMessageVersion({
              message_id,
              chat_id: activeChat.chat_id,
              version_index,
            });
            dispatch(
              setActiveChat({
                ...activeChat,
                messages: branched_history,
                active: true,
              }),
            );
          }
        }
      } catch (e) {
        handleError(e);
      }
    },
    [activeChat, dispatch, handleError],
  );

  const messages = useMemo(
    () =>
      activeChat?.chat_id
        ? transformToMessages({
            messages: activeChat.messages,
            refInput: messageRef,
            onToggleEdit,
            onChangeVersion,
            onCancelEdit,
            onSaveEdit,
            readyOnlyChat: activeChat.status === ChatStatusEnum.READONLY,
            statusMessage: activeChat.status_msg || '',
          })
        : [],
    [
      activeChat?.chat_id,
      activeChat?.messages,
      activeChat?.status,
      activeChat?.status_msg,
      onCancelEdit,
      onChangeVersion,
      onSaveEdit,
      onToggleEdit,
    ],
  );

  const items = useMemo(
    () =>
      messages.length > 0
        ? messages
        : [
            {
              key: 'welcome',
              role: 'Welcome',
              content: <WelcomeBlock />,
            },
          ],
    [messages],
  );

  const onLoadMore = async (resetData = false) => {
    try {
      if (loading || !activeChat?.chat_id) {
        return;
      }
      setLoading(true);
      const nextPage = resetData ? 1 : currentPage + 1;
      const { docs, hasNextPage } = await getMessages({
        chat_id: activeChat.chat_id,
        page: nextPage,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });

      dispatch(
        setActiveChat({
          ...activeChat,
          messages: {
            ...transformMessagesToObject(docs.reverse()),
            ...activeChat.messages,
          },
        }),
      );
      dispatch(setHasMoreMessages(hasNextPage));
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <StyledChatContainer
      className="chat"
      $hasMessages={!!messages.length}
      $disabledByVault={disabledByVault}
    >
      {disabledByVault ? (
        <Result
          status="error"
          title="Access denied"
          subTitle="The conversation is safety in your vault. Enter vault mode to view it."
        />
      ) : (
        <>
          <MessagesBlock
            isLoading={loading}
            onLoadMore={onLoadMore}
            componentRef={messagesRef}
            items={items}
          />
          <ChatSender
            activeChat={activeChat}
            onRequest={(values) =>
              handleMessageSend({
                ...values,
                setAiTyping: (value) => dispatch(setAiTyping(value)),
                setActiveChat: (value) => dispatch(setActiveChat(value)),
                setTotalChats: (value) => dispatch(setTotalChats(value)),
                setActiveChatGroup: (value) =>
                  dispatch(setActiveChatGroup(value)),
                setChats: (value) => dispatch(setChats(value)),
                activeChat,
                chats,
                totalChats,
                handleError,
              })
            }
          />
        </>
      )}
      {activeChat?.messages && Object.keys(activeChat.messages).length > 1 ? (
        <ChatSettings />
      ) : null}
    </StyledChatContainer>
  );
};

export default Chat;

