import { FC, useEffect, useImperativeHandle, useMemo, useRef } from 'react';
import { Spin } from 'antd';
import { RedoOutlined } from '@ant-design/icons';
import InfiniteScroll from 'react-infinite-scroll-component';

import { useAppSelector } from '@shared/ui/store';

import {
  StyledMessagesBlock,
  StyledMessagesList,
} from '@shared/ui/components/molecules/Chat/MessagesBlock/MessagesBlock.styled';
import UserBubble from '@shared/ui/components/molecules/Chat/Bubbles/UserBubble';
import FileBubble from '@shared/ui/components/molecules/Chat/Bubbles/FileBubble';
import AssistantBubble from '@shared/ui/components/molecules/Chat/Bubbles/AssistantBubble';
import DefaultBubble from '@shared/ui/components/molecules/Chat/Bubbles/DefaultBubble';
import ErrorBubble from '@shared/ui/components/molecules/Chat/Bubbles/ErrorBubble';

import { MessagesBlockProps } from '@shared/ui/components/molecules/Chat/MessagesBlock/MessagesBlock.props';
import { RenderUserMessagesResultType } from '@shared/ui/types/messages.types';
import { RoleEnum } from '@shared/ui/enums/chats.enums';

const MessagesBlock: FC<MessagesBlockProps> = ({
  className = '',
  items = [],
  onLoadMore,
  customHeight = 'calc(100vh - 64px - 96px - 72px - 3.2rem)',
  isLoading = false,
  componentRef,
  ...props
}) => {
  const user = useAppSelector((store) => store.settings.user);
  const collapsedSidebar = useAppSelector(
    (store) => store.settings.collapsedSidebar,
  );
  const aiTyping = useAppSelector((store) => store.chats.aiTyping);
  const hasMoreMessages = useAppSelector(
    (store) => store.chats.hasMoreMessages,
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const previousItemsLength = useRef(items.length);
  const previousScrollHeight = useRef(0);

  useImperativeHandle(
    componentRef,
    () => ({
      scrollBottom: () => {
        const timer = setTimeout(() => {
          containerRef?.current?.scrollTo({
            top: 0,
            behavior: 'smooth',
          });
          clearTimeout(timer);
        }, 250);
      },
    }),
    [],
  );

  // Preserve scroll position when new messages are loaded
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // If items increased (new messages loaded at the top)
    if (items.length > previousItemsLength.current) {
      const currentScrollHeight = container.scrollHeight;
      const scrollHeightDiff =
        currentScrollHeight - previousScrollHeight.current;

      // Adjust scroll position to maintain visual position
      if (scrollHeightDiff > 0) {
        container.scrollTop = container.scrollTop + scrollHeightDiff;
      }
    }

    // Update refs
    previousItemsLength.current = items.length;
    previousScrollHeight.current = container.scrollHeight;
  }, [items.length]);

  const handleLoadMore = () => {
    const container = containerRef.current;
    if (container) {
      // Store current scroll height before loading
      previousScrollHeight.current = container.scrollHeight;
    }
    onLoadMore();
  };

  // Main render function
  const renderBubbles = useMemo(() => {
    return items.map((bubble, index) => {
      // Use bubble.key or a stable identifier instead of index if possible
      const bubbleKey = bubble.key || `${bubble.role}-${index}`;

      const isLastMessage = index === items.length - 1;

      if (bubble.role === RoleEnum.USER) {
        return (
          <UserBubble
            key={bubbleKey}
            bubble={bubble as RenderUserMessagesResultType}
            user={user}
          />
        );
      } else if (bubble.role === 'fileUser') {
        return <FileBubble key={bubbleKey} bubble={bubble} />;
      } else if (bubble.role === RoleEnum.ASSISTANT) {
        return (
          <AssistantBubble
            key={bubbleKey}
            bubble={bubble}
            isLastMessage={isLastMessage}
            aiTyping={aiTyping}
          />
        );
      } else if (bubble.role === 'error') {
        return <ErrorBubble key={bubbleKey} bubble={bubble} />;
      }
      return <DefaultBubble key={bubbleKey} bubble={bubble} />;
    });
  }, [items, user?.email, aiTyping]);

  return (
    <StyledMessagesBlock
      id='message-block'
      className={`message-block ${className}`}
      ref={containerRef}
      $collapsedSidebar={collapsedSidebar}
      $customHeight={customHeight}
      {...props}
    >
      <InfiniteScroll
        dataLength={items.length}
        next={handleLoadMore}
        hasMore={hasMoreMessages && !isLoading}
        inverse={true}
        style={{ display: 'flex', flexDirection: 'column-reverse' }}
        loader={
          <div style={{ textAlign: 'center' }}>
            <Spin indicator={<RedoOutlined spin />} size='small' />
          </div>
        }
        scrollableTarget='message-block'
      >
        <StyledMessagesList>{renderBubbles}</StyledMessagesList>
      </InfiniteScroll>
    </StyledMessagesBlock>
  );
};

export default MessagesBlock;
