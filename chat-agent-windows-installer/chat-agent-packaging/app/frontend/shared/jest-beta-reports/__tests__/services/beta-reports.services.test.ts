// beta-reports.services.test.ts
import axiosLibs from '@shared/ui/libs/axios.libs';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { pickKeys } from '@shared/ui/utils/common.utils';
import {
  getBetaReports,
  getIssueCandidates,
  leaveFeedbackIssue,
  getReportsReleases,
  getAvailablePlatforms,
  getAvailableDevices,
} from '@/services/beta-reports.services';
import { feedbackIssueValidator } from '@/validators/beta-reports.validator';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import {
  BetaReportType,
  IssueCandidateType,
  ReportsReleaseType,
} from '@/types/beta-reports.types';
import { DEFAULT_DATE_FORMAT } from '@shared/ui/constants/common.constants';

// Mock dependencies
jest.mock('@shared/ui/libs/axios.libs');
jest.mock('@shared/ui/libs/dayjs.libs');
jest.mock('@shared/ui/utils/common.utils');
jest.mock('@/validators/beta-reports.validator');

const mockedAxios = axiosLibs as jest.Mocked<typeof axiosLibs>;
const mockedDayjs = customDayjs as jest.MockedFunction<typeof customDayjs>;
const mockedPickKeys = pickKeys as jest.MockedFunction<typeof pickKeys>;
const mockedValidator = feedbackIssueValidator as jest.Mocked<
  typeof feedbackIssueValidator
>;

