import React from 'react';
import { screen } from '@testing-library/react';
import { GetServerSidePropsContext } from 'next';
import axios from 'axios';
import HomePage, { getServerSideProps } from '@/pages/index';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';
import { getUser } from '@shared/ui/services/user.services';
import {
  getReleases,
  updateLastReleaseDate,
} from '@shared/ui/services/releases.services';
import { getMessages } from '@shared/ui/services/messages.services';
import { createChat, getChats } from '@shared/ui/services/chats.services';
import {
  getAvailableDevices,
  getAvailablePlatforms,
} from '@/services/beta-reports.services';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { handleServerError } from '@shared/ui/utils/errors.utils';
import {
  DEFAULT_PAGE_SIZE,
  CHAT_MESSAGES_PAGE_SIZE,
} from '@shared/ui/constants/common.constants';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

// Mock axios
jest.mock('axios');

// Mock Next.js Head component
jest.mock('next/head', () => {
  return function Head({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
  };
});

// Mock BetaReportsTemplate component
jest.mock('@/components/templates/BetaReportsTemplate', () => {
  return function BetaReportsTemplate(props: any) {
    return (
      <div
        data-testid='beta-reports-template'
        data-props={JSON.stringify(props)}
      >
        Beta Reports Template
      </div>
    );
  };
});

// Mock services
jest.mock('@shared/ui/services/user.services', () => ({
  getUser: jest.fn(),
}));

jest.mock('@shared/ui/services/releases.services', () => ({
  getReleases: jest.fn(),
  updateLastReleaseDate: jest.fn(),
}));

jest.mock('@shared/ui/services/messages.services', () => ({
  getMessages: jest.fn(),
}));

jest.mock('@shared/ui/services/chats.services', () => ({
  getChats: jest.fn(),
  createChat: jest.fn(),
}));

jest.mock('@/services/beta-reports.services', () => ({
  getAvailableDevices: jest.fn(),
  getAvailablePlatforms: jest.fn(),
}));

jest.mock('@shared/ui/utils/errors.utils', () => ({
  handleServerError: jest.fn(),
}));

jest.mock('@shared/ui/libs/dayjs.libs', () => jest.fn());

jest.mock('@shared/ui/utils/messages.utils', () => ({
  transformMessagesToObject: jest.fn((docs) => {
    return docs.reduce((acc: any, doc: any) => {
      acc[doc.message_id] = doc;
      return acc;
    }, {});
  }),
}));

jest.mock('@shared/ui/utils/common.utils', () => ({
  pickKeys: jest.fn(({ obj }) => obj),
}));

// Mock Redux wrapper
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
const mockAxios = axios as jest.Mocked<typeof axios>;
const mockGetUser = getUser as jest.MockedFunction<typeof getUser>;
const mockGetReleases = getReleases as jest.MockedFunction<typeof getReleases>;
const mockGetMessages = getMessages as jest.MockedFunction<typeof getMessages>;
const mockGetChats = getChats as jest.MockedFunction<typeof getChats>;
const mockCreateChat = createChat as jest.MockedFunction<typeof createChat>;
const mockGetAvailableDevices = getAvailableDevices as jest.MockedFunction<
  typeof getAvailableDevices
>;
const mockGetAvailablePlatforms = getAvailablePlatforms as jest.MockedFunction<
  typeof getAvailablePlatforms
>;
const mockUpdateLastReleaseDate = updateLastReleaseDate as jest.MockedFunction<
  typeof updateLastReleaseDate
>;
const mockHandleServerError = handleServerError as jest.MockedFunction<
  typeof handleServerError
>;
const mockCustomDayjs = customDayjs as jest.MockedFunction<typeof customDayjs>;

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

    it('should render HomePage component with BetaReportsTemplate', () => {
      renderLayout(<HomePage pageProps={{ hasAccess: true }} />, { store });
      expect(screen.getByTestId('beta-reports-template')).toBeInTheDocument();
    });

    it('should pass pageProps to BetaReportsTemplate', () => {
      const pageProps = {
        hasAccess: true,
        defaultPlatform: PlatformEnum.ATV,
        availableDevicesOptions: [{ label: 'Device 1', value: 'device-1' }],
      };

      renderLayout(<HomePage pageProps={pageProps} />, { store });

      const template = screen.getByTestId('beta-reports-template');
      const props = JSON.parse(template.getAttribute('data-props') || '{}');

      expect(props).toMatchObject(pageProps);
    });

    it('should render without errors', () => {
      expect(() =>
        renderLayout(<HomePage pageProps={{ hasAccess: true }} />, { store }),
      ).not.toThrow();
    });
  });

  describe('getServerSideProps', () => {
    const mockContext: GetServerSidePropsContext = {
      req: {
        headers: {
          authorization: 'Bearer token',
          'user-agent': 'test-agent',
        },
        cookies: {
          userEmail: 'test@example.com',
          platform: PlatformEnum.ATV,
        },
      } as any,
      res: {} as any,
      query: {},
      params: {},
      resolvedUrl: '/',
    };

    const mockUser = {
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      last_release_date: '2025-10-01',
    };

    const mockReleases = {
      docs: [
        {
          id: 'release-1',
          date: '2025-10-20',
          title: 'Release 1.0.0',
          changes: ['Feature 1', 'Feature 2'],
        },
      ],
      hasNextPage: true,
      totalDocs: 10,
      totalPages: 2,
      page: 1,
      limit: DEFAULT_PAGE_SIZE,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
    };

    const mockChat = {
      chat_id: 'chat-1',
      title: 'Test Chat',
      created_at: '2025-01-01T00:00:00Z',
      owner_id: 'user-1',
      last_message_at: '2025-01-01T00:00:00Z',
      vault_mode: false,
      messages: {},
      active: true,
      favorite: false,
      status: ChatStatusEnum.NORMAL,
      status_msg: null,
      group_id: null,
    };

    const mockMessages = {
      docs: [
        {
          message_id: 'msg-1',
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
      totalDocs: 1,
      limit: CHAT_MESSAGES_PAGE_SIZE,
      page: 1,
      totalPages: 1,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 1,
    };

    beforeEach(() => {
      jest.clearAllMocks();
      testStore = null;

      mockAxios.get.mockResolvedValue({ data: { valid: true } });
      mockGetUser.mockResolvedValue(mockUser);
      mockGetReleases.mockResolvedValue(mockReleases);
      mockGetChats.mockResolvedValue({
        docs: [mockChat],
        hasNextPage: false,
        totalDocs: 1,
        limit: 1,
        page: 1,
        totalPages: 1,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 1,
        active_chat_id: 'chat-1',
      });
      mockGetMessages.mockResolvedValue(mockMessages);
      mockGetAvailableDevices.mockResolvedValue(['Device 1', 'Device 2']);
      mockGetAvailablePlatforms.mockResolvedValue(['AndroidTV', 'DishTV']);
      mockUpdateLastReleaseDate.mockResolvedValue({ success: true });

      const mockDayjsInstance = {
        isAfter: jest.fn(() => false),
        toDate: jest.fn(() => new Date('2025-10-20')),
        clone: jest.fn(),
        isValid: jest.fn(() => true),
        format: jest.fn(() => '2025-10-20'),
        valueOf: jest.fn(() => 1729382400000),
      } as any;

      mockCustomDayjs.mockReturnValue(mockDayjsInstance);
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

      it('uses userEmail from cookies when available', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toHaveProperty('props');
        expect(mockGetUser).toHaveBeenCalledWith(
          expect.objectContaining({
            'X-Auth-Request-Email': 'test@example.com',
          }),
        );
      });

      it('uses userEmail from headers when not in cookies', async () => {
        const contextWithHeaderEmail = {
          ...mockContext,
          req: {
            ...mockContext.req,
            cookies: { platform: PlatformEnum.ATV },
            headers: {
              ...mockContext.req.headers,
              'x-auth-request-email': 'header@example.com',
            },
          },
        };

        // @ts-ignore
        const result = await getServerSideProps(contextWithHeaderEmail);

        expect(result).toHaveProperty('props');
        expect(mockGetUser).toHaveBeenCalledWith(
          expect.objectContaining({
            'X-Auth-Request-Email': 'header@example.com',
          }),
        );
      });
    });

    describe('Access Control', () => {
      it('should return hasAccess: false when access check fails', async () => {
        mockAxios.get.mockResolvedValueOnce({ data: { valid: false } });

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual({
          props: {
            hasAccess: false,
          },
        });

        expect(mockGetUser).toHaveBeenCalled();
        expect(mockGetReleases).toHaveBeenCalled();
        expect(mockGetChats).not.toHaveBeenCalled();
      });

      it('should load full data when access check passes', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toHaveProperty('props');
        // @ts-ignore
        expect(result.props.hasAccess).toBe(true);
        expect(mockGetChats).toHaveBeenCalled();
        expect(mockGetMessages).toHaveBeenCalled();
      });
    });

    describe('Successful Data Loading', () => {
      it('should successfully load all data with access', async () => {
        const result = await getServerSideProps(mockContext);

        expect(result).toHaveProperty('props');
        // @ts-ignore
        const props = result.props;

        expect(props.hasAccess).toBe(true);
        expect(props.availableDevicesOptions).toEqual([
          { label: 'Device 1', value: 'Device 1' },
          { label: 'Device 2', value: 'Device 2' },
        ]);
        expect(props.availablePlatformsOptions).toEqual([
          { label: 'AndroidTV', value: 'AndroidTV' },
          { label: 'DishTV', value: 'DishTV' },
        ]);
        expect(props.activeChat).toBeDefined();
        expect(props.defaultPlatform).toBe(PlatformEnum.ATV);

        const state = testStore.getState();
        expect(state.settings.user).toMatchObject(mockUser);
        expect(state.settings.releases).toEqual(mockReleases.docs);
      });

      it('should create new chat when no existing chat found', async () => {
        mockGetChats.mockResolvedValueOnce({
          docs: [],
          hasNextPage: false,
          totalDocs: 0,
          limit: 1,
          page: 1,
          totalPages: 0,
          nextPage: 1,
          hasPrevPage: false,
          prevPage: 1,
        });
        mockCreateChat.mockResolvedValue(mockChat);

        const result = await getServerSideProps(mockContext);

        expect(mockCreateChat).toHaveBeenCalledWith({
          namespace: `beta_report/${PlatformEnum.ATV.toLowerCase()}`,
          incomingHeaders: expect.objectContaining({
            'X-Auth-Request-Email': 'test@example.com',
          }),
        });
        expect(result).toHaveProperty('props');
      });

      it('should use existing chat when available', async () => {
        const result = await getServerSideProps(mockContext);

        expect(mockCreateChat).not.toHaveBeenCalled();
        expect(result).toHaveProperty('props');
        // @ts-ignore
        expect(result.props.activeChat.chat_id).toBe('chat-1');
      });

      it('should handle cookies for filters', async () => {
        const contextWithCookies = {
          ...mockContext,
          req: {
            ...mockContext.req,
            cookies: {
              userEmail: 'test@example.com',
              platform: 'DishTV',
              release: '2',
              device: 'device-1',
              priority: '3',
              dateRange: JSON.stringify(['2025-01-01', '2025-01-31']),
            },
          },
        };

        // @ts-ignore
        const result = await getServerSideProps(contextWithCookies);

        // @ts-ignore
        const props = result.props;
        expect(props.defaultPlatform).toBe('DishTV');
        expect(props.defaultRelease).toBe('2');
        expect(props.defaultDevice).toBe('device-1');
        expect(props.defaultPriority).toBe('3');
        expect(props.defaultDateRange).toEqual(['2025-01-01', '2025-01-31']);
      });
    });

    describe('Release Modal Logic', () => {
      it('should show release modal when new release is available', async () => {
        const mockDayjsInstance = {
          isAfter: jest.fn(() => true),
          toDate: jest.fn(() => new Date('2025-10-20')),
          clone: jest.fn(),
          isValid: jest.fn(() => true),
          format: jest.fn(() => '2025-10-20'),
        } as any;
        mockCustomDayjs.mockReturnValue(mockDayjsInstance);

        const result = await getServerSideProps(mockContext);

        expect(mockUpdateLastReleaseDate).toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(true);
      });

      it('should show release modal when no lastReleaseDate exists', async () => {
        mockGetUser.mockResolvedValueOnce({
          ...mockUser,
          last_release_date: null,
        });

        const result = await getServerSideProps(mockContext);

        expect(mockUpdateLastReleaseDate).toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(true);
      });

      it('should not show release modal when release is not newer', async () => {
        mockGetUser.mockResolvedValueOnce({
          ...mockUser,
          last_release_date: '2025-10-25',
        });

        const mockDayjsInstance = {
          isAfter: jest.fn(() => false),
          toDate: jest.fn(() => new Date('2025-10-20')),
          clone: jest.fn(),
          isValid: jest.fn(() => true),
        } as any;
        mockCustomDayjs.mockReturnValue(mockDayjsInstance);

        const result = await getServerSideProps(mockContext);

        expect(mockUpdateLastReleaseDate).not.toHaveBeenCalled();

        const state = testStore.getState();
        expect(state.settings.showReleaseModal).toBe(false);
      });
    });

    describe('Error Handling', () => {
      it('should handle access check error', async () => {
        const error = new Error('Access check failed');
        const errorResult = {
          redirect: { destination: '/500', permanent: false },
        };

        mockAxios.get.mockRejectedValueOnce(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });

      it('should handle getUser error', async () => {
        const error = new Error('User fetch failed');
        const errorResult = {
          redirect: { destination: '/500', permanent: false },
        };

        mockGetUser.mockRejectedValueOnce(error);
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

        mockGetChats.mockRejectedValueOnce(error);
        mockHandleServerError.mockReturnValue(errorResult);

        const result = await getServerSideProps(mockContext);

        expect(result).toEqual(errorResult);
        expect(mockHandleServerError).toHaveBeenCalledWith({
          error,
          ctx: mockContext,
        });
      });
    });
  });
});
