import { act, renderHook } from '@testing-library/react';
import { getChat, getChats } from '@shared/ui/services/chats.services';
import { getMessages } from '@shared/ui/services/messages.services';
import { DeepPartial } from '@shared/ui/types/common.types';
import { RootStore } from '@shared/ui/types/store.types';
import { ChatType } from '@shared/ui/types/chats.types';
import { RawMessageType } from '@shared/ui/types/messages.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import useRefetchChats from '@/hooks/useRefetchChats';
import React from 'react';
import {
  CHAT_MESSAGES_PAGE_SIZE,
  CHATS_PAGE_SIZE,
} from '@shared/ui/constants/common.constants';

jest.mock('@shared/ui/services/chats.services');
jest.mock('@shared/ui/services/messages.services');

const mockGetChats = getChats as jest.MockedFunction<typeof getChats>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;

describe('useRefetchChats', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderUseRefetchChats = (initialState: DeepPartial<RootStore> = {}) => {
    const store = mockStore(initialState);
    const dispatchSpy = jest.spyOn(store, 'dispatch');

    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Provider } = require('react-redux');
    const Wrapper = ({ children }: { children: React.ReactNode }) =>
      React.createElement(Provider, { store }, children);

    const hookResult = renderHook(() => useRefetchChats(), {
      wrapper: Wrapper,
    });

    return { ...hookResult, store, dispatchSpy };
  };

  const createMockChat = (overrides: Partial<ChatType> = {}): ChatType => ({
    chat_id: '1',
    title: 'Test Chat',
    created_at: '2023-01-01T00:00:00Z',
    owner_id: 'user_1',
    last_message_at: '2023-01-01T00:00:00Z',
    vault_mode: false,
    messages: {},
    active: false,
    favorite: false,
    group_id: null,
    status: ChatStatusEnum.NORMAL,
    status_msg: null,
    ...overrides,
  });

  const createMockMessages = (): RawMessageType => ({
    msg_1: {
      content: {
        0: {
          type: MessageTypeEnum.TEXT,
          text: 'Hello world',
        },
      },
      role: RoleEnum.USER,
      version_count: 1,
      version_index: 0,
      created_at: '2023-01-01T00:00:00Z',
      attachments: [],
    },
  });

  const createMockPaginationResponse = (overrides: any = {}) => ({
    docs: [],
    totalDocs: 0,
    limit: 25,
    page: 1,
    totalPages: 0,
    hasNextPage: false,
    hasPrevPage: false,
    nextPage: 1,
    prevPage: 0,
    pagingCounter: 1,
    active_chat_id: null,
    ...overrides,
  });

  const createMockMessagesResponse = (overrides: any = {}) => ({
    docs: [],
    totalDocs: 0,
    limit: 25,
    page: 1,
    totalPages: 0,
    hasNextPage: false,
    hasPrevPage: false,
    nextPage: 1,
    prevPage: 0,
    pagingCounter: 1,
    ...overrides,
  });

  describe('refetchChats function', () => {
    it('should return refetchChats function', () => {
      const { result } = renderUseRefetchChats();
      expect(result.current).toHaveProperty('refetchChats');
      expect(typeof result.current.refetchChats).toBe('function');
    });

    it('should handle empty API response', async () => {
      mockGetChats.mockResolvedValue(createMockPaginationResponse());

      const { result, dispatchSpy } = renderUseRefetchChats();
      await result.current.refetchChats();

      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 25,
        group_id: 'all',
      });
      expect(dispatchSpy).toHaveBeenCalledTimes(3);
    });

    it('should process chats data correctly', async () => {
      const mockResponse = createMockPaginationResponse({
        docs: [
          createMockChat({ chat_id: '1', title: 'Chat 1' }),
          createMockChat({ chat_id: '2', title: 'Chat 2' }),
        ],
        hasNextPage: true,
        active_chat_id: '2',
        totalDocs: 10,
      });

      mockGetChats.mockResolvedValue(mockResponse);

      // Mock getChat since active_chat_id is '2'
      mockGetChat.mockResolvedValue({
        messages: {},
        chat_id: '2',
        title: 'Chat 2',
        vault_mode: false,
        created_at: '2023-01-01T00:00:00Z',
        owner_id: 'user_1',
        last_message_at: '2023-01-01T00:00:00Z',
        active: false,
        favorite: false,
        group_id: null,
        status: ChatStatusEnum.NORMAL,
        status_msg: null,
      });

      // Mock getMessages
      mockGetMessages.mockResolvedValue(
        createMockMessagesResponse({
          docs: [
            {
              message_id: 'msg_1',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'Hello',
                },
              },
              role: RoleEnum.USER,
              version_count: 1,
              version_index: 0,
              attachments: [],
            },
          ],
          hasNextPage: false,
        }),
      );

      const { result, dispatchSpy } = renderUseRefetchChats();

      await act(async () => {
        await result.current.refetchChats();
      });

      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: CHATS_PAGE_SIZE,
        group_id: 'all',
      });

      expect(mockGetMessages).toHaveBeenCalledWith({
        chat_id: '2',
        page: 1,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });

      const setChatsCall = dispatchSpy.mock.calls.find(
        (call) => call[0].type === 'chats/setChats',
      );

      expect(setChatsCall?.[0].payload).toEqual([
        expect.objectContaining({ chat_id: '1', active: false }),
        expect.objectContaining({ chat_id: '2', active: true }),
      ]);
    });

    it('should not fetch active chat when no active_chat_id', async () => {
      mockGetChats.mockResolvedValue(
        createMockPaginationResponse({
          docs: [createMockChat()],
          active_chat_id: null,
        }),
      );

      const { result, dispatchSpy } = renderUseRefetchChats();
      await result.current.refetchChats();

      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 25,
        group_id: 'all',
      });
      expect(mockGetChat).not.toHaveBeenCalled();
      expect(mockGetMessages).not.toHaveBeenCalled();
      expect(dispatchSpy).toHaveBeenCalledTimes(3);
    });

    it('should fetch active chat when active_chat_id provided', async () => {
      mockGetChats.mockResolvedValue(
        createMockPaginationResponse({
          docs: [],
          active_chat_id: '1',
        }),
      );

      mockGetChat.mockResolvedValue({
        messages: {},
        chat_id: '1',
        title: 'Active Chat',
        vault_mode: false,
        created_at: '2023-01-01T00:00:00Z',
        owner_id: 'user_1',
        last_message_at: '2023-01-01T00:00:00Z',
        active: false,
        favorite: false,
        group_id: null,
        status: ChatStatusEnum.NORMAL,
        status_msg: null,
      });

      mockGetMessages.mockResolvedValue(
        createMockMessagesResponse({
          docs: [
            {
              message_id: 'msg_1',
              content: {
                0: {
                  type: MessageTypeEnum.TEXT,
                  text: 'Hello world',
                },
              },
              role: RoleEnum.USER,
              version_count: 1,
              version_index: 0,
              attachments: [],
            },
          ],
          hasNextPage: false,
        }),
      );

      const { result, dispatchSpy } = renderUseRefetchChats();
      await result.current.refetchChats();

      expect(mockGetChats).toHaveBeenCalledWith({
        page: 1,
        limit: 25,
        group_id: 'all',
      });
      expect(mockGetChat).toHaveBeenCalledWith({ id: '1' });
      expect(mockGetMessages).toHaveBeenCalledWith({
        chat_id: '1',
        page: 1,
        limit: CHAT_MESSAGES_PAGE_SIZE,
      });
      expect(dispatchSpy).toHaveBeenCalledTimes(5); // setChats, setHasMoreChats, setTotalChats, setActiveChat, setHasMoreMessages

      const setActiveChatCall = dispatchSpy.mock.calls.find(
        (call) => call[0].type === 'chats/setActiveChat',
      );

      expect(setActiveChatCall?.[0].payload).toEqual(
        expect.objectContaining({
          chat_id: '1',
          active: true,
        }),
      );
    });

    describe('vault mode handling', () => {
      it('should include messages when vault_mode is false', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockResolvedValue({
          messages: {},
          chat_id: '1',
          vault_mode: false,
          title: 'Test Chat',
          created_at: '2023-01-01T00:00:00Z',
          owner_id: 'user_1',
          last_message_at: '2023-01-01T00:00:00Z',
          active: false,
          favorite: false,
          group_id: null,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
        });

        mockGetMessages.mockResolvedValue(
          createMockMessagesResponse({
            docs: [
              {
                message_id: 'msg_1',
                content: {
                  0: {
                    type: MessageTypeEnum.TEXT,
                    text: 'Hello world',
                  },
                },
                role: RoleEnum.USER,
                version_count: 1,
                version_index: 0,
                attachments: [],
              },
            ],
            hasNextPage: false,
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats({
          chats: { vaultMode: false, vaultModeRegistered: false },
        });

        await result.current.refetchChats();

        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 25,
          group_id: 'all',
        });

        const setActiveChatCall = dispatchSpy.mock.calls.find(
          (call) => call[0].type === 'chats/setActiveChat',
        );

        // @ts-ignore
        expect(setActiveChatCall?.[0]?.payload?.messages).toEqual({
          msg_1: expect.objectContaining({
            content: {
              0: {
                type: MessageTypeEnum.TEXT,
                text: 'Hello world',
              },
            },
            role: RoleEnum.USER,
          }),
        });
      });

      it('should include messages when vault access granted', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockResolvedValue({
          messages: {},
          chat_id: '1',
          vault_mode: true,
          title: 'Test Chat',
          created_at: '2023-01-01T00:00:00Z',
          owner_id: 'user_1',
          last_message_at: '2023-01-01T00:00:00Z',
          active: false,
          favorite: false,
          group_id: null,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
        });

        mockGetMessages.mockResolvedValue(
          createMockMessagesResponse({
            docs: [
              {
                message_id: 'msg_1',
                content: {
                  0: {
                    type: MessageTypeEnum.TEXT,
                    text: 'Hello world',
                  },
                },
                role: RoleEnum.USER,
                version_count: 1,
                version_index: 0,
                attachments: [],
              },
            ],
            hasNextPage: false,
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats({
          chats: { vaultMode: true, vaultModeRegistered: true },
        });

        await result.current.refetchChats();

        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 25,
          group_id: 'all',
        });

        const setActiveChatCall = dispatchSpy.mock.calls.find(
          (call) => call[0].type === 'chats/setActiveChat',
        );
        // @ts-ignore
        expect(setActiveChatCall?.[0]?.payload?.messages).toEqual({
          msg_1: expect.objectContaining({
            content: {
              0: {
                type: MessageTypeEnum.TEXT,
                text: 'Hello world',
              },
            },
            role: RoleEnum.USER,
          }),
        });
      });

      it('should exclude messages when vault access denied', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockResolvedValue({
          messages: {},
          chat_id: '1',
          vault_mode: true,
          title: 'Test Chat',
          created_at: '2023-01-01T00:00:00Z',
          owner_id: 'user_1',
          last_message_at: '2023-01-01T00:00:00Z',
          active: false,
          favorite: false,
          group_id: null,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
        });

        mockGetMessages.mockResolvedValue(
          createMockMessagesResponse({
            docs: [
              {
                message_id: 'msg_1',
                content: {
                  0: {
                    type: MessageTypeEnum.TEXT,
                    text: 'Hello world',
                  },
                },
                role: RoleEnum.USER,
                version_count: 1,
                version_index: 0,
                attachments: [],
              },
            ],
            hasNextPage: false,
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats({
          chats: { vaultMode: false, vaultModeRegistered: false },
        });

        await result.current.refetchChats();

        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 25,
          group_id: 'all',
        });

        const setActiveChatCall = dispatchSpy.mock.calls.find(
          (call) => call[0].type === 'chats/setActiveChat',
        );
        // @ts-ignore
        expect(setActiveChatCall?.[0]?.payload?.messages).toEqual({});
      });
    });

    describe('error handling', () => {
      it('should handle getChats errors', async () => {
        mockGetChats.mockRejectedValue(new Error('API Error'));

        const { result } = renderUseRefetchChats();

        await expect(result.current.refetchChats()).rejects.toThrow(
          'API Error',
        );
      });

      it('should handle getChat errors', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockRejectedValue(new Error('Chat not found'));

        const { result } = renderUseRefetchChats();

        await expect(result.current.refetchChats()).rejects.toThrow(
          'Chat not found',
        );
      });

      it('should handle getMessages errors', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockResolvedValue(createMockChat({ chat_id: '1' }));
        mockGetMessages.mockRejectedValue(new Error('Messages not found'));

        const { result } = renderUseRefetchChats();

        await expect(result.current.refetchChats()).rejects.toThrow(
          'Messages not found',
        );
      });
    });

    describe('edge cases', () => {
      it('should handle undefined active_chat_id', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [createMockChat()],
            active_chat_id: undefined,
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats();
        await result.current.refetchChats();

        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 25,
          group_id: 'all',
        });
        expect(mockGetChat).not.toHaveBeenCalled();
        expect(mockGetMessages).not.toHaveBeenCalled();
        expect(dispatchSpy).toHaveBeenCalledTimes(3);
      });

      it('should handle empty string active_chat_id', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [createMockChat()],
            active_chat_id: '',
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats();
        await result.current.refetchChats();

        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 25,
          group_id: 'all',
        });
        expect(mockGetChat).not.toHaveBeenCalled();
        expect(mockGetMessages).not.toHaveBeenCalled();
        expect(dispatchSpy).toHaveBeenCalledTimes(3);
      });

      it('should handle empty messages array', async () => {
        mockGetChats.mockResolvedValue(
          createMockPaginationResponse({
            docs: [],
            active_chat_id: '1',
          }),
        );

        mockGetChat.mockResolvedValue(createMockChat({ chat_id: '1' }));
        mockGetMessages.mockResolvedValue(
          createMockMessagesResponse({
            docs: [],
            hasNextPage: false,
          }),
        );

        const { result, dispatchSpy } = renderUseRefetchChats();
        await result.current.refetchChats();

        const setActiveChatCall = dispatchSpy.mock.calls.find(
          (call) => call[0].type === 'chats/setActiveChat',
        );

        // @ts-ignore
        expect(setActiveChatCall?.[0]?.payload?.messages).toEqual({});
      });
    });
  });
});