describe('Beta Reports Services', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getBetaReports', () => {
    const mockBetaReport: BetaReportType = {
      id: 1,
      url: 'https://example.com/report',
      ingest_date: '2024-01-15',
      receiver_id: 'receiver-456',
      platform: PlatformEnum.ATV,
      joey_id: 'joey-789',
      hopperp_id: 'hopperp-012',
      hopper_model: 'Hopper 3',
      hopper_software: '1.2.3',
      hopperp_model: 'Hopper Plus',
      hopperp_software: '2.3.4',
      joey_model: 'Joey 4',
      joey_software: '3.4.5',
      event_time: '2024-01-15T10:30:00Z',
      title: 'Test Report',
      marked_log: true,
      has_attachment: false,
      category: 'Performance',
      formalized_report: 'Detailed report content',
      related_issue: 'ISSUE-123',
      report_display_id: '123',
      release: 1,
      release_name: 'asd',
      event_date: '2025-12-12',
      detail: 'test',
      analysis: 'test',
    };

    const mockResponse = {
      data: {
        docs: [mockBetaReport],
        totalDocs: 1,
        totalPages: 1,
        page: 1,
        limit: 10,
      },
    };

    it('should fetch beta reports with all parameters', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      // @ts-ignore
      mockedDayjs.mockImplementation((date: any) => ({
        format: jest.fn().mockReturnValue('2024-01-15'),
      })) as any;

      const params = {
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        platform: PlatformEnum.ATV,
        release: 1,
        device: 'Hopper 3',
      };

      const result = await getBetaReports(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/reports',
        {
          params: {
            page: 1,
            limit: 10,
            start_date: '2024-01-15',
            end_date: '2024-01-15',
            platform: PlatformEnum.ATV,
            release: 1,
            device: 'Hopper 3',
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch beta reports with minimal parameters', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      const params = {
        page: 1,
        limit: 10,
      };

      const result = await getBetaReports(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/reports',
        {
          params: {
            page: 1,
            limit: 10,
            platform: undefined,
            release: undefined,
            device: undefined,
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should format dates correctly', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      const mockFormat = jest.fn().mockReturnValue('2024-01-15');
      mockedDayjs.mockReturnValue({
        format: mockFormat,
      } as any);

      await getBetaReports({
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
      });

      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-01');
      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-31');
      expect(mockFormat).toHaveBeenCalledWith(DEFAULT_DATE_FORMAT);
    });

    it('should include incoming headers when provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedPickKeys.mockReturnValue({
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      });

      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
        'other-header': 'value',
      };

      await getBetaReports({
        page: 1,
        limit: 10,
        incomingHeaders,
      });

      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/reports',
        expect.objectContaining({
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=abc123',
          },
        }),
      );
    });

    it('should not include headers when incomingHeaders is not provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      await getBetaReports({
        page: 1,
        limit: 10,
      });

      expect(mockedPickKeys).not.toHaveBeenCalled();
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/reports',
        expect.not.objectContaining({
          headers: expect.anything(),
        }),
      );
    });

    it('should handle API errors', async () => {
      const error = new Error('API Error');
      mockedAxios.get.mockRejectedValue(error);

      await expect(
        getBetaReports({
          page: 1,
          limit: 10,
        }),
      ).rejects.toThrow('API Error');
    });

    it('should omit start_date when not provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedDayjs.mockReturnValue({
        format: jest.fn().mockReturnValue('2024-01-31'),
      } as any);

      await getBetaReports({
        page: 1,
        limit: 10,
        end_date: '2024-01-31',
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).not.toHaveProperty('start_date');
      expect(callParams?.params).toHaveProperty('end_date', '2024-01-31');
    });

    it('should omit end_date when not provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedDayjs.mockReturnValue({
        format: jest.fn().mockReturnValue('2024-01-01'),
      } as any);

      await getBetaReports({
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).toHaveProperty('start_date', '2024-01-01');
      expect(callParams?.params).not.toHaveProperty('end_date');
    });
  });

  describe('getIssueCandidates', () => {
    const mockIssueCandidate: IssueCandidateType = {
      id: 'ISSUE-123',
      platform: PlatformEnum.STB,
      description: 'System crash on startup',
      title: 'Memory leak detected',
      priority: 5,
      date: '2024-01-15',
      accepted: null,
      last_updated_date: '2024-01-01',
    };

    const mockResponse = {
      data: {
        docs: [mockIssueCandidate],
        totalDocs: 1,
        totalPages: 1,
        page: 1,
        limit: 10,
      },
    };

    it('should fetch issue candidates with all parameters including priority', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      // @ts-ignore
      mockedDayjs.mockImplementation((date: any) => ({
        format: jest.fn().mockReturnValue('2024-01-15'),
      })) as any;

      const params = {
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        platform: PlatformEnum.STB,
        release: 1,
        min_priority: 3,
        max_priority: 8,
      };

      const result = await getIssueCandidates(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/issues',
        {
          params: {
            page: 1,
            limit: 10,
            start_date: '2024-01-15',
            end_date: '2024-01-15',
            platform: PlatformEnum.STB,
            release: 1,
            min_priority: 3,
            max_priority: 8,
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch issue candidates with minimal parameters', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      const params = {
        page: 1,
        limit: 10,
      };

      const result = await getIssueCandidates(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/issues',
        {
          params: {
            page: 1,
            limit: 10,
            platform: undefined,
            release: undefined,
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should include min_priority when set to 0', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      await getIssueCandidates({
        page: 1,
        limit: 10,
        min_priority: 0,
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).toHaveProperty('min_priority', 0);
    });

    it('should include max_priority when set to 0', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      await getIssueCandidates({
        page: 1,
        limit: 10,
        max_priority: 0,
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).toHaveProperty('max_priority', 0);
    });

    it('should omit priority params when undefined', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      await getIssueCandidates({
        page: 1,
        limit: 10,
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).not.toHaveProperty('min_priority');
      expect(callParams?.params).not.toHaveProperty('max_priority');
    });

    it('should include incoming headers when provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedPickKeys.mockReturnValue({
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=xyz789',
      });

      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=xyz789',
      };

      await getIssueCandidates({
        page: 1,
        limit: 10,
        incomingHeaders,
      });

      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/issues',
        expect.objectContaining({
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=xyz789',
          },
        }),
      );
    });

    it('should format dates correctly', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      const mockFormat = jest.fn().mockReturnValue('2024-01-15');
      mockedDayjs.mockReturnValue({
        format: mockFormat,
      } as any);

      await getIssueCandidates({
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
      });

      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-01');
      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-31');
      expect(mockFormat).toHaveBeenCalledWith(DEFAULT_DATE_FORMAT);
    });

    it('should handle API errors', async () => {
      const error = new Error('Network Error');
      mockedAxios.get.mockRejectedValue(error);

      await expect(
        getIssueCandidates({
          page: 1,
          limit: 10,
        }),
      ).rejects.toThrow('Network Error');
    });
  });

  describe('leaveFeedbackIssue', () => {
    const mockSuccessResponse = {
      data: {
        success: true,
      },
    };

    beforeEach(() => {
      mockedValidator.parseAsync = jest.fn().mockResolvedValue({
        accepted: true,
        id: 'ISSUE-123',
        comments: 'Test comment',
      });
    });

    it('should submit feedback with all fields', async () => {
      mockedAxios.post.mockResolvedValue(mockSuccessResponse);

      const feedback = {
        accepted: true,
        id: 'ISSUE-123',
        comments: 'This is a valid feedback',
      };

      const result = await leaveFeedbackIssue(feedback);

      expect(mockedValidator.parseAsync).toHaveBeenCalledWith(feedback);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/agents/betareport/feedback',
        {
          accept: true,
          issue_id: 'ISSUE-123',
          comments: 'This is a valid feedback',
        },
      );
      expect(result).toEqual({ success: true });
    });

    it('should submit feedback without comments', async () => {
      mockedAxios.post.mockResolvedValue(mockSuccessResponse);

      const feedback = {
        accepted: false,
        id: 'ISSUE-456',
      };

      await leaveFeedbackIssue(feedback);

      expect(mockedValidator.parseAsync).toHaveBeenCalledWith(feedback);
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/agents/betareport/feedback',
        {
          accept: false,
          issue_id: 'ISSUE-456',
          comments: undefined,
        },
      );
    });

    it('should map "accepted" to "accept" in API payload', async () => {
      mockedAxios.post.mockResolvedValue(mockSuccessResponse);

      await leaveFeedbackIssue({
        accepted: true,
        id: 'ISSUE-789',
        comments: 'Test',
      });

      const postCall = mockedAxios.post.mock.calls[0];
      expect(postCall[1]).toHaveProperty('accept', true);
      expect(postCall[1]).not.toHaveProperty('accepted');
    });

    it('should validate input before making API call', async () => {
      const validationError = new Error('Validation failed');
      mockedValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        leaveFeedbackIssue({
          accepted: true,
          id: '',
          comments: 'Test',
        }),
      ).rejects.toThrow('Validation failed');

      expect(mockedValidator.parseAsync).toHaveBeenCalled();
      expect(mockedAxios.post).not.toHaveBeenCalled();
    });

    it('should handle API errors', async () => {
      mockedAxios.post.mockRejectedValue(new Error('Server Error'));

      await expect(
        leaveFeedbackIssue({
          accepted: true,
          id: 'ISSUE-123',
          comments: 'Test',
        }),
      ).rejects.toThrow('Server Error');
    });

    it('should handle validation errors with invalid id', async () => {
      const validationError = new Error('Issue ID is required');
      mockedValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        leaveFeedbackIssue({
          accepted: true,
          id: '',
        }),
      ).rejects.toThrow('Issue ID is required');
    });

    it('should handle comments exceeding max length', async () => {
      const validationError = new Error('Comments too long');
      mockedValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        leaveFeedbackIssue({
          accepted: true,
          id: 'ISSUE-123',
          comments: 'A'.repeat(251),
        }),
      ).rejects.toThrow('Comments too long');
    });

    it('should pass through empty comments', async () => {
      mockedAxios.post.mockResolvedValue(mockSuccessResponse);

      await leaveFeedbackIssue({
        accepted: true,
        id: 'ISSUE-123',
        comments: '',
      });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/agents/betareport/feedback',
        expect.objectContaining({
          comments: '',
        }),
      );
    });
  });

  describe('getReportsReleases', () => {
    const mockRelease: ReportsReleaseType = {
      id: 1,
      release_date: new Date('2024-01-15'),
      release: 'v1.0.0',
    };

    const mockResponse = {
      data: {
        docs: [mockRelease],
        totalDocs: 1,
        totalPages: 1,
        page: 1,
        limit: 10,
        hasNextPage: false,
        nextPage: null,
        hasPrevPage: false,
        prevPage: null,
      },
    };

    it('should fetch releases with all parameters', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      // @ts-ignore
      mockedDayjs.mockImplementation((date: any) => ({
        format: jest.fn().mockReturnValue('2024-01-15'),
      })) as any;

      const params = {
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        platform: PlatformEnum.ATV,
      };

      const result = await getReportsReleases(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/releases',
        {
          params: {
            page: 1,
            limit: 10,
            start_date: '2024-01-15',
            end_date: '2024-01-15',
            platform: PlatformEnum.ATV,
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should fetch releases with minimal parameters', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      const params = {
        page: 1,
        limit: 10,
      };

      const result = await getReportsReleases(params);

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/releases',
        {
          params: {
            page: 1,
            limit: 10,
            platform: undefined,
          },
        },
      );
      expect(result).toEqual(mockResponse.data);
    });

    it('should format dates correctly', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      const mockFormat = jest.fn().mockReturnValue('2024-01-15');
      mockedDayjs.mockReturnValue({
        format: mockFormat,
      } as any);

      await getReportsReleases({
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
      });

      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-01');
      expect(mockedDayjs).toHaveBeenCalledWith('2024-01-31');
      expect(mockFormat).toHaveBeenCalledWith(DEFAULT_DATE_FORMAT);
    });

    it('should include incoming headers when provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedPickKeys.mockReturnValue({
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      });

      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      };

      await getReportsReleases({
        page: 1,
        limit: 10,
        incomingHeaders,
      });

      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/releases',
        expect.objectContaining({
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=abc123',
          },
        }),
      );
    });

    it('should handle API errors', async () => {
      const error = new Error('API Error');
      mockedAxios.get.mockRejectedValue(error);

      await expect(
        getReportsReleases({
          page: 1,
          limit: 10,
        }),
      ).rejects.toThrow('API Error');
    });

    it('should omit dates when not provided', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      await getReportsReleases({
        page: 1,
        limit: 10,
        platform: PlatformEnum.STB,
      });

      const callParams = mockedAxios.get.mock.calls[0][1];
      expect(callParams?.params).not.toHaveProperty('start_date');
      expect(callParams?.params).not.toHaveProperty('end_date');
      expect(callParams?.params).toHaveProperty('platform', PlatformEnum.STB);
    });

    it('should return releases with correct structure', async () => {
      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getReportsReleases({
        page: 1,
        limit: 10,
      });

      expect(result.docs[0]).toHaveProperty('id');
      expect(result.docs[0]).toHaveProperty('release_date');
      expect(result.docs[0]).toHaveProperty('release');
      expect(result.docs[0].release_date).toBeInstanceOf(Date);
    });

    it('should handle multiple releases', async () => {
      const multipleReleasesResponse = {
        data: {
          docs: [
            {
              id: 1,
              release_date: new Date('2024-01-15'),
              release: 'v1.0.0',
            },
            {
              id: 2,
              release_date: new Date('2024-01-20'),
              release: 'v1.1.0',
            },
            {
              id: 3,
              release_date: new Date('2024-01-25'),
              release: 'v1.2.0',
            },
          ],
          totalDocs: 3,
          totalPages: 1,
          page: 1,
          limit: 10,
        },
      };

      mockedAxios.get.mockResolvedValue(multipleReleasesResponse);

      const result = await getReportsReleases({
        page: 1,
        limit: 10,
      });

      expect(result.docs).toHaveLength(3);
      expect(result.docs[0].release).toBe('v1.0.0');
      expect(result.docs[1].release).toBe('v1.1.0');
      expect(result.docs[2].release).toBe('v1.2.0');
    });
  });

  describe('getAvailablePlatforms', () => {
    const mockPlatforms = ['AndroidTV', 'DishTV', 'iOS'];

    it('should fetch available platforms without headers', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockPlatforms });

      const result = await getAvailablePlatforms();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/available-platforms',
        {},
      );
      expect(result).toEqual(mockPlatforms);
    });

    it('should fetch available platforms with incoming headers', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockPlatforms });
      mockedPickKeys.mockReturnValue({
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      });

      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      };

      const result = await getAvailablePlatforms({ incomingHeaders });

      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/available-platforms',
        {
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=abc123',
          },
        },
      );
      expect(result).toEqual(mockPlatforms);
    });

    it('should handle empty platforms list', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });

      const result = await getAvailablePlatforms();

      expect(result).toEqual([]);
    });

    it('should handle API errors', async () => {
      const error = new Error('Network Error');
      mockedAxios.get.mockRejectedValue(error);

      await expect(getAvailablePlatforms()).rejects.toThrow('Network Error');
    });
  });

  describe('getAvailableDevices', () => {
    const mockDevices = ['Hopper 3', 'Joey 4', 'Hopper Plus'];

    it('should fetch available devices without headers', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockDevices });

      const result = await getAvailableDevices();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/available-devices',
        {},
      );
      expect(result).toEqual(mockDevices);
    });

    it('should fetch available devices with incoming headers', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockDevices });
      mockedPickKeys.mockReturnValue({
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=xyz789',
      });

      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=xyz789',
      };

      const result = await getAvailableDevices({ incomingHeaders });

      expect(mockedPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/available-devices',
        {
          headers: {
            'x-auth-request-email': 'test@example.com',
            cookie: 'session=xyz789',
          },
        },
      );
      expect(result).toEqual(mockDevices);
    });

    it('should handle empty devices list', async () => {
      mockedAxios.get.mockResolvedValue({ data: [] });

      const result = await getAvailableDevices();

      expect(result).toEqual([]);
    });

    it('should handle API errors', async () => {
      const error = new Error('Server Error');
      mockedAxios.get.mockRejectedValue(error);

      await expect(getAvailableDevices()).rejects.toThrow('Server Error');
    });

    it('should call API with correct endpoint', async () => {
      mockedAxios.get.mockResolvedValue({ data: mockDevices });

      await getAvailableDevices();

      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/agents/betareport/available-devices',
        expect.any(Object),
      );
    });
  });

  describe('Integration Tests', () => {
    it('should handle complete workflow for beta reports', async () => {
      const mockResponse = {
        data: {
          docs: [],
          totalDocs: 0,
          totalPages: 0,
          page: 1,
          limit: 10,
        },
      };

      mockedAxios.get.mockResolvedValue(mockResponse);
      mockedDayjs.mockReturnValue({
        format: jest.fn().mockReturnValue('2024-01-15'),
      } as any);

      const result = await getBetaReports({
        page: 1,
        limit: 10,
        start_date: '2024-01-01',
        end_date: '2024-01-31',
        platform: PlatformEnum.ATV,
      });

      expect(result.docs).toEqual([]);
      expect(result.totalDocs).toBe(0);
    });

    it('should handle complete workflow for issue candidates', async () => {
      const mockResponse = {
        data: {
          docs: [],
          totalDocs: 0,
          totalPages: 0,
          page: 1,
          limit: 10,
        },
      };

      mockedAxios.get.mockResolvedValue(mockResponse);

      const result = await getIssueCandidates({
        page: 1,
        limit: 10,
      });

      expect(result.docs).toEqual([]);
      expect(result.totalDocs).toBe(0);
    });

    it('should handle complete workflow for releases and platforms', async () => {
      const mockPlatforms = ['AndroidTV', 'DishTV'];
      const mockReleases = {
        data: {
          docs: [
            {
              id: 1,
              release_date: new Date('2024-01-15'),
              release: 'v1.0.0',
            },
          ],
          totalDocs: 1,
          page: 1,
          limit: 10,
        },
      };

      mockedAxios.get
        .mockResolvedValueOnce({ data: mockPlatforms })
        .mockResolvedValueOnce(mockReleases);

      const platforms = await getAvailablePlatforms();
      const releases = await getReportsReleases({
        page: 1,
        limit: 10,
        platform: platforms[0],
      });

      expect(platforms).toEqual(mockPlatforms);
      expect(releases.docs).toHaveLength(1);
      expect(releases.docs[0]).toHaveProperty('release_date');
    });

    it('should handle workflow with devices and reports', async () => {
      const mockDevices = ['Hopper 3'];
      const mockReports = {
        data: {
          docs: [],
          totalDocs: 0,
          page: 1,
          limit: 10,
        },
      };

      mockedAxios.get
        .mockResolvedValueOnce({ data: mockDevices })
        .mockResolvedValueOnce(mockReports);

      const devices = await getAvailableDevices();
      const reports = await getBetaReports({
        page: 1,
        limit: 10,
        device: devices[0],
      });

      expect(devices).toEqual(mockDevices);
      expect(reports.docs).toEqual([]);
    });
  });
});
