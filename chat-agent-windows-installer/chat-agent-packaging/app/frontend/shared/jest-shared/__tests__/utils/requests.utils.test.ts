import { getUser } from '@shared/ui/services/user.services';
import {
  checkVaultRegisteredService,
  checkVaultStatusService,
} from '@chats/services/vault.services';
import { getReleases } from '@shared/ui/services/releases.services';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';
import { fetchUserData } from '@chats/utils/requests.utils';
import { ReleasesType } from '@shared/ui/types/releases.types';
import { PaginationType } from '@shared/ui/types/pagination.types';

// Mock dependencies
jest.mock('@shared/ui/services/user.services');
jest.mock('@chats/services/vault.services');
jest.mock('@shared/ui/services/releases.services');

const mockGetUser = getUser as jest.MockedFunction<typeof getUser>;
const mockCheckVaultRegisteredService =
  checkVaultRegisteredService as jest.MockedFunction<
    typeof checkVaultRegisteredService
  >;
const mockCheckVaultStatusService =
  checkVaultStatusService as jest.MockedFunction<
    typeof checkVaultStatusService
  >;
const mockGetReleases = getReleases as jest.MockedFunction<typeof getReleases>;

describe('fetchUserData', () => {
  const mockIncomingHeaders: AxiosIncomingClientHeaders['incomingHeaders'] = {
    'x-auth-request-email': 'test@example.com',
    cookie: 'session=abc123',
    authorization: 'Bearer token123',
  };

  const mockUser = {
    email: 'test@example.com',
    first_name: 'John',
    last_name: 'Doe',
    last_release_date: null,
  };

  const mockReleasesData: ReleasesType[] = [
    {
      date: '25.12.2023',
      title: 'Version 1.0.0',
      changes: ['Initial release', 'Added user authentication'],
    },
    {
      date: '25.01.2024',
      title: 'Version 1.1.0',
      changes: ['Bug fixes', 'Performance improvements', 'New features'],
    },
  ];

  const mockReleasesPagination: PaginationType<ReleasesType> = {
    docs: mockReleasesData,
    totalDocs: 2,
    limit: 25,
    page: 1,
    totalPages: 1,
    hasNextPage: false,
    nextPage: 1,
    hasPrevPage: false,
    prevPage: 1,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch user data, vault information, and releases successfully', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: true,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle all vault modes enabled and registered with releases', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(true);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: true,
      isVaultModeEnabled: true,
      releases: mockReleasesPagination,
    });
  });

  it('should handle vault modes disabled and not registered with empty releases', async () => {
    const emptyReleases: PaginationType<ReleasesType> = {
      docs: [],
      totalDocs: 0,
      limit: 25,
      page: 1,
      totalPages: 0,
      hasNextPage: false,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 0,
    };

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(emptyReleases);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: emptyReleases,
    });
  });

  it('should handle empty user data with releases', async () => {
    const emptyUser = {
      email: '',
      first_name: '',
      last_name: '',
      last_release_date: null,
    };

    mockGetUser.mockResolvedValue(emptyUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: emptyUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });
  });

  it('should handle getUser service failure', async () => {
    const error = new Error('User service error');
    mockGetUser.mockRejectedValue(error);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(true);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    await expect(fetchUserData(mockIncomingHeaders)).rejects.toThrow(
      'User service error',
    );

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle checkVaultRegisteredService failure', async () => {
    const error = new Error('Vault registration check failed');
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockRejectedValue(error);
    mockCheckVaultStatusService.mockResolvedValue(true);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    await expect(fetchUserData(mockIncomingHeaders)).rejects.toThrow(
      'Vault registration check failed',
    );

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle checkVaultStatusService failure', async () => {
    const error = new Error('Vault status check failed');
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockRejectedValue(error);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    await expect(fetchUserData(mockIncomingHeaders)).rejects.toThrow(
      'Vault status check failed',
    );

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle getReleases service failure', async () => {
    const error = new Error('Releases service error');
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockRejectedValue(error);

    await expect(fetchUserData(mockIncomingHeaders)).rejects.toThrow(
      'Releases service error',
    );

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle multiple service failures', async () => {
    const userError = new Error('User service error');
    const vaultError = new Error('Vault service error');
    const releasesError = new Error('Releases service error');

    mockGetUser.mockRejectedValue(userError);
    mockCheckVaultRegisteredService.mockRejectedValue(vaultError);
    mockCheckVaultStatusService.mockRejectedValue(vaultError);
    mockGetReleases.mockRejectedValue(releasesError);

    await expect(fetchUserData(mockIncomingHeaders)).rejects.toThrow(
      'User service error',
    );

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should call all services with correct parameters', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    await fetchUserData(mockIncomingHeaders);

    expect(mockGetUser).toHaveBeenCalledTimes(1);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledTimes(1);
    expect(mockCheckVaultStatusService).toHaveBeenCalledTimes(1);
    expect(mockGetReleases).toHaveBeenCalledTimes(1);

    expect(mockGetUser).toHaveBeenCalledWith(mockIncomingHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(
      mockIncomingHeaders,
    );
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle undefined incoming headers', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(undefined as any);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    expect(mockGetUser).toHaveBeenCalledWith(undefined);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(undefined);
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(undefined);
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: undefined,
    });
  });

  it('should handle empty incoming headers object', async () => {
    const emptyHeaders = {};

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(emptyHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    expect(mockGetUser).toHaveBeenCalledWith(emptyHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(emptyHeaders);
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(emptyHeaders);
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: emptyHeaders,
    });
  });

  it('should execute all services concurrently using Promise.all', async () => {
    const startTime = Date.now();

    // Mock services with delays to test concurrent execution
    mockGetUser.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(mockUser), 50)),
    );
    mockCheckVaultRegisteredService.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(true), 50)),
    );
    mockCheckVaultStatusService.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve(false), 50)),
    );
    mockGetReleases.mockImplementation(
      () =>
        new Promise((resolve) =>
          setTimeout(() => resolve(mockReleasesPagination), 50),
        ),
    );

    const result = await fetchUserData(mockIncomingHeaders);
    const endTime = Date.now();
    const executionTime = endTime - startTime;

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: true,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    // If executed concurrently, total time should be close to 50ms, not 200ms
    expect(executionTime).toBeLessThan(100);
  });

  it('should handle releases with different data structures', async () => {
    const complexReleasesData: ReleasesType[] = [
      {
        date: '01.01.2024',
        title: 'Major Release v2.0',
        changes: [
          'Complete UI overhaul',
          'New authentication system',
          'Performance improvements',
          'Bug fixes and stability improvements',
        ],
      },
      {
        date: '25.02.2024',
        title: 'Hotfix v2.0.1',
        changes: ['Critical security patch'],
      },
    ];

    const complexReleases: PaginationType<ReleasesType> = {
      docs: complexReleasesData,
      totalDocs: 2,
      limit: 25,
      page: 1,
      totalPages: 1,
      hasNextPage: false,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 0,
    };

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(true);
    mockGetReleases.mockResolvedValue(complexReleases);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: true,
      isVaultModeEnabled: true,
      releases: complexReleases,
    });

    expect(result.releases.docs).toHaveLength(2);
    expect(result.releases.docs[0].changes).toHaveLength(4);
    expect(result.releases.docs[1].changes).toHaveLength(1);
  });

  it('should handle getReleases returning null or undefined', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(null as any);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: null,
    });
  });

  it('should pass headers correctly to all services that require authentication', async () => {
    const customHeaders = {
      'x-auth-request-email': 'custom@test.com',
      cookie: 'custom-session=xyz789',
      authorization: 'Bearer custom-token',
      'user-agent': 'Custom-Agent/1.0',
    };

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(customHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: true,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    // Verify all services received the custom headers
    expect(mockGetUser).toHaveBeenCalledWith(customHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(customHeaders);
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(customHeaders);
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: customHeaders,
    });
  });

  it('should handle partial header objects', async () => {
    const partialHeaders = {
      'x-auth-request-email': 'partial@test.com',
      // Missing cookie and authorization
    };

    const emptyReleases: PaginationType<ReleasesType> = {
      docs: [],
      totalDocs: 0,
      limit: 25,
      page: 1,
      totalPages: 0,
      hasNextPage: false,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 0,
    };

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(emptyReleases);

    const result = await fetchUserData(partialHeaders);

    expect(result).toEqual({
      user: mockUser,
      isVaultModeRegistered: false,
      isVaultModeEnabled: false,
      releases: emptyReleases,
    });

    expect(mockGetUser).toHaveBeenCalledWith(partialHeaders);
    expect(mockCheckVaultRegisteredService).toHaveBeenCalledWith(
      partialHeaders,
    );
    expect(mockCheckVaultStatusService).toHaveBeenCalledWith(partialHeaders);
    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: partialHeaders,
    });
  });

  it('should maintain the order of returned values matching Promise.all destructuring', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(mockIncomingHeaders);

    // Verify the order matches the destructuring: [user, isVaultModeRegistered, isVaultModeEnabled, releases]
    expect(Object.keys(result)).toEqual([
      'user',
      'isVaultModeRegistered',
      'isVaultModeEnabled',
      'releases',
    ]);
  });

  it('should handle services returning different data types correctly', async () => {
    const userWithExtraFields = {
      ...mockUser,
      id: 123,
      createdAt: '2023-01-01',
      preferences: { theme: 'dark' },
    };

    mockGetUser.mockResolvedValue(userWithExtraFields);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result).toEqual({
      user: userWithExtraFields,
      isVaultModeRegistered: true,
      isVaultModeEnabled: false,
      releases: mockReleasesPagination,
    });

    expect(typeof result.user).toBe('object');
    expect(typeof result.isVaultModeRegistered).toBe('boolean');
    expect(typeof result.isVaultModeEnabled).toBe('boolean');
    expect(typeof result.releases).toBe('object');
    expect(Array.isArray(result.releases.docs)).toBe(true);
  });

  it('should use correct pagination parameters for getReleases', async () => {
    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(false);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(mockReleasesPagination);

    await fetchUserData(mockIncomingHeaders);

    expect(mockGetReleases).toHaveBeenCalledWith({
      page: 1,
      limit: 25,
      incomingHeaders: mockIncomingHeaders,
    });
  });

  it('should handle paginated releases with hasNextPage true', async () => {
    const paginatedReleases: PaginationType<ReleasesType> = {
      docs: mockReleasesData,
      totalDocs: 50,
      limit: 25,
      page: 1,
      totalPages: 4,
      hasNextPage: true,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 1,
    };

    mockGetUser.mockResolvedValue(mockUser);
    mockCheckVaultRegisteredService.mockResolvedValue(true);
    mockCheckVaultStatusService.mockResolvedValue(false);
    mockGetReleases.mockResolvedValue(paginatedReleases);

    const result = await fetchUserData(mockIncomingHeaders);

    expect(result.releases.hasNextPage).toBe(true);
    expect(result.releases.totalDocs).toBe(50);
    expect(result.releases.totalPages).toBe(4);
  });
});
