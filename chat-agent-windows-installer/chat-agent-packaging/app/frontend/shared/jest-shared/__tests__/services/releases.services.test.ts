import axiosLibs from '@shared/ui/libs/axios.libs';
import { ReleasesType } from '@shared/ui/types/releases.types';
import {
  getReleases,
  updateLastReleaseDate,
} from '@shared/ui/services/releases.services';
import { updateLastReleaseDateValidator } from '@shared/ui/validators/releases.validators';
import { pickKeys } from '@shared/ui/utils/common.utils';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import { PaginationType } from '@shared/ui/types/pagination.types';

// Mock the axios library
jest.mock('@shared/ui/libs/axios.libs');
const mockedAxios = axiosLibs as jest.Mocked<typeof axiosLibs>;

// Mock the validator
jest.mock('@shared/ui/validators/releases.validators');
const mockedValidator = updateLastReleaseDateValidator as jest.Mocked<
  typeof updateLastReleaseDateValidator
>;

// Mock the utility function
jest.mock('@shared/ui/utils/common.utils');
const mockedPickKeys = pickKeys as jest.MockedFunction<typeof pickKeys>;

describe('Releases Services', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Setup default mock implementations
    mockedValidator.parseAsync = jest.fn().mockResolvedValue(undefined);
    mockedPickKeys.mockImplementation(({ obj, keysToPick }) => {
      const result: any = {};
      keysToPick.forEach((key) => {
        if (obj && key in obj) {
          result[key] = obj[key];
        }
      });
      return result;
    });
  });

  describe('getReleases', () => {
    const mockReleasesData: ReleasesType[] = [
      {
        date: '2023-12-01',
        title: 'Version 1.0.0',
        changes: ['Initial release', 'Added user authentication'],
      },
      {
        date: '2023-12-15',
        title: 'Version 1.1.0',
        changes: ['Bug fixes', 'Performance improvements', 'New dashboard'],
      },
    ];

    const mockPaginatedResponse: PaginationType<ReleasesType> = {
      docs: mockReleasesData,
      totalDocs: 10,
      limit: DEFAULT_PAGE_SIZE,
      page: 1,
      totalPages: 2,
      hasNextPage: true,
      nextPage: 2,
      hasPrevPage: false,
      prevPage: 0,
    };

    it('should return paginated releases data when API call is successful', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
      expect(result).toEqual(mockPaginatedResponse);
      expect(result.docs).toHaveLength(2);
      expect(result.docs[0]).toMatchObject({
        date: expect.any(String),
        title: expect.any(String),
        changes: expect.any(Array),
      });
      expect(result.hasNextPage).toBe(true);
      expect(result.totalDocs).toBe(10);
    });

    it('should use default values when no parameters provided', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should pass custom pagination parameters correctly', async () => {
      // Arrange
      const customResponse: PaginationType<ReleasesType> = {
        ...mockPaginatedResponse,
        page: 2,
        limit: 5,
        hasPrevPage: true,
        prevPage: 1,
      };
      mockedAxios.get.mockResolvedValue({ data: customResponse });

      // Act
      const result = await getReleases({
        page: 2,
        limit: 5,
        search: 'version',
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 2,
          limit: 5,
          search: 'version',
        },
      });
      expect(result.page).toBe(2);
      expect(result.limit).toBe(5);
    });

    it('should handle search parameter correctly', async () => {
      // Arrange
      const searchTerm = 'bug fix';
      const searchResponse: PaginationType<ReleasesType> = {
        ...mockPaginatedResponse,
        docs: [mockReleasesData[1]], // Only one result for search
        totalDocs: 1,
        totalPages: 1,
        hasNextPage: false,
      };
      mockedAxios.get.mockResolvedValue({ data: searchResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        search: searchTerm,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: searchTerm,
        },
      });
      expect(result.docs).toHaveLength(1);
      expect(result.totalDocs).toBe(1);
      expect(result.hasNextPage).toBe(false);
    });

    it('should handle empty search string', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        search: '',
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle undefined search parameter', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should return paginated data with headers when incomingHeaders provided', async () => {
      // Arrange
      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
        'other-header': 'should-be-filtered',
      };
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        incomingHeaders,
      });

      // Assert
      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
        headers: {
          'x-auth-request-email': 'test@example.com',
          cookie: 'session=abc123',
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle empty results with correct pagination structure', async () => {
      // Arrange
      const emptyResponse: PaginationType<ReleasesType> = {
        docs: [],
        totalDocs: 0,
        limit: DEFAULT_PAGE_SIZE,
        page: 1,
        totalPages: 0,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 0,
      };
      mockedAxios.get.mockResolvedValue({ data: emptyResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(result.docs).toEqual([]);
      expect(result.totalDocs).toBe(0);
      expect(result.hasNextPage).toBe(false);
    });

    it('should handle last page correctly', async () => {
      // Arrange
      const lastPageResponse: PaginationType<ReleasesType> = {
        docs: [mockReleasesData[0]],
        totalDocs: 3,
        limit: DEFAULT_PAGE_SIZE,
        page: 2,
        totalPages: 2,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: true,
        prevPage: 1,
      };
      mockedAxios.get.mockResolvedValue({ data: lastPageResponse });

      // Act
      const result = await getReleases({
        page: 2,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(result.hasNextPage).toBe(false);
      expect(result.hasPrevPage).toBe(true);
      expect(result.page).toBe(2);
      expect(result.totalPages).toBe(2);
    });

    it('should throw error when API call fails', async () => {
      // Arrange
      const errorMessage = 'Network Error';
      mockedAxios.get.mockRejectedValue(new Error(errorMessage));

      // Act & Assert
      await expect(
        getReleases({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
        }),
      ).rejects.toThrow(errorMessage);
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
    });

    it('should throw error when API returns 404', async () => {
      // Arrange
      const error = {
        response: {
          status: 404,
          data: { message: 'Not Found' },
        },
      };
      mockedAxios.get.mockRejectedValue(error);

      // Act & Assert
      await expect(
        getReleases({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
        }),
      ).rejects.toEqual(error);
    });

    it('should throw error when API returns 500', async () => {
      // Arrange
      const error = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' },
        },
      };
      mockedAxios.get.mockRejectedValue(error);

      // Act & Assert
      await expect(
        getReleases({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
        }),
      ).rejects.toEqual(error);
    });

    it('should handle single release item correctly', async () => {
      // Arrange
      const singleReleaseResponse: PaginationType<ReleasesType> = {
        docs: [
          {
            date: '2023-12-01',
            title: 'Hotfix 1.0.1',
            changes: ['Critical bug fix'],
          },
        ],
        totalDocs: 1,
        limit: DEFAULT_PAGE_SIZE,
        page: 1,
        totalPages: 1,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 0,
      };
      mockedAxios.get.mockResolvedValue({ data: singleReleaseResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(result.docs).toHaveLength(1);
      expect(result.docs[0].date).toBe('2023-12-01');
      expect(result.docs[0].title).toBe('Hotfix 1.0.1');
      expect(result.docs[0].changes).toEqual(['Critical bug fix']);
      expect(result.totalDocs).toBe(1);
    });

    it('should handle release with empty changes array', async () => {
      // Arrange
      const emptyChangesResponse: PaginationType<ReleasesType> = {
        docs: [
          {
            date: '2023-12-01',
            title: 'Version 2.0.0',
            changes: [],
          },
        ],
        totalDocs: 1,
        limit: DEFAULT_PAGE_SIZE,
        page: 1,
        totalPages: 1,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 0,
      };
      mockedAxios.get.mockResolvedValue({ data: emptyChangesResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(result.docs).toHaveLength(1);
      expect(result.docs[0].changes).toEqual([]);
    });

    it('should handle release with multiple changes', async () => {
      // Arrange
      const multipleChangesResponse: PaginationType<ReleasesType> = {
        docs: [
          {
            date: '2023-12-01',
            title: 'Major Update 3.0.0',
            changes: [
              'Complete UI redesign',
              'New API endpoints',
              'Database migration',
              'Security improvements',
              'Performance optimizations',
            ],
          },
        ],
        totalDocs: 1,
        limit: DEFAULT_PAGE_SIZE,
        page: 1,
        totalPages: 1,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 0,
      };
      mockedAxios.get.mockResolvedValue({ data: multipleChangesResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(result.docs).toHaveLength(1);
      expect(result.docs[0].changes).toHaveLength(5);
      expect(result.docs[0].changes).toContain('Complete UI redesign');
      expect(result.docs[0].changes).toContain('Performance optimizations');
    });

    it('should handle special characters in search', async () => {
      // Arrange
      const specialSearch = '!@#$%^&*()_+{}|:"<>?';
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        search: specialSearch,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: specialSearch,
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle Unicode characters in search', async () => {
      // Arrange
      const unicodeSearch = '🚀 测试 español';
      mockedAxios.get.mockResolvedValue({ data: mockPaginatedResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        search: unicodeSearch,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          search: unicodeSearch,
        },
      });
      expect(result).toEqual(mockPaginatedResponse);
    });

    it('should handle very large page numbers', async () => {
      // Arrange
      const largePageResponse: PaginationType<ReleasesType> = {
        docs: [],
        totalDocs: 100,
        limit: DEFAULT_PAGE_SIZE,
        page: 999,
        totalPages: 10,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: true,
        prevPage: 998,
      };
      mockedAxios.get.mockResolvedValue({ data: largePageResponse });

      // Act
      const result = await getReleases({
        page: 999,
        limit: DEFAULT_PAGE_SIZE,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 999,
          limit: DEFAULT_PAGE_SIZE,
          search: '',
        },
      });
      expect(result.page).toBe(999);
      expect(result.docs).toEqual([]);
    });

    it('should handle custom limit values', async () => {
      // Arrange
      const customLimitResponse: PaginationType<ReleasesType> = {
        ...mockPaginatedResponse,
        limit: 50,
      };
      mockedAxios.get.mockResolvedValue({ data: customLimitResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: 50,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: 50,
          search: '',
        },
      });
      expect(result.limit).toBe(50);
    });

    it('should handle zero limit edge case', async () => {
      // Arrange
      const zeroLimitResponse: PaginationType<ReleasesType> = {
        docs: [],
        totalDocs: 10,
        limit: 0,
        page: 1,
        totalPages: 0,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 0,
      };
      mockedAxios.get.mockResolvedValue({ data: zeroLimitResponse });

      // Act
      const result = await getReleases({
        page: 1,
        limit: 0,
      });

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/releases', {
        params: {
          page: 1,
          limit: 0,
          search: '',
        },
      });
      expect(result.limit).toBe(0);
      expect(result.docs).toEqual([]);
    });
  });

  describe('updateLastReleaseDate', () => {
    const mockDate = new Date('2023-12-01T10:00:00Z');
    const mockResponseData = {
      success: true,
      message: 'Date updated successfully',
    };

    it('should update last release date successfully', async () => {
      // Arrange
      mockedAxios.put.mockResolvedValue({ data: mockResponseData });

      // Act
      const result = await updateLastReleaseDate({ date: mockDate });

      // Assert
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
      expect(result).toEqual(mockResponseData);
    });

    it('should update last release date with headers when incomingHeaders provided', async () => {
      // Arrange
      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
        'other-header': 'should-be-filtered',
      };
      mockedAxios.put.mockResolvedValue({ data: mockResponseData });

      // Act
      const result = await updateLastReleaseDate({
        date: mockDate,
        incomingHeaders,
      });

      // Assert
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=abc123',
          },
        },
      );
      expect(result).toEqual(mockResponseData);
    });

    it('should throw validation error when date is invalid', async () => {
      // Arrange
      const validationError = new Error('Invalid date format');
      mockedValidator.parseAsync.mockRejectedValue(validationError);

      // Act & Assert
      await expect(updateLastReleaseDate({ date: mockDate })).rejects.toThrow(
        'Invalid date format',
      );
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).not.toHaveBeenCalled();
    });

    it('should throw error when API call fails', async () => {
      // Arrange
      const errorMessage = 'Network Error';
      mockedAxios.put.mockRejectedValue(new Error(errorMessage));

      // Act & Assert
      await expect(updateLastReleaseDate({ date: mockDate })).rejects.toThrow(
        errorMessage,
      );
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
    });

    it('should throw error when API returns 400', async () => {
      // Arrange
      const error = {
        response: {
          status: 400,
          data: { message: 'Bad Request' },
        },
      };
      mockedAxios.put.mockRejectedValue(error);

      // Act & Assert
      await expect(updateLastReleaseDate({ date: mockDate })).rejects.toEqual(
        error,
      );
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
    });

    it('should throw error when API returns 401 Unauthorized', async () => {
      // Arrange
      const error = {
        response: {
          status: 401,
          data: { message: 'Unauthorized' },
        },
      };
      mockedAxios.put.mockRejectedValue(error);

      // Act & Assert
      await expect(updateLastReleaseDate({ date: mockDate })).rejects.toEqual(
        error,
      );
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
    });

    it('should throw error when API returns 500', async () => {
      // Arrange
      const error = {
        response: {
          status: 500,
          data: { message: 'Internal Server Error' },
        },
      };
      mockedAxios.put.mockRejectedValue(error);

      // Act & Assert
      await expect(updateLastReleaseDate({ date: mockDate })).rejects.toEqual(
        error,
      );
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
    });

    it('should handle empty response data', async () => {
      // Arrange
      mockedAxios.put.mockResolvedValue({ data: null });

      // Act
      const result = await updateLastReleaseDate({ date: mockDate });

      // Assert
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
      expect(result).toBeNull();
    });

    it('should handle undefined response data', async () => {
      // Arrange
      mockedAxios.put.mockResolvedValue({ data: undefined });

      // Act
      const result = await updateLastReleaseDate({ date: mockDate });

      // Assert
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: mockDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2023-12-01' },
        {},
      );
      expect(result).toBeUndefined();
    });

    it('should work with different date formats', async () => {
      // Arrange
      const differentDate = new Date('2024-01-15T15:30:00Z');
      mockedAxios.put.mockResolvedValue({ data: mockResponseData });

      // Act
      const result = await updateLastReleaseDate({ date: differentDate });

      // Assert
      expect(mockedValidator.parseAsync).toHaveBeenCalledWith({
        date: differentDate,
      });
      expect(mockedAxios.put).toHaveBeenCalledWith(
        '/releases',
        { date: '2024-01-15' },
        {},
      );
      expect(result).toEqual(mockResponseData);
    });
  });
});
