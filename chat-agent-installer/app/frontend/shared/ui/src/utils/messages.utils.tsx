import { Flex, GetProp, Input, Space } from 'antd';
import { nanoid } from 'nanoid';
import { LegacyRef, ReactNode, RefObject } from 'react';

const { TextArea } = Input;

import { ALLOWED_IMAGES_MIME_TYPES } from '@shared/ui/constants/validation.constants';
import { BACKEND_URL } from '@shared/ui/constants/env.constants';

import {
  MessageListType,
  MessageType,
  OriginalMessageType,
  RawMessageType,
  TransformMessagesType,
} from '@shared/ui/types/messages.types';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { TextAreaRef } from 'antd/es/input/TextArea';
import { Conversations } from '@ant-design/x';
import { CommentOutlined } from '@ant-design/icons';
import {
  createMessage,
  createMessageVersion,
} from '@shared/ui/services/messages.services';
import { createChat, getChat } from '@shared/ui/services/chats.services';
import { ChatRequestProps, ChatType } from '@shared/ui/types/chats.types';
import { XStream } from '@ant-design/x-sdk';
import { StreamResponseType } from '@shared/ui/types/stream.types';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import { omitKeys } from '@shared/ui/utils/common.utils';

export const renderUserInputInMessage = ({
  content,
  refInput,
  edit = false,
}: {
  content: string;
  refInput: RefObject<TextAreaRef | null>;
  edit: boolean;
}) => {
  return (
    <>
      {edit ? (
        <TextArea
          ref={refInput as LegacyRef<TextAreaRef>}
          defaultValue={content}
          autoSize={{ minRows: 1, maxRows: 10 }}
        />
      ) : (
        content
      )}
    </>
  );
};

export const renderUserMessage = ({
  key,
  content,
  version_count,
  version_index,
  edit = false,
  refInput,
  onChangeVersion,
  onToggleEdit,
  onSaveEdit,
  onCancelEdit,
  showEditBtn = false,
  readyOnlyChat = false,
}: MessageListType &
  Pick<
    TransformMessagesType,
    | 'refInput'
    | 'onChangeVersion'
    | 'onToggleEdit'
    | 'onSaveEdit'
    | 'onCancelEdit'
  > & {
    showEditBtn: boolean;
  }) => {
  return {
    key,
    role: RoleEnum.USER,
    version_count,
    version_index,
    onChangeVersion,
    onToggleEdit,
    onSaveEdit,
    onCancelEdit,
    edit,
    refInput,
    showEditBtn,
    content,
    readyOnlyChat,
  };
};

export const renderAttachmentMessages = ({
  attachments = [],
  version_index = 0,
  version_count = 1,
}: Pick<MessageType, 'attachments' | 'version_index' | 'version_count'>) => {
  return {
    key: nanoid(4),
    role: 'fileUser',
    version_count,
    version_index,
    content: attachments.map(({ attachment_id, filename, media_type }) => ({
      uid: attachment_id,
      name: filename,
      ...(Object.keys(ALLOWED_IMAGES_MIME_TYPES).includes(media_type) && {
        thumbUrl: `${BACKEND_URL}/attachments/${attachment_id}`,
        url: `${BACKEND_URL}/attachments/${attachment_id}`,
      }),
    })),
  };
};

export const renderAIMessage = ({
  key,
  content,
  version_count,
  version_index,
  loading = false,
}: MessageListType) => {
  return {
    key,
    role: RoleEnum.ASSISTANT,
    content,
    version_count,
    version_index,
    loading,
  };
};

