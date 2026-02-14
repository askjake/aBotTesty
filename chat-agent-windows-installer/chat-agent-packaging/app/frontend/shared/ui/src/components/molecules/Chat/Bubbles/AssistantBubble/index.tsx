import { memo, useMemo } from 'react';
import { Avatar } from 'antd';
import { BsRobot } from 'react-icons/bs';
import XMarkdown, { type ComponentProps } from '@ant-design/x-markdown';
import Latex from '@ant-design/x-markdown/plugins/Latex';

import MessageCode from '@shared/ui/components/molecules/Chat/MessageRender/MessageCode';
import MessageThinking from '@shared/ui/components/molecules/Chat/MessageRender/MessageThinking';
import CustomBubble from '@shared/ui/components/atoms/Bubbles/CustomBubble';

import { RoleEnum } from '@shared/ui/enums/chats.enums';
import { RawMessageType } from '@shared/ui/types/messages.types';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Custom link component for artifact downloads
const MessageLink: React.FC<ComponentProps> = (props) => {
  const { href, children } = props;
  const hrefStr = typeof href === 'string' ? href : undefined;
  
  // Check if this is an artifact download link
  const isArtifactLink = hrefStr?.startsWith('/rest/api/v1/agent-mode/artifacts/');
  
  return (
    <a
      href={hrefStr}
      target={isArtifactLink ? '_blank' : undefined}
      rel={isArtifactLink ? 'noopener noreferrer' : undefined}
      style={{
        color: '#1890ff',
        textDecoration: 'underline',
        cursor: 'pointer',
      }}
    >
      {children}
    </a>
  );
};

const AssistantBubble = memo(
  ({
    bubble,
    isLastMessage,
    aiTyping,
  }: {
    bubble: any;
    isLastMessage: boolean;
    aiTyping: boolean;
  }) => {
    const { content = {}, loading } = bubble;

    const markdownContent = useMemo(() => {
      return Object.values(content as RawMessageType[string]['content'])
        .map(({ type, reasoning = '', text = '' }) => {
          if (type === MessageTypeEnum.REASONING) {
            const sanitizedReasoning = reasoning.replace(/\n/g, '<br/>');
            return sanitizedReasoning
              ? `<think>${sanitizedReasoning}</think>`
              : '';
          }
          return text;
        })
        .join('\n');
    }, [content]);

    const isThinkingLoading = isLastMessage && aiTyping;

    const thinkComponent = useMemo(
      () => (props: ComponentProps) => (
        <MessageThinking loading={isThinkingLoading} {...props} />
      ),
      [isThinkingLoading],
    );

    return (
      <CustomBubble
        role={RoleEnum.ASSISTANT}
        placement='start'
        shape='corner'
        loading={loading}
        avatar={<Avatar icon={<BsRobot />} />}
        content={content[0]?.text || ''}
        contentRender={() => (
          <XMarkdown
            components={{
              code: MessageCode,
              think: thinkComponent,
              a: MessageLink,
            }}
            paragraphTag='div'
            streaming={{
              hasNextChunk: aiTyping,
              enableAnimation: true,
            }}
            config={{ extensions: Latex() }}
          >
            {markdownContent}
          </XMarkdown>
        )}
      />
    );
  },
  (oldProps, newProps) => {
    // Only re-render if content changes or if it's the last message and aiTyping changes
    const contentChanged = oldProps.bubble.content !== newProps.bubble.content;
    const loadingChanged = oldProps.bubble.loading !== newProps.bubble.loading;
    const isLastMessageChanged =
      oldProps.isLastMessage !== newProps.isLastMessage;
    const aiTypingChanged =
      oldProps.isLastMessage &&
      newProps.isLastMessage &&
      oldProps.aiTyping !== newProps.aiTyping;

    return !(
      contentChanged ||
      loadingChanged ||
      isLastMessageChanged ||
      aiTypingChanged
    );
  },
);

export default AssistantBubble;
