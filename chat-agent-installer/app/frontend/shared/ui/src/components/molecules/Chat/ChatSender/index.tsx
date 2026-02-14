import dynamic from 'next/dynamic';
import { FC, useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { Sender } from '@ant-design/x';
import { Button, Dropdown, Flex, MenuProps } from 'antd';
import { VscLightbulbSparkle, VscSettings } from 'react-icons/vsc';
import { CloseOutlined } from '@ant-design/icons';

import { useAppSelector } from '@shared/ui/store';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';
import { uploadAttachments } from '@shared/ui/services/attachments.services';
import { dexieDb } from '@shared/ui/libs/dexie.libs';
import { isIndexedDBSupported } from '@shared/ui/utils/common.utils';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

import { StyledChatSenderWrapper } from '@shared/ui/components/molecules/Chat/ChatSender/ChatSender.styled';
import SenderHeaderBlock from '../SenderHeaderBlock';
const AttachmentButton = dynamic(
  () => import('@shared/ui/components/molecules/Chat/AttachmentButton'),
);

import { AttachmentType, FileType } from '@shared/ui/types/attachments.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { SenderHeaderBlockRef } from '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.props';
import { ChatSenderProps } from '@shared/ui/components/molecules/Chat/ChatSender/ChatSender.props';

const items: MenuProps['items'] = [
  {
    key: '0',
    label: 'Tools',
    disabled: true,
  },
  {
    type: 'divider',
  },
  {
    key: '1',
    label: 'Enable Reasoning',
    icon: <VscLightbulbSparkle />,
  },
];

const ChatSender: FC<ChatSenderProps> = ({
  onRequest,
  activeChat = null,
  className = '',
}) => {
  const handleError = useHandleError();
  const [selectedKey, setSelectedKey] = useState<string[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [attachmentsList, setAttachmentsList] = useState<AttachmentType[]>([]);
  const [headerOpen, setHeaderOpen] = useState(false);
  const [loading, setLoading] = useState<boolean>(false);
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );
  const senderHeaderBlockRef = useRef<SenderHeaderBlockRef>(null);
  const prevChatId = usePrevious(activeChat?.chat_id);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const isReadyOnlyChat = useMemo(
    () => activeChat?.status === ChatStatusEnum.READONLY,
    [activeChat],
  );

  // Load draft message on mount or when chat changes
  useEffect(() => {
    if (isIndexedDBSupported()) {
      const loadDraftMessage = async () => {
        if (activeChat?.chat_id) {
          try {
            const draft = await dexieDb.draftMessages.get(activeChat.chat_id);
            if (draft?.message) {
              setNewMessage(draft.message);
            }
          } catch (e) {
            handleError(e);
          }
        }
      };

      loadDraftMessage();
    }
  }, [activeChat?.chat_id]);

  // Clear draft when switching chats
  useEffect(() => {
    if (prevChatId && activeChat?.chat_id !== prevChatId) {
      setNewMessage('');
      senderHeaderBlockRef?.current?.resetAttachments?.();
      setAttachmentsList([]);
    }
  }, [activeChat, prevChatId]);

  // Debounced save to IndexedDB
  const saveDraftMessage = useCallback(
    (message: string) => {
      if (!activeChat?.chat_id) return;

      // Clear existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Set new timer
      debounceTimerRef.current = setTimeout(async () => {
        try {
          if (message.trim()) {
            await dexieDb.draftMessages.put({
              chat_id: activeChat.chat_id,
              message,
              updated_at: new Date(),
            });
          } else {
            // Remove draft if message is empty
            await dexieDb.draftMessages.delete(activeChat.chat_id);
          }
        } catch (e) {
          handleError(e);
        }
      }, 500);
    },
    [activeChat?.chat_id],
  );

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleMessageChange = (value: string) => {
    setNewMessage(value);
    if (isIndexedDBSupported()) {
      saveDraftMessage(value);
    }
  };

  const onSubmit = async (nextContent: string) => {
    if (!nextContent) return;
    try {
      setNewMessage('');
      setHeaderOpen(false);
      senderHeaderBlockRef?.current?.resetAttachments?.();

      await onRequest({
        content: nextContent,
        attachments: attachmentsList,
        selectedKey,
      });
      // Remove draft from IndexedDB after successful send
      if (activeChat?.chat_id && isIndexedDBSupported()) {
        await dexieDb.draftMessages.delete(activeChat.chat_id);
      }
    } catch (e) {
      console.error(e);
      setNewMessage(nextContent);
    } finally {
      setAttachmentsList([]);
    }
  };

  const onAddAttachment = async (
    files: FileType[],
  ): Promise<{ attachments: AttachmentType[] }> => {
    const { attachments = [] } = await uploadAttachments(files);
    setAttachmentsList((prev) => [...prev, ...attachments]);
    return {
      attachments,
    };
  };

  const onRemoveAttachment = (attachment_id: string) => {
    setAttachmentsList((prev) =>
      prev.filter((item) => item.attachment_id !== attachment_id),
    );
  };

  const renderToolButton = (key = '') => {
    if (key === '1') {
      return (
        <Button
          color='primary'
          disabled={loading || aiTyping}
          variant='filled'
          icon={<VscLightbulbSparkle />}
          onClick={() => setSelectedKey([])}
        >
          <span>Reasoning</span>
          <CloseOutlined />
        </Button>
      );
    }
    return;
  };

  return (
    <StyledChatSenderWrapper $collapsedSidebar={collapsedSidebar}>
      <Sender
        className={`chat-sender ${className}`}
        value={newMessage}
        suffix={false}
        header={
          <SenderHeaderBlock
            onAddAttachment={onAddAttachment}
            onRemoveAttachment={onRemoveAttachment}
            open={headerOpen}
            onOpenChange={setHeaderOpen}
            setLoading={setLoading}
            componentRef={senderHeaderBlockRef}
          />
        }
        onSubmit={onSubmit}
        onChange={handleMessageChange}
        footer={(_, { components }) => {
          const { SendButton, LoadingButton } = components;
          return (
            <Flex justify='space-between' align='center'>
              <Flex gap='small' align='center'>
                <AttachmentButton
                  setHeaderOpen={setHeaderOpen}
                  headerOpen={headerOpen}
                  hasFiles={!!attachmentsList.length}
                  disabled={loading || isReadyOnlyChat || aiTyping}
                />
                <Dropdown
                  trigger={['click']}
                  menu={{
                    items,
                    disabled: loading || aiTyping,
                    selectable: true,
                    selectedKeys: selectedKey,
                    onClick: ({ key }) =>
                      setSelectedKey((prev) =>
                        prev.includes(key) ? [] : [key],
                      ),
                  }}
                >
                  <Button
                    type='text'
                    shape='circle'
                    icon={<VscSettings />}
                    disabled={loading || isReadyOnlyChat || aiTyping}
                  />
                </Dropdown>
                {renderToolButton(selectedKey[0])}
              </Flex>
              <Flex align='center'>
                {loading || aiTyping ? (
                  <LoadingButton type='default' />
                ) : (
                  <SendButton type='primary' disabled={isReadyOnlyChat} />
                )}
              </Flex>
            </Flex>
          );
        }}
        loading={loading || aiTyping}
        disabled={isReadyOnlyChat}
      />
    </StyledChatSenderWrapper>
  );
};

export default ChatSender;
