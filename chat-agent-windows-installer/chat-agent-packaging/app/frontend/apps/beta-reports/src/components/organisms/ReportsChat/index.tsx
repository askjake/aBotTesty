import { Card, Skeleton } from 'antd';
import {
  FC,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import { TextAreaRef } from 'antd/es/input/TextArea';
import dynamic from 'next/dynamic';

import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { useAppDispatch } from '@shared/ui/store';
import {
  handleMessageSend,
  transformMessagesToObject,
  transformToMessages,
} from '@shared/ui/utils/messages.utils';
import { createChat, getChats } from '@shared/ui/services/chats.services';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import {
  setAiTyping,
  setHasMoreMessages,
} from '@shared/ui/store/chats/chats.slice';
import {
  changeMessageVersion,
  getMessages,
} from '@shared/ui/services/messages.services';

import { StyledReportsChatContainer } from '@/components/organisms/ReportsChat/ReportsChat.styled';
const MessagesBlock = dynamic(
  () => import('@shared/ui/components/molecules/Chat/MessagesBlock'),
  {
    ssr: false,
    loading: () => (
      <Skeleton.Node
        active
        styles={{
          root: { width: '100%' },
        }}
        style={{
          width: '100%',
          height: 'calc(100vh - 48px - 50px - 153px - 96px - 71px)',
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
        style={{ height: '106px', width: '100%', borderRadius: '1rem' }}
        styles={{
          root: { width: '100%' },
        }}
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

import { ReportsChatProps } from '@/components/organisms/ReportsChat/ReportsChat.props';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { ChatType } from '@shared/ui/types/chats.types';
import {
  ChangeVersionType,
  RawMessageType,
} from '@shared/ui/types/messages.types';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import { MessagesBlockRef } from '@shared/ui/components/molecules/Chat/MessagesBlock/MessagesBlock.props';

const ReportsChat: FC<ReportsChatProps> = ({
  chat,
  platform = PlatformEnum.ATV.toLowerCase(),
  className = '',
  componentRef,
  ...props
}) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const messageRef = useRef<TextAreaRef>(null);
  const prevPlatform = usePrevious(platform);
  const [activeChat, setActiveChat] = useState<ChatType | null>(chat);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef<MessagesBlockRef>(null);

  useEffect(() => {
    setCurrentPage(1);
    if (messagesRef?.current) {
      messagesRef?.current?.scrollBottom();
    }
  }, [activeChat?.chat_id]);

  useEffect(() => {
    if (prevPlatform && platform !== prevPlatform) {
      getActiveChat();
    }
  }, [platform]);

  useImperativeHandle(
    componentRef,
    () => ({
      refetchData: async () => {
        await getActiveChat();
      },
    }),
    [],
  );

  const getActiveChat = async () => {
    try {
      const namespace = `beta_report/${platform.toLowerCase()}`;
      const chats = await getChats({
        page: 1,
        limit: 1,
        namespace,
      });
      let activeChat = null;
      if (chats?.docs?.length) {
        activeChat = chats?.docs?.[0];
      } else {
        activeChat = await createChat({ namespace });
      }
      const { docs, hasNextPage } = await getMessages({
        chat_id: activeChat.chat_id,
        page: 1,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });
      setActiveChat({
        ...activeChat,
        active: true,
        messages: transformMessagesToObject(docs.reverse()),
      });
      setCurrentPage(1);
      dispatch(setHasMoreMessages(hasNextPage));
    } catch (e) {
      handleError(e);
    }
  };

  const onCancelEdit = useCallback(
    (message_id: string) => {
      if (message_id && activeChat) {
        setActiveChat({
          ...activeChat,
          messages: Object.fromEntries(
            Object.entries(activeChat.messages).map(([key, value]) => [
              key,
              { ...value, edit: false },
            ]),
          ),
        });
      }
    },
    [activeChat],
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
            setActiveChat: (value) => setActiveChat(value),
            activeChat,
            handleError,
          });
        }
      }
    },
    [activeChat, dispatch, handleError],
  );

  const onToggleEdit = useCallback(
    (message_id: string) => {
      if (message_id && activeChat) {
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
            {},
          ),
        });
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
              chat_id: activeChat?.chat_id,
              version_index: version_index,
            });
            setActiveChat({
              ...activeChat,
              messages: branched_history,
              active: true,
            });
          }
        }
      } catch (e) {
        handleError(e);
      }
    },
    [activeChat, handleError],
  );

  const messages = useMemo(
    () =>
      activeChat?.chat_id
        ? transformToMessages({
            messages: activeChat?.messages,
            refInput: messageRef,
            onToggleEdit,
            onChangeVersion,
            onCancelEdit,
            onSaveEdit,
            readyOnlyChat: activeChat?.status === ChatStatusEnum.READONLY,
            statusMessage: activeChat?.status_msg || '',
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
              content: <WelcomeBlock logo='/beta-reports/img/logo.png' />,
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
        chat_id: activeChat?.chat_id,
        page: nextPage,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });

      setActiveChat({
        ...activeChat,
        messages: {
          ...transformMessagesToObject(docs.reverse()),
          ...activeChat.messages,
        },
      });
      dispatch(setHasMoreMessages(hasNextPage));
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className={`reports-chat ${className}`} {...props}>
      <StyledReportsChatContainer $hasMessages={!!messages.length}>
        <MessagesBlock
          isLoading={loading}
          onLoadMore={onLoadMore}
          customHeight='calc(100vh - 48px - 50px - 153px - 96px - 71px)'
          componentRef={messagesRef}
          items={items}
        />
        <ChatSender
          activeChat={activeChat}
          onRequest={(values) =>
            handleMessageSend({
              ...values,
              setAiTyping: (value) => dispatch(setAiTyping(value)),
              setActiveChat: (value) => setActiveChat(value),
              activeChat,
              handleError,
            })
          }
        />
      </StyledReportsChatContainer>
    </Card>
  );
};

export default ReportsChat;
