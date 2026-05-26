import React, { createRef } from 'react';
import { screen, waitFor } from '@testing-library/react';
import { TextAreaRef } from 'antd/es/input/TextArea';
import '@testing-library/jest-dom';

import { RoleEnum } from '@shared/ui/enums/chats.enums';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';

// Mock external dependencies
const mockMessageSuccess = jest.fn();

jest.mock('@shared/ui/components/molecules/Chat/Bubbles/UserBubble', () => ({
  __esModule: true,
  default: jest.fn(({ bubble, user }: any) => (
    <div data-testid='user-bubble' data-user-email={user?.email}>
      {bubble.content[0]?.text}
    </div>
  )),
}));

jest.mock('@shared/ui/components/molecules/Chat/Bubbles/FileBubble', () => ({
  __esModule: true,
  default: jest.fn(({ bubble }: any) => (
    <div data-testid='file-bubble'>
      {bubble.content?.map((file: any) => (
        <div key={file.uid} data-testid='file-item'>
          {file.name}
        </div>
      ))}
    </div>
  )),
}));

jest.mock(
  '@shared/ui/components/molecules/Chat/Bubbles/AssistantBubble',
  () => ({
    __esModule: true,
    default: jest.fn(({ bubble, isLastMessage, aiTyping }: any) => (
      <div
        data-testid='assistant-bubble'
        data-is-last={isLastMessage}
        data-ai-typing={aiTyping}
      >
        {bubble.content[0]?.text}
      </div>
    )),
  }),
);

jest.mock('@shared/ui/components/molecules/Chat/Bubbles/ErrorBubble', () => ({
  __esModule: true,
  default: jest.fn(({ bubble }: any) => (
    <div data-testid='error-bubble'>{bubble.content}</div>
  )),
}));

jest.mock('@shared/ui/components/molecules/Chat/Bubbles/DefaultBubble', () => ({
  __esModule: true,
  default: jest.fn(({ bubble }: any) => (
    <div data-testid='default-bubble'>{bubble.content}</div>
  )),
}));

jest.mock('@ant-design/icons', () => ({
  RedoOutlined: jest.fn(({ spin }: any) => (
    <div data-testid='redo-icon' data-spin={spin}>
      ↻
    </div>
  )),
}));

jest.mock('react-infinite-scroll-component', () => {
  return jest.fn(
    ({ children, loader, hasMore, inverse, scrollableTarget }: any) => (
      <div
        data-testid='infinite-scroll'
        data-has-more={hasMore}
        data-inverse={inverse}
        data-scrollable-target={scrollableTarget}
      >
        {children}
        {hasMore && <div data-testid='loader'>{loader}</div>}
      </div>
    ),
  );
});

jest.mock(
  '@shared/ui/components/molecules/Chat/MessagesBlock/MessagesBlock.styled',
  () => ({
    StyledMessagesBlock: React.forwardRef(
      (
        {
          children,
          className,
          $collapsedSidebar,
          $customHeight,
          id,
          ...props
        }: any,
        ref,
      ) => (
        <div
          ref={ref}
          id={id}
          className={className}
          data-testid='messages-block'
          data-collapsed={$collapsedSidebar}
          data-custom-height={$customHeight}
          {...props}
        >
          {children}
        </div>
      ),
    ),
    StyledMessagesList: ({ children, ...props }: any) => (
      <div data-testid='messages-list' {...props}>
        {children}
      </div>
    ),
  }),
);

jest.mock('antd', () => ({
  App: {
    useApp: jest.fn(() => ({ message: { success: mockMessageSuccess } })),
  },
  Spin: ({ indicator, size }: any) => (
    <div data-testid='spin' data-size={size}>
      {indicator}
    </div>
  ),
}));

import MessagesBlock from '@shared/ui/components/molecules/Chat/MessagesBlock';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