export const transformToMessages = ({
  messages = {},
  onChangeVersion,
  onToggleEdit,
  refInput,
  onSaveEdit,
  onCancelEdit,
  readyOnlyChat,
  statusMessage,
}: TransformMessagesType): MessageListType[] => [
  ...Object.entries(messages).reduce(
    (
      prev: MessageListType[],
      [
        message_id,
        {
          content,
          role = RoleEnum.USER,
          version_count = 0,
          version_index = 0,
          attachments = [],
          edit = false,
          loading = false,
        },
      ],
    ) => {
      if (role == RoleEnum.USER) {
        if (attachments.length) {
          prev = [
            ...prev,
            renderAttachmentMessages({
              version_count,
              version_index,
              attachments,
            }),
          ];
        }
        prev = [
          ...prev,
          renderUserMessage({
            role,
            key: message_id,
            content,
            version_count,
            version_index,
            edit,
            onToggleEdit,
            onChangeVersion,
            refInput,
            onSaveEdit,
            onCancelEdit,
            showEditBtn: !attachments.length,
            readyOnlyChat,
          }),
        ];
      } else if (role === RoleEnum.ASSISTANT) {
        prev = [
          ...prev,
          renderAIMessage({
            key: message_id,
            role,
            content,
            version_count,
            version_index,
            loading,
          }),
        ];
      }
      return prev;
    },
    [],
  ),
  ...(readyOnlyChat
    ? [
        {
          key: 'error',
          role: 'error',
          content: statusMessage,
          version_count: 0,
          version_index: 0,
        },
      ]
    : []),
];

export const groupable = (
  icon: ReactNode | undefined = <CommentOutlined />,
): GetProp<typeof Conversations, 'groupable'> => ({
  label: (group) => (
    <Flex gap='small'>
      <Space>
        {icon}
        <span>{group}</span>
      </Space>
    </Flex>
  ),
});

export const transformMessagesToObject = (
  messages: OriginalMessageType[] = [],
) =>
  Array.isArray(messages)
    ? Object.assign(
        {},
        ...messages.map(({ message_id, ...fields }) => ({
          [message_id]: {
            ...fields,
          },
        })),
      )
    : {};

