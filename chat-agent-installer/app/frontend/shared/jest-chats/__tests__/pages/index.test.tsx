import React from 'react';
import { screen } from '@testing-library/react';
import { GetServerSidePropsContext } from 'next';
import HomePage, { getServerSideProps } from '@/pages/index';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import { getChat, getChats } from '@shared/ui/services/chats.services';
import { getMessages } from '@shared/ui/services/messages.services';
import { getChatsGroups } from '@/services/chatGroup.service';
import { updateLastReleaseDate } from '@shared/ui/services/releases.services';
import { fetchUserData } from '@/utils/requests.utils';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { handleServerError } from '@shared/ui/utils/errors.utils';
import { transformMessagesToObject } from '@shared/ui/utils/messages.utils';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock Next.js Head component
jest.mock('next/head', () => {
  return function Head({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

// Mock HomeTemplate component
jest.mock('@/components/templates/HomeTemplate', () => {
  return function HomeTemplate() {
    return <div data-testid='home-template'>Home Template</div>;
  };
});

// Mock services
jest.mock('@shared/ui/services/chats.services', () => ({
  getChats: jest.fn(),
  getChat: jest.fn(),
}));

jest.mock('@shared/ui/services/messages.services', () => ({
  getMessages: jest.fn(),
}));

jest.mock('@/services/chatGroup.service', () => ({
  getChatsGroups: jest.fn(),
}));

jest.mock('@shared/ui/services/releases.services', () => ({
  updateLastReleaseDate: jest.fn(),
}));

jest.mock('@/utils/requests.utils', () => ({
  fetchUserData: jest.fn(),
}));

jest.mock('@shared/ui/utils/errors.utils', () => ({
  handleServerError: jest.fn(),
}));

jest.mock('@shared/ui/utils/messages.utils', () => ({
  transformMessagesToObject: jest.fn(),
}));

jest.mock('@shared/ui/libs/dayjs.libs', () => jest.fn());

// Mock constants
jest.mock('@shared/ui/constants/common.constants', () => ({
  CHATS_PAGE_SIZE: 15,
  CHAT_GROUPS_PAGE_SIZE: 50,
  CHAT_MESSAGES_PAGE_SIZE: 20,
}));

// Mock Redux wrapper with a store instance that we can access
let testStore: any = null;

jest.mock('@shared/ui/store', () => ({
  wrapper: {
    getServerSideProps: jest.fn((callback) => {
      return async (ctx: any) => {
        testStore = mockStore({}, { serializableCheck: false });
        return await callback(testStore)(ctx);
      };
    }),
  },
}));

// Type definitions for mocks
const mockGetChats = getChats as jest.MockedFunction<typeof getChats>;
const mockGetChat = getChat as jest.MockedFunction<typeof getChat>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;
const mockGetChatsGroups = getChatsGroups as jest.MockedFunction<
  typeof getChatsGroups
>;
const mockUpdateLastReleaseDate = updateLastReleaseDate as jest.MockedFunction<
  typeof updateLastReleaseDate
>;
const mockFetchUserData = fetchUserData as jest.MockedFunction<
  typeof fetchUserData
>;
const mockHandleServerError = handleServerError as jest.MockedFunction<
  typeof handleServerError
>;
const mockCustomDayjs = customDayjs as jest.MockedFunction<typeof customDayjs>;
const mockTransformMessagesToObject =
  transformMessagesToObject as jest.MockedFunction<
    typeof transformMessagesToObject
  >;

describe('HomePage', () => {
  const defaultUser = {
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    last_release_date: null,
  };

  describe('Component Rendering', () => {
    let store: ReturnType<typeof mockStore>;

    beforeEach(() => {
      store = mockStore({
        chats: {
          chats: [],
          activeChat: null,
          hasMoreChats: false,
          hasMoreMessages: false,
          totalChats: 0,
          vaultMode: false,
          vaultModeRegistered: false,
          showEnableVaultModal: false,
          aiTyping: false,
        },
        settings: {
          user: defaultUser,
          releases: [],
          showReleaseModal: false,
          hasMoreReleases: false,
          themeMode: 'light',
          collapsedSidebar: false,
        },
        chatsGroups: {
          chatsGroups: [],
          activeChatGroup: null,
        },
      });
    });

    it('should render HomePage component with Head and HomeTemplate', () => {
      renderLayout(<HomePage />, { store });
      expect(screen.getByTestId('home-template')).toBeInTheDocument();
    });

    it('should render without errors', () => {
      expect(() => renderLayout(<HomePage />, { store })).not.toThrow();
    });
  });

  describe('getServerSideProps', () => {
    const mockContext: GetServerSidePropsContext = {
      req: {
        headers: {
          authorization: 'Bearer token',
          'user-agent': 'test-agent',
        },
        cookies: { userEmail: 'test@example.com' },
      } as any,
      res: {} as any,
      query: {},
      params: {},
      resolvedUrl: '/',
    };

    const mockUserData = {
      user: {
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        last_release_date: null,
      },
      isVaultModeRegistered: true,
      isVaultModeEnabled: false,
      releases: {
        docs: [
          {
            date: '25.12.2023',
            title: 'Version 1.0.0',
            changes: ['Initial release', 'Added authentication'],
          },
        ],
        totalDocs: 1,
        limit: 10,
        page: 1,
        totalPages: 1,
        hasNextPage: false,
        nextPage: 2,
        hasPrevPage: false,
        prevPage: 1,
      },
    };

    const mockMessagesList = [
      {
        message_id: 'msg-1',
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello message',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        created_at: '2023-12-25T00:00:00.000Z',
        attachments: [],
      },
    ];

    const mockMessagesObject = {
      'msg-1': {
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello message',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        created_at: '2023-12-25T00:00:00.000Z',
        attachments: [],
        edit: false,
        loading: false,
      },
    };

    const mockChatsData = {
      docs: [
        {
          chat_id: 'chat1',
          title: 'Chat 1',
          created_at: '2023-12-25T00:00:00.000Z',
          owner_id: 'user-123',
          last_message_at: '2023-12-25T00:00:00.000Z',
          vault_mode: false,
          active: false,
          favorite: false,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
          group_id: null,
          messages: {},
        },
        {
          chat_id: 'chat2',
          title: 'Chat 2',
          created_at: '2023-12-25T00:00:00.000Z',
          owner_id: 'user-123',
          last_message_at: '2023-12-25T00:00:00.000Z',
          vault_mode: false,
          active: false,
          favorite: false,
          status: ChatStatusEnum.NORMAL,
          status_msg: null,
          group_id: null,
          messages: {},
        },
      ],
      totalDocs: 10,
      limit: 15,
      page: 1,
      totalPages: 1,
      hasNextPage: true,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
      active_chat_id: 'chat1',
    };

    const mockActiveChat = {
      chat_id: 'chat1',
      title: 'Active Chat',
      created_at: '2023-12-25T00:00:00.000Z',
      owner_id: 'user-123',
      last_message_at: '2023-12-25T00:00:00.000Z',
      vault_mode: false,
      active: true,
      favorite: false,
      status: ChatStatusEnum.NORMAL,
      status_msg: null,
      group_id: null,
      messages: {},
    };

    const mockMessagesResponse = {
      docs: mockMessagesList,
      totalDocs: 1,
      limit: 20,
      page: 1,
      totalPages: 1,
      hasNextPage: false,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
    };

    const mockChatGroups = [
      {
        group_id: 'group1',
        title: 'Group 1',
      },
      {
        group_id: 'group2',
        title: 'Group 2',
      },
    ];

    const mockChatGroupsPagination = {
      docs: mockChatGroups,
      totalDocs: 2,
      limit: 50,
      page: 1,
      totalPages: 1,
      hasNextPage: false,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
    };

    const mockEmptyChatGroupsPagination = {
      docs: [],
      totalDocs: 0,
      limit: 50,
      page: 1,
      totalPages: 0,
      hasNextPage: false,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
    };

    beforeEach(() => {
      jest.clearAllMocks();
      testStore = null;

      const mockDayjsInstance = {
        isAfter: jest.fn(() => false),
        toDate: jest.fn(() => new Date('2023-12-25')),
        clone: jest.fn(),
        isValid: jest.fn(() => true),
        year: jest.fn(() => 2023),
        month: jest.fn(() => 11),
        date: jest.fn(() => 25),
        day: jest.fn(() => 1),
        hour: jest.fn(() => 0),
        minute: jest.fn(() => 0),
        second: jest.fn(() => 0),
        millisecond: jest.fn(() => 0),
        format: jest.fn(() => '2023-12-25'),
        valueOf: jest.fn(() => 1703462400000),
        unix: jest.fn(() => 1703462400),
        utc: jest.fn(),
        local: jest.fn(),
        utcOffset: jest.fn(),
        timezone: jest.fn(),
        startOf: jest.fn(),
        endOf: jest.fn(),
        add: jest.fn(),
        subtract: jest.fn(),
        set: jest.fn(),
        get: jest.fn(),
        isBefore: jest.fn(),
        isSame: jest.fn(),
        isSameOrAfter: jest.fn(),
        isSameOrBefore: jest.fn(),
        isBetween: jest.fn(),
        isDST: jest.fn(),
        isLeapYear: jest.fn(),
        diff: jest.fn(),
        toString: jest.fn(() => '2023-12-25'),
        toISOString: jest.fn(() => '2023-12-25T00:00:00.000Z'),
        toJSON: jest.fn(() => '2023-12-25T00:00:00.000Z'),
        toArray: jest.fn(() => [2023, 11, 25, 0, 0, 0, 0]),
        toObject: jest.fn(() => ({
          years: 2023,
          months: 11,
          date: 25,
          hours: 0,
          minutes: 0,
          seconds: 0,
          milliseconds: 0,
        })),
      } as any;

      mockCustomDayjs.mockReturnValue(mockDayjsInstance);
      mockTransformMessagesToObject.mockReturnValue(mockMessagesObject);
    });

    describe('Authentication', () => {
      it('should redirect to /403 when userEmail cookie is missing', async () => {
        const contextWithoutEmail = {
          ...mockContext,
          req: {
            ...mockContext.req,
            cookies: {},
            headers: {},
          },
        };
        // @ts-ignore
        const result = await getServerSideProps(contextWithoutEmail);

        expect(result).toEqual({
          redirect: {
            destination: '/403',
            permanent: false,
          },
        });
      });

      it('should use x-auth-request-email header when cookie is missing', async () => {
        const contextWithHeader = {
          ...mockContext,
          req: {
            ...mockContext.req,
            cookies: {},
            headers: {
              ...mockContext.req.headers,
              'x-auth-request-email': 'test@example.com',
            },
          },
        };

        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue({
          ...mockChatsData,
          active_chat_id: undefined,
        });
        mockGetChatsGroups.mockResolvedValue(mockEmptyChatGroupsPagination);
        // @ts-ignore
        const result = await getServerSideProps(contextWithHeader);

        expect(result).toEqual({ props: {} });
        expect(mockFetchUserData).toHaveBeenCalled();
      });
    });

    describe('Successful Data Loading', () => {
      beforeEach(() => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockResolvedValue(mockActiveChat);
        mockGetMessages.mockResolvedValue(mockMessagesResponse);
        mockGetChatsGroups.mockResolvedValue(mockChatGroupsPagination);
        mockUpdateLastReleaseDate.mockResolvedValue({ success: true });
      });

      it('should successfully load all data and update store correctly', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        const expectedHeaders = {
          ...mockContext.req.headers,
          'X-Auth-Request-Email': 'test@example.com',
        };

        expect(mockFetchUserData).toHaveBeenCalledWith(expectedHeaders);
        expect(mockGetChats).toHaveBeenCalledWith({
          page: 1,
          limit: 15,
          incomingHeaders: expectedHeaders,
        });
        expect(mockGetChat).toHaveBeenCalledWith({
          id: 'chat1',
          incomingHeaders: expectedHeaders,
        });
        expect(mockGetMessages).toHaveBeenCalledWith({
          chat_id: 'chat1',
          page: 1,
          limit: 20,
          incomingHeaders: expectedHeaders,
        });
        expect(mockGetChatsGroups).toHaveBeenCalledWith({
          page: 1,
          limit: 50,
          incomingHeaders: expectedHeaders,
        });

        const state = testStore.getState();
        expect(state.settings.user).toMatchObject({
          email: mockUserData.user.email,
          first_name: mockUserData.user.first_name,
          last_name: mockUserData.user.last_name,
        });
        expect(state.settings.releases).toEqual(mockUserData.releases.docs);
        expect(state.settings.hasMoreReleases).toBe(false);
        expect(state.chats.vaultModeRegistered).toBe(
          mockUserData.isVaultModeRegistered,
        );
        expect(state.chats.vaultMode).toBe(mockUserData.isVaultModeEnabled);
        expect(state.chats.chats).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              chat_id: 'chat1',
              title: 'Chat 1',
              active: true,
            }),
            expect.objectContaining({
              chat_id: 'chat2',
              title: 'Chat 2',
              active: false,
            }),
          ]),
        );
        expect(state.chats.hasMoreChats).toBe(mockChatsData.hasNextPage);
        expect(state.chats.totalChats).toBe(mockChatsData.totalDocs);
        expect(state.chats.activeChat).toMatchObject({
          messages: mockMessagesObject,
          chat_id: mockActiveChat.chat_id,
          title: mockActiveChat.title,
        });
        expect(state.chats.hasMoreMessages).toBe(false);
        expect(state.chatsGroups.chatsGroups).toEqual(mockChatGroups);
      });

      it('should handle case when no active chat exists', async () => {
        mockGetChats.mockResolvedValue({
          ...mockChatsData,
          active_chat_id: undefined,
        });

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockGetChat).not.toHaveBeenCalled();
        expect(mockGetMessages).not.toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.chats.activeChat).toBeNull();
        expect(state.chats.hasMoreMessages).toBe(false);
      });

      it('should handle empty chat (no chat_id returned)', async () => {
        mockGetChat.mockResolvedValue({
          ...mockActiveChat,
          chat_id: undefined,
        } as any);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockGetMessages).not.toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.chats.hasMoreMessages).toBe(false);
      });

      it('should transform messages correctly', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockTransformMessagesToObject).toHaveBeenCalledWith(
          mockMessagesList.reverse(),
        );

        const state = testStore.getState();
        expect(state.chats.activeChat?.messages).toEqual(mockMessagesObject);
      });

      it('should handle messages with hasNextPage', async () => {
        mockGetMessages.mockResolvedValue({
          ...mockMessagesResponse,
          hasNextPage: true,
        });

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        const state = testStore.getState();
        expect(state.chats.hasMoreMessages).toBe(true);
      });
    });

    describe('Release Modal Logic', () => {
      beforeEach(() => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue({
          ...mockChatsData,
          active_chat_id: undefined,
        });
        mockGetChatsGroups.mockResolvedValue(mockEmptyChatGroupsPagination);
        mockUpdateLastReleaseDate.mockResolvedValue({ success: true });
      });

      it('should show release modal and update date when new release is available', async () => {
        const existingReleaseDate = '2023-12-20';
        const userWithReleaseDate = {
          ...mockUserData,
          user: {
            ...mockUserData.user,
            last_release_date: existingReleaseDate,
          },
        };
        // @ts-ignore
        mockFetchUserData.mockResolvedValue(userWithReleaseDate);

        const mockDayjsInstance = {
          isAfter: jest.fn(() => true),
          toDate: jest.fn(() => new Date('2023-12-25')),
          clone: jest.fn(),
          isValid: jest.fn(() => true),
          format: jest.fn(() => '2023-12-25'),
          valueOf: jest.fn(() => 1703462400000),
        } as any;
        mockCustomDayjs.mockReturnValue(mockDayjsInstance);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockDayjsInstance.isAfter).toHaveBeenCalledWith(
          mockDayjsInstance,
          'day',
        );
        expect(mockUpdateLastReleaseDate).toHaveBeenCalledWith({
          date: new Date('2023-12-25'),
          incomingHeaders: expect.any(Object),
        });

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(true);
        expect(state.settings.user.last_release_date).toEqual('25.12.2023');
      });

      it('should show release modal when no lastReleaseDate exists', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockUpdateLastReleaseDate).toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(true);
      });

      it('should not show release modal when release is not newer', async () => {
        const existingReleaseDate = '2023-12-26';
        const userWithLaterReleaseDate = {
          ...mockUserData,
          user: {
            ...mockUserData.user,
            last_release_date: existingReleaseDate,
          },
        };
        mockFetchUserData.mockResolvedValue(userWithLaterReleaseDate);

        const mockDayjsInstance = {
          isAfter: jest.fn(() => false),
          toDate: jest.fn(() => new Date('2023-12-25')),
          clone: jest.fn(),
          isValid: jest.fn(() => true),
        } as any;
        mockCustomDayjs.mockReturnValue(mockDayjsInstance);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockUpdateLastReleaseDate).not.toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(false);
      });

      it('should not show release modal when no releases exist', async () => {
        mockFetchUserData.mockResolvedValue({
          ...mockUserData,
          releases: {
            docs: [],
            totalDocs: 0,
            limit: 10,
            page: 1,
            totalPages: 0,
            hasNextPage: false,
            nextPage: 2,
            hasPrevPage: false,
            prevPage: 1,
          },
        });

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });
        expect(mockCustomDayjs).not.toHaveBeenCalled();
        expect(mockUpdateLastReleaseDate).not.toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(false);
      });
    });

    describe('Error Handling', () => {
      it('should handle fetchUserData error', async () => {
        const error = new Error('User data fetch failed');
        const errorResult = {
          redirect: { destination: '/500', permanent: false },
        };

        mockFetchUserData.mockRejectedValue(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });

      it('should handle getChats error', async () => {
        const error = new Error('Chats fetch failed');
        const errorResult = { notFound: true as const };

        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockRejectedValue(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });

      it('should handle getChat error', async () => {
        const error = new Error('Active chat fetch failed');
        const errorResult = { notFound: true as const };

        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockRejectedValue(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });

      it('should handle getMessages error', async () => {
        const error = new Error('Messages fetch failed');
        const errorResult = { notFound: true as const };

        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockResolvedValue(mockActiveChat);
        mockGetMessages.mockRejectedValue(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });

      it('should handle getChatGroups error', async () => {
        const error = new Error('Chat groups fetch failed');
        const errorResult = {
          redirect: { destination: '/500', permanent: false },
        };

        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue({
          ...mockChatsData,
          active_chat_id: undefined,
        });
        mockGetChatsGroups.mockRejectedValue(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });
    });

    describe('Data Processing', () => {
      beforeEach(() => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChatsGroups.mockResolvedValue(mockChatGroupsPagination);
        mockUpdateLastReleaseDate.mockResolvedValue({ success: true });
        mockGetMessages.mockResolvedValue(mockMessagesResponse);
      });

      it('should correctly map active status to chats', async () => {
        const chatsWithDifferentActive = {
          ...mockChatsData,
          docs: [
            { ...mockChatsData.docs[0], chat_id: 'chat1', title: 'Chat 1' },
            { ...mockChatsData.docs[1], chat_id: 'chat2', title: 'Chat 2' },
            { ...mockChatsData.docs[0], chat_id: 'chat3', title: 'Chat 3' },
          ],
          active_chat_id: 'chat2',
          totalDocs: 3,
        };

        mockGetChats.mockResolvedValue(chatsWithDifferentActive);
        mockGetChat.mockResolvedValue({ ...mockActiveChat, chat_id: 'chat2' });

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        const state = testStore.getState();
        expect(state.chats.activeChat).toMatchObject({
          chat_id: 'chat2',
          messages: mockMessagesObject,
          title: mockActiveChat.title,
        });

        expect(state.chats.chats).toEqual(
          expect.arrayContaining([
            expect.objectContaining({
              chat_id: 'chat1',
              title: 'Chat 1',
              active: false,
            }),
            expect.objectContaining({
              chat_id: 'chat2',
              title: 'Chat 2',
              active: true,
            }),
            expect.objectContaining({
              chat_id: 'chat3',
              title: 'Chat 3',
              active: false,
            }),
          ]),
        );
      });

      it('should handle undefined values with defaults', async () => {
        mockGetChats.mockResolvedValue({
          docs: undefined,
          totalDocs: undefined,
          limit: 15,
          page: 1,
          totalPages: 0,
          hasNextPage: undefined,
          nextPage: 2,
          hasPrevPage: false,
          prevPage: 1,
          active_chat_id: undefined,
        } as any);
        mockGetChatsGroups.mockResolvedValue({
          docs: undefined,
          totalDocs: 0,
          limit: 50,
          page: 1,
          totalPages: 0,
          hasNextPage: false,
          nextPage: 2,
          hasPrevPage: false,
          prevPage: 1,
        } as any);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        const state = testStore.getState();
        expect(state.chats.chats).toEqual([]);
        expect(state.chats.hasMoreChats).toBe(false);
        expect(state.chats.totalChats).toBe(0);
        expect(state.chatsGroups.chatsGroups).toEqual([]);
      });

      it('should handle empty messages response', async () => {
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockResolvedValue(mockActiveChat);
        mockGetMessages.mockResolvedValue({
          docs: [],
          totalDocs: 0,
          limit: 20,
          page: 1,
          totalPages: 0,
          hasNextPage: false,
          nextPage: 2,
          hasPrevPage: false,
          prevPage: 1,
        });
        mockTransformMessagesToObject.mockReturnValue({});

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        const state = testStore.getState();
        expect(state.chats.activeChat).toMatchObject({
          messages: {},
          chat_id: 'chat1',
          title: 'Active Chat',
        });
      });
    });

    describe('Integration', () => {
      beforeEach(() => {
        mockUpdateLastReleaseDate.mockResolvedValue({ success: true });
        mockGetMessages.mockResolvedValue(mockMessagesResponse);
      });

      it('should call all services in correct order', async () => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockResolvedValue(mockActiveChat);
        mockGetChatsGroups.mockResolvedValue(mockChatGroupsPagination);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        expect(mockFetchUserData).toHaveBeenCalledTimes(1);
        expect(mockGetChats).toHaveBeenCalledTimes(1);
        expect(mockGetChat).toHaveBeenCalledTimes(1);
        expect(mockGetMessages).toHaveBeenCalledTimes(1);
        expect(mockGetChatsGroups).toHaveBeenCalledTimes(1);
      });

      it('should use correct page sizes from constants', async () => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue({
          ...mockChatsData,
          active_chat_id: undefined,
        });
        mockGetChatsGroups.mockResolvedValue(mockEmptyChatGroupsPagination);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        expect(mockGetChats).toHaveBeenCalledWith(
          expect.objectContaining({ limit: 15 }),
        );
        expect(mockGetChatsGroups).toHaveBeenCalledWith(
          expect.objectContaining({ limit: 50 }),
        );
      });

      it('should use correct messages page size', async () => {
        mockFetchUserData.mockResolvedValue(mockUserData);
        mockGetChats.mockResolvedValue(mockChatsData);
        mockGetChat.mockResolvedValue(mockActiveChat);
        mockGetChatsGroups.mockResolvedValue(mockChatGroupsPagination);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({ props: {} });

        expect(mockGetMessages).toHaveBeenCalledWith(
          expect.objectContaining({ limit: 20 }),
        );
      });
    });
  });
});