describe('MessagesBlock', () => {
  const defaultStore = mockStore({
    settings: {
      collapsedSidebar: false,
      user: { email: 'test@example.com' },
    },
    chats: {
      aiTyping: false,
      hasMoreMessages: false,
    },
  });

  const mockOnLoadMore = jest.fn();
  const mockComponentRef = createRef<any>();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders correctly with no items', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('messages-block')).toBeInTheDocument();
      expect(screen.getByTestId('infinite-scroll')).toBeInTheDocument();
      expect(screen.getByTestId('messages-list')).toBeInTheDocument();
    });

    it('applies custom className', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          className='custom'
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('messages-block')).toHaveClass(
        'message-block',
        'custom',
      );
    });

    it('applies custom height', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          customHeight='500px'
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('messages-block')).toHaveAttribute(
        'data-custom-height',
        '500px',
      );
    });

    it('uses default height when not provided', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('messages-block')).toHaveAttribute(
        'data-custom-height',
        'calc(100vh - 64px - 96px - 72px - 3.2rem)',
      );
    });

    it('handles collapsed sidebar state', () => {
      const collapsedStore = mockStore({
        settings: {
          collapsedSidebar: true,
          user: { email: 'test@example.com' },
        },
        chats: {
          aiTyping: false,
          hasMoreMessages: false,
        },
      });

      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: collapsedStore },
      );

      expect(screen.getByTestId('messages-block')).toHaveAttribute(
        'data-collapsed',
        'true',
      );
    });
  });

  describe('User Messages', () => {
    it('renders user message bubble', () => {
      const userMessage = {
        key: 'user-1',
        role: RoleEnum.USER,
        content: {
          0: { type: MessageTypeEnum.TEXT, text: 'Hello' },
        },
        edit: false,
        refInput: createRef<TextAreaRef>(),
        version_count: 1,
        version_index: 0,
        showEditBtn: true,
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={[userMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('user-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('user-bubble')).toHaveAttribute(
        'data-user-email',
        'test@example.com',
      );
      expect(screen.getByTestId('user-bubble')).toHaveTextContent('Hello');
    });
  });

  describe('Assistant Messages', () => {
    it('renders assistant message bubble', () => {
      const assistantMessage = {
        key: 'ai-1',
        role: RoleEnum.ASSISTANT,
        content: {
          0: { type: MessageTypeEnum.TEXT, text: 'AI response' },
        },
        version_count: 1,
        version_index: 0,
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={[assistantMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('assistant-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('assistant-bubble')).toHaveTextContent(
        'AI response',
      );
      expect(screen.getByTestId('assistant-bubble')).toHaveAttribute(
        'data-is-last',
        'true',
      );
      expect(screen.getByTestId('assistant-bubble')).toHaveAttribute(
        'data-ai-typing',
        'false',
      );
    });

    it('passes aiTyping state to last assistant message', () => {
      const storeWithTyping = mockStore({
        settings: {
          collapsedSidebar: false,
          user: { email: 'test@example.com' },
        },
        chats: {
          aiTyping: true,
          hasMoreMessages: false,
        },
      });

      const assistantMessage = {
        key: 'ai-1',
        role: RoleEnum.ASSISTANT,
        content: {
          0: { type: MessageTypeEnum.TEXT, text: 'AI response' },
        },
        version_count: 1,
        version_index: 0,
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={[assistantMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: storeWithTyping },
      );

      expect(screen.getByTestId('assistant-bubble')).toHaveAttribute(
        'data-ai-typing',
        'true',
      );
    });

    it('does not pass aiTyping to non-last assistant messages', () => {
      const storeWithTyping = mockStore({
        settings: {
          collapsedSidebar: false,
          user: { email: 'test@example.com' },
        },
        chats: {
          aiTyping: true,
          hasMoreMessages: false,
        },
      });

      const messages = [
        {
          key: 'ai-1',
          role: RoleEnum.ASSISTANT,
          content: {
            0: { type: MessageTypeEnum.TEXT, text: 'First AI response' },
          },
          version_count: 1,
          version_index: 0,
        },
        {
          key: 'ai-2',
          role: RoleEnum.ASSISTANT,
          content: {
            0: { type: MessageTypeEnum.TEXT, text: 'Second AI response' },
          },
          version_count: 1,
          version_index: 0,
        },
      ];

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={messages}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: storeWithTyping },
      );

      const bubbles = screen.getAllByTestId('assistant-bubble');
      expect(bubbles[0]).toHaveAttribute('data-is-last', 'false');
      expect(bubbles[0]).toHaveAttribute('data-ai-typing', 'true');
      expect(bubbles[1]).toHaveAttribute('data-is-last', 'true');
      expect(bubbles[1]).toHaveAttribute('data-ai-typing', 'true');
    });
  });

  describe('File Messages', () => {
    it('renders file message bubble', () => {
      const fileMessage = {
        key: 'file-1',
        role: 'fileUser',
        content: [
          { uid: '1', name: 'file.pdf', url: 'http://example.com/file.pdf' },
          {
            uid: '2',
            name: 'image.jpg',
            thumbUrl: 'http://example.com/image.jpg',
          },
        ],
        version_count: 1,
        version_index: 0,
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={[fileMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('file-bubble')).toBeInTheDocument();
      const fileItems = screen.getAllByTestId('file-item');
      expect(fileItems).toHaveLength(2);
      expect(fileItems[0]).toHaveTextContent('file.pdf');
      expect(fileItems[1]).toHaveTextContent('image.jpg');
    });
  });

  describe('Error Messages', () => {
    it('renders error message bubble', () => {
      const errorMessage = {
        key: 'error-1',
        role: 'error',
        content: 'Something went wrong',
        loading: false,
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={[errorMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('error-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('error-bubble')).toHaveTextContent(
        'Something went wrong',
      );
    });
  });

  describe('Multiple Messages', () => {
    it('handles multiple message types in sequence', () => {
      const items = [
        {
          key: '1',
          role: RoleEnum.USER,
          content: { 0: { type: MessageTypeEnum.TEXT, text: 'User message' } },
          edit: false,
          refInput: createRef<TextAreaRef>(),
        },
        {
          key: '2',
          role: RoleEnum.ASSISTANT,
          content: { 0: { type: MessageTypeEnum.TEXT, text: 'AI response' } },
        },
        {
          key: '3',
          role: 'fileUser',
          content: [{ uid: '1', name: 'file.pdf' }],
        },
      ];

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          items={items}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('user-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('assistant-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('file-bubble')).toBeInTheDocument();
    });
  });

  describe('Infinite Scroll', () => {
    it('shows loader when hasMoreMessages is true and not loading', () => {
      const storeWithMore = mockStore({
        settings: {
          collapsedSidebar: false,
          user: { email: 'test@example.com' },
        },
        chats: {
          aiTyping: false,
          hasMoreMessages: true,
        },
      });

      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: storeWithMore },
      );

      expect(screen.getByTestId('loader')).toBeInTheDocument();
      expect(screen.getByTestId('spin')).toBeInTheDocument();
      expect(screen.getByTestId('redo-icon')).toBeInTheDocument();
      expect(screen.getByTestId('redo-icon')).toHaveAttribute(
        'data-spin',
        'true',
      );
    });

    it('does not show loader when isLoading is true', () => {
      const storeWithMore = mockStore({
        settings: {
          collapsedSidebar: false,
          user: { email: 'test@example.com' },
        },
        chats: {
          aiTyping: false,
          hasMoreMessages: true,
        },
      });

      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={true}
          componentRef={mockComponentRef}
        />,
        { store: storeWithMore },
      );

      expect(screen.queryByTestId('loader')).not.toBeInTheDocument();
    });

    it('passes inverse prop to InfiniteScroll', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('infinite-scroll')).toHaveAttribute(
        'data-inverse',
        'true',
      );
    });

    it('passes scrollableTarget to InfiniteScroll', () => {
      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('infinite-scroll')).toHaveAttribute(
        'data-scrollable-target',
        'message-block',
      );
    });
  });

  describe('Fallback Rendering', () => {
    it('renders default bubble when role is not recognized', () => {
      const unknownMessage = {
        key: 'unknown-1',
        role: 'unknown',
        content: 'Some content',
        variant: 'shadow',
      };

      renderLayout(
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          // @ts-ignore
          items={[unknownMessage]}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      expect(screen.getByTestId('default-bubble')).toBeInTheDocument();
      expect(screen.getByTestId('default-bubble')).toHaveTextContent(
        'Some content',
      );
    });
  });

  describe('Component Ref', () => {
    it('exposes scrollBottom method through ref', async () => {
      jest.useFakeTimers();

      renderLayout(
        // @ts-ignore
        <MessagesBlock
          onLoadMore={mockOnLoadMore}
          isLoading={false}
          componentRef={mockComponentRef}
        />,
        { store: defaultStore },
      );

      await waitFor(() => {
        expect(mockComponentRef.current).toBeTruthy();
      });

      expect(mockComponentRef.current).toHaveProperty('scrollBottom');
      expect(typeof mockComponentRef.current.scrollBottom).toBe('function');

      jest.useRealTimers();
    });
  });
});