export const handleMessageSend = async ({
  content,
  message_id,
  attachments = [],
  selectedKey = ['1'],
  setAiTyping,
  setChats,
  setTotalChats,
  setActiveChatGroup,
  setActiveChat,
  activeChat,
  chats = [],
  totalChats = 0,
  handleError,
}: ChatRequestProps & {
  setAiTyping: (typing: boolean) => void;
  setChats?: (chats: ChatType[]) => void;
  setTotalChats?: (total: number) => void;
  setActiveChatGroup?: (group: string) => void;
  setActiveChat: (chat: ChatType) => void;
  activeChat: ChatType | null;
  chats?: ChatType[];
  totalChats?: number;
  handleError: (error: any) => void;
}) => {
  try {
    setAiTyping(true);

    // Check if the active chat exists
    let currentChat: ChatType | null = activeChat
      ? structuredClone({ ...activeChat })
      : null;
    const prevChats = [...chats];

    // Create a new chat if the current chat doesn't exist
    if (!currentChat) {
      const chat = await createChat({
        namespace: 'generic',
      });

      currentChat = {
        ...chat,
        active: true,
        messages: {},
      };

      prevChats.unshift(currentChat);
      if (setChats) {
        setChats(
          prevChats.map((item) => ({
            ...item,
            active: item.chat_id === currentChat?.chat_id,
          })),
        );
      }
      if (setTotalChats) {
        setTotalChats(totalChats + 1);
      }

      if (setActiveChatGroup) {
        setActiveChatGroup('all');
      }
    }

    // Check if a new message, or it is creating a new version for existing message
    const messageStream = message_id
      ? await createMessageVersion({
          message_id,
          chat_id: currentChat.chat_id,
          content,
        })
      : await createMessage({
          chat_id: currentChat.chat_id,
          content,
          message_config: {
            reasoning: selectedKey[0] === '1',
          },
          attachments: attachments.map(
            ({ attachment_id, owner_id, filename, media_type }) => ({
              attachment_id,
              owner_id,
              filename,
              media_type,
            }),
          ),
        });

    // Editing message logic
    if (message_id) {
      // Disable editing - optimize by only updating edit flag
      const updatedMessages = { ...currentChat.messages };
      Object.keys(updatedMessages).forEach((key) => {
        if (updatedMessages[key]?.edit) {
          updatedMessages[key] = { ...updatedMessages[key], edit: false };
        }
      });

      currentChat = { ...currentChat, messages: updatedMessages };

      // Check if message exists
      const currentMessage = currentChat.messages[message_id];
      if (!currentMessage || currentMessage?.content[0]?.text === content) {
        return;
      }

      // Add new version and truncate messages after current message
      const messageKeys = Object.keys(currentChat.messages);
      const messageIndex = messageKeys.indexOf(message_id);
      const messagesToKeep = messageKeys.slice(0, messageIndex + 1);

      currentChat = {
        ...currentChat,
        messages: {
          ...Object.fromEntries(
            messagesToKeep.map((key) => [
              key,
              currentChat?.messages[key] as RawMessageType[string],
            ]),
          ),
          [message_id]: {
            ...currentChat.messages[message_id],
            content: {
              0: {
                type: MessageTypeEnum.TEXT,
                text: content,
              },
            },
            version_index:
              (currentChat?.messages[message_id]?.version_index || 0) + 1,
            version_count:
              (currentChat?.messages[message_id]?.version_count || 0) + 1,
          },
        },
      };
    }

    if (currentChat) {
      let aiMessageId = '';
      let userMessageId = '';
      // Store content by index to prevent overwriting
      const contentByIndex: Record<
        number,
        { type: string; buffer: string[]; startTime: number }
      > = {};

      // Buffer system for constant speed rendering
      let isStreamComplete = false;
      let renderIntervalId: NodeJS.Timeout | null = null;

      // Configuration
      const CHARS_PER_RENDER = 3; // Characters to render per interval
      const RENDER_INTERVAL_MS = 19; // ~158 chars/sec

      // Track displayed length for each content block
      const displayedLengths: Record<number, number> = {};

      // Function to calculate how much should be rendered based on elapsed time
      const calculateRenderedLength = (
        blockIndex: number,
        currentTime: number,
      ) => {
        const block = contentByIndex[blockIndex];
        if (!block || !block.startTime) return 0;

        const fullLength = block.buffer.join('').length;
        const elapsedTime = currentTime - block.startTime;
        const charsToRender = Math.floor(
          (elapsedTime / RENDER_INTERVAL_MS) * CHARS_PER_RENDER,
        );

        return Math.min(charsToRender, fullLength);
      };

      // Function to render buffered content at constant speed
      const renderBufferedContent = () => {
        const currentTime = Date.now();
        let hasUpdate = false;
        const contentUpdates: Record<number, any> = {};

        // Process each content block
        Object.keys(contentByIndex).forEach((idx) => {
          const numIdx = Number(idx);
          const block = contentByIndex[numIdx];
          const fullBufferedContent = block.buffer.join('');

          if (!displayedLengths[numIdx]) {
            displayedLengths[numIdx] = 0;
          }

          // Calculate how much should be rendered based on time elapsed
          const targetLength = calculateRenderedLength(numIdx, currentTime);

          // Update displayed length if we need to catch up
          if (displayedLengths[numIdx] < targetLength) {
            displayedLengths[numIdx] = targetLength;

            if (block.type === 'text') {
              contentUpdates[numIdx] = {
                type: MessageTypeEnum.TEXT,
                text: fullBufferedContent.substring(
                  0,
                  displayedLengths[numIdx],
                ),
              };
            } else if (block.type === 'reasoning') {
              contentUpdates[numIdx] = {
                type: MessageTypeEnum.REASONING,
                reasoning: fullBufferedContent.substring(
                  0,
                  displayedLengths[numIdx],
                ),
              };
            }
            hasUpdate = true;
          }
        });

        // Apply all updates at once
        if (hasUpdate) {
          currentChat = {
            ...currentChat!,
            messages: {
              ...currentChat!.messages,
              [aiMessageId]: {
                ...currentChat!.messages[aiMessageId],
                content: {
                  ...currentChat!.messages[aiMessageId]?.content,
                  ...contentUpdates,
                },
                loading: false,
              },
            },
          };
          setActiveChat({ ...currentChat! });
        }

        // Stop interval if streaming is complete and all content is rendered
        if (isStreamComplete) {
          const allComplete = Object.keys(contentByIndex).every((idx) => {
            const numIdx = Number(idx);
            const block = contentByIndex[numIdx];
            const fullLength = block.buffer.join('').length;
            return (
              block.buffer.length === 0 ||
              displayedLengths[numIdx] >= fullLength
            );
          });

          if (allComplete && renderIntervalId) {
            clearInterval(renderIntervalId);
            renderIntervalId = null;
          }
        }
      };

      // Handle visibility change - catch up on rendering when tab becomes visible
      const handleVisibilityChange = () => {
        if (!document.hidden) {
          // Tab became visible - trigger immediate render to catch up
          renderBufferedContent();
        }
      };

      // Add visibility change listener
      document.addEventListener('visibilitychange', handleVisibilityChange);

      // Start the constant-speed rendering interval
      renderIntervalId = setInterval(renderBufferedContent, RENDER_INTERVAL_MS);

      try {
        for await (const chunk of XStream({
          readableStream: messageStream,
        })) {
          const data = JSON.parse(chunk.data) as StreamResponseType['data'];
          const {
            type,
            // @ts-ignore
            delta,
            // @ts-ignore
            message,
            // @ts-ignore
            content_block,
            // @ts-ignore
            index = 0,
          } = data ?? {};

          if (type === 'message_start' && message?.response_message_id) {
            aiMessageId = message.response_message_id;
            userMessageId = message.input_message_id;

            // Create new messages object with minimal updates
            const newMessages: RawMessageType = {
              ...currentChat?.messages,
            };

            if (!message_id) {
              newMessages[userMessageId] = {
                content: {
                  0: {
                    type: MessageTypeEnum.TEXT,
                    text: content,
                  },
                },
                version_count: 1,
                version_index: 0,
                role: RoleEnum.USER,
                attachments,
              };
            }

            newMessages[aiMessageId] = {
              content: {},
              version_count: 1,
              version_index: 0,
              role: RoleEnum.ASSISTANT,
              attachments: [],
              loading: true,
            };

            currentChat = {
              ...currentChat,
              messages: newMessages,
            };

            // Immediate update for message start
            setActiveChat({ ...currentChat });
          }

          if (aiMessageId) {
            // Common message
            if (delta?.type === 'text_delta') {
              if (type === 'content_block_start') {
                contentByIndex[index] = {
                  type: 'text',
                  buffer: [],
                  startTime: Date.now(),
                };
                displayedLengths[index] = 0;
              } else if (type === 'content_block_delta') {
                if (!contentByIndex[index]) {
                  contentByIndex[index] = {
                    type: 'text',
                    buffer: [],
                    startTime: Date.now(),
                  };
                  displayedLengths[index] = 0;
                }
                contentByIndex[index].buffer.push(delta?.text || '');
              }
            }

            // Reason message
            if (
              content_block?.type === 'reasoning' ||
              delta?.type === 'reasoning_delta'
            ) {
              if (type === 'content_block_start') {
                contentByIndex[index] = {
                  type: 'reasoning',
                  buffer: [],
                  startTime: Date.now(),
                };
                displayedLengths[index] = 0;
              } else if (type === 'content_block_delta') {
                if (!contentByIndex[index]) {
                  contentByIndex[index] = {
                    type: 'reasoning',
                    buffer: [],
                    startTime: Date.now(),
                  };
                  displayedLengths[index] = 0;
                }
                contentByIndex[index].buffer.push(delta?.reasoning || '');
              }
            }

            // Handle errors
            if (
              type === 'message_delta' &&
              (delta?.stop_reason === 'error_or_unexpected_end' ||
                (delta?.stop_reason === 'message_stop' &&
                  delta?.error_msg?.length))
            ) {
              isStreamComplete = true;
              if (renderIntervalId) {
                clearInterval(renderIntervalId);
                renderIntervalId = null;
              }
              document.removeEventListener(
                'visibilitychange',
                handleVisibilityChange,
              );

              currentChat = {
                ...currentChat,
                status: ChatStatusEnum.READONLY,
                status_msg: delta?.error_msg,
                messages: omitKeys({
                  obj: currentChat?.messages || {},
                  keysToRemove: [aiMessageId],
                }),
              };
              setActiveChat({ ...currentChat });
              throw new Error(delta?.error_msg || 'Unknown error');
            }
          }
        }

        // Mark stream as complete
        isStreamComplete = true;

        // FIX: Clean up intervals and listeners FIRST (before final update)
        if (renderIntervalId) {
          clearInterval(renderIntervalId);
          renderIntervalId = null;
        }
        document.removeEventListener(
          'visibilitychange',
          handleVisibilityChange,
        );

        // Force render all remaining buffered content immediately
        const finalContentUpdates: Record<number, any> = {};
        Object.keys(contentByIndex).forEach((idx) => {
          const numIdx = Number(idx);
          const block = contentByIndex[numIdx];
          const fullBufferedContent = block.buffer.join('');

          if (block.type === 'text') {
            finalContentUpdates[numIdx] = {
              type: MessageTypeEnum.TEXT,
              text: fullBufferedContent,
            };
          } else if (block.type === 'reasoning') {
            finalContentUpdates[numIdx] = {
              type: MessageTypeEnum.REASONING,
              reasoning: fullBufferedContent,
            };
          }
        });

        // Apply final update with all content
        if (Object.keys(finalContentUpdates).length > 0) {
          // FIX: Create completely new object references to force React re-render
          const finalMessages = {
            ...currentChat!.messages,
            [aiMessageId]: {
              ...currentChat!.messages[aiMessageId],
              content: {
                ...currentChat!.messages[aiMessageId]?.content,
                ...finalContentUpdates,
              },
              loading: false,
            },
          };

          currentChat = {
            ...currentChat!,
            messages: finalMessages,
          };
          
          // Force a complete state update with new references
          setActiveChat({ ...currentChat! });
          
          // Use setTimeout to ensure the state update is flushed to React
          setTimeout(() => {
            setActiveChat({ 
              ...currentChat!,
            });
          }, 0);
        }

      } catch (streamError) {
        if (renderIntervalId) {
          clearInterval(renderIntervalId);
        }
        document.removeEventListener(
          'visibilitychange',
          handleVisibilityChange,
        );
        throw streamError;
      }

      // Final update to ensure everything is synced
      setActiveChat({ ...currentChat });

      // Update title if needed (only for new chats)
      if (Object.keys(currentChat?.messages || {})?.length <= 2) {
        const { title } = await getChat({
          id: currentChat?.chat_id as string,
        });

        if (title !== currentChat?.title) {
          const updatedChat = { ...currentChat, title };
          setActiveChat(updatedChat);
          if (setChats) {
            setChats(
              prevChats.map((item) => ({
                ...item,
                ...(item.chat_id === currentChat?.chat_id && { title }),
              })),
            );
          }
        }
      }
    }
  } catch (e) {
    handleError(e);
    if (activeChat?.chat_id) {
      const getChatData = await getChat({
        id: activeChat?.chat_id as string,
      });
      setActiveChat({
        ...getChatData,
        active: true,
      });
    }
    throw e;
  } finally {
    setAiTyping(false);
  }
};
