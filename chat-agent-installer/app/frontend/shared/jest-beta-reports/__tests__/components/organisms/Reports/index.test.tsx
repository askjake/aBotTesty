import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { getBetaReports } from '@/services/beta-reports.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import { BetaReportType } from '@/types/beta-reports.types';
import { PaginationType } from '@shared/ui/types/pagination.types';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import Reports from '@/components/organisms/Reports';

jest.mock('@/services/beta-reports.services');
jest.mock('@shared/ui/hooks/useHandleError.hook');

// Suppress act warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('Reports Component', () => {
  const mockHandleError = jest.fn();
  const mockGetBetaReports = getBetaReports as jest.MockedFunction<
    typeof getBetaReports
  >;
  const mockComponentRef = { current: null };

  const mockReports: BetaReportType[] = [
    {
      id: 1,
      report_display_id: 'REPORT-001',
      url: 'https://example.com/report1',
      ingest_date: '2025-10-21',
      platform: PlatformEnum.ATV,
      release: 1,
      release_name: 'Release 1.0',
      receiver_id: 'receiver-1',
      hopper_model: 'hopper-model-1',
      hopperp_model: 'hopperp-model-1',
      joey_model: 'joey-model-1',
      hopperp_id: 'hopperp-1',
      joey_id: 'joey-1',
      hopper_software: 'hopper-sw-1',
      hopperp_software: 'hopperp-sw-1',
      joey_software: 'joey-sw-1',
      event_date: '2025-10-21',
      event_time: '2025-10-21T10:00:00Z',
      title: 'Test Report 1',
      detail: 'Detailed information about test report 1',
      marked_log: true,
      has_attachment: true,
      category: 'Bug',
      analysis: 'Analysis of test report 1',
      formalized_report: 'This is a formalized report for test 1',
      related_issue: 'issue-1',
    },
    {
      id: 2,
      report_display_id: 'REPORT-002',
      url: 'https://example.com/report2',
      ingest_date: '2025-10-22',
      platform: PlatformEnum.STB,
      release: 2,
      release_name: 'Release 2.0',
      receiver_id: null,
      hopper_model: null,
      hopperp_model: null,
      joey_model: null,
      hopperp_id: null,
      joey_id: null,
      hopper_software: 'hopper-sw-2',
      hopperp_software: null,
      joey_software: null,
      event_date: '2025-10-22',
      event_time: '2025-10-22T10:00:00Z',
      title: 'Test Report 2',
      detail: 'Detailed information about test report 2',
      marked_log: false,
      has_attachment: false,
      category: 'Feature',
      analysis: 'Analysis of test report 2',
      formalized_report: 'This is a formalized report for test 2',
      related_issue: null,
    },
  ];

  const mockPaginationResponse: PaginationType<BetaReportType> = {
    docs: mockReports,
    totalDocs: 2,
    limit: DEFAULT_PAGE_SIZE,
    page: 1,
    totalPages: 1,
    hasNextPage: false,
    nextPage: 1,
    hasPrevPage: false,
    prevPage: 2,
  };

  const defaultProps = {
    componentRef: mockComponentRef,
    start_date: '2025-10-01',
    end_date: '2025-10-31',
    platform: PlatformEnum.ATV,
    release: 1,
    device: 'test-device',
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useHandleError as jest.Mock).mockReturnValue(mockHandleError);
    mockGetBetaReports.mockResolvedValue(mockPaginationResponse);
  });

  it('renders the component with card title', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeInTheDocument();
    });
  });

  it('loads reports on mount with correct parameters', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        start_date: '2025-10-01',
        end_date: '2025-10-31',
        platform: PlatformEnum.ATV,
        release: 1,
        device: 'test-device',
      });
    });
  });

  it('displays loaded reports in table', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('REPORT-001')).toBeInTheDocument();
      expect(screen.getByText('REPORT-002')).toBeInTheDocument();
    });
  });

  it('renders URLs as clickable links with correct attributes', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      const links = screen.getAllByText('Open link');
      expect(links).toHaveLength(2);
      expect(links[0]).toHaveAttribute('href', 'https://example.com/report1');
      expect(links[0]).toHaveAttribute('target', '_blank');
      expect(links[1]).toHaveAttribute('href', 'https://example.com/report2');
    });
  });

  it('renders has_attachment field with visual indicators', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('✅')).toBeInTheDocument();
      expect(screen.getByText('❌')).toBeInTheDocument();
    });
  });

  it('displays platform enum values correctly', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('AndroidTV')).toBeInTheDocument();
      expect(screen.getByText('DishTV')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully', async () => {
    const error = new Error('API Error');
    mockGetBetaReports.mockRejectedValueOnce(error);

    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(error);
    });
  });

  it('renders empty table when no reports are returned', async () => {
    const emptyResponse: PaginationType<BetaReportType> = {
      docs: [],
      totalDocs: 0,
      limit: DEFAULT_PAGE_SIZE,
      page: 1,
      totalPages: 0,
      hasNextPage: false,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 2,
    };

    mockGetBetaReports.mockResolvedValueOnce(emptyResponse);

    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Reports')).toBeInTheDocument();
    });

    expect(screen.queryByText('REPORT-001')).not.toBeInTheDocument();
  });

  it('handles null values in report fields without crashing', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('REPORT-002')).toBeInTheDocument();
      expect(screen.getByText('hopper-sw-2')).toBeInTheDocument();
    });
  });

  it('reloads data when start_date changes', async () => {
    const { rerender } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    mockGetBetaReports.mockClear();
    rerender(<Reports {...defaultProps} start_date='2025-11-01' />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith(
        expect.objectContaining({
          start_date: '2025-11-01',
        }),
      );
    });
  });

  it('reloads data when end_date changes', async () => {
    const { rerender } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    mockGetBetaReports.mockClear();
    rerender(<Reports {...defaultProps} end_date='2025-11-30' />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith(
        expect.objectContaining({
          end_date: '2025-11-30',
        }),
      );
    });
  });

  it('reloads data when platform filter changes', async () => {
    const { rerender } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    mockGetBetaReports.mockClear();
    rerender(<Reports {...defaultProps} platform={PlatformEnum.STB} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith(
        expect.objectContaining({
          platform: PlatformEnum.STB,
        }),
      );
    });
  });

  it('reloads data when release changes', async () => {
    const { rerender } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    mockGetBetaReports.mockClear();
    rerender(<Reports {...defaultProps} release={2} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith(
        expect.objectContaining({
          release: 2,
        }),
      );
    });
  });

  it('reloads data when device changes', async () => {
    const { rerender } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    mockGetBetaReports.mockClear();
    rerender(<Reports {...defaultProps} device='new-device' />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith(
        expect.objectContaining({
          device: 'new-device',
        }),
      );
    });
  });

  it('applies custom className to card', async () => {
    const { container } = renderLayout(
      <Reports {...defaultProps} className='custom-class' />,
    );

    await waitFor(() => {
      const card = container.querySelector('.reports');
      expect(card).toHaveClass('custom-class');
    });
  });

  it('passes additional props to Card component', async () => {
    renderLayout(<Reports {...defaultProps} data-testid='custom-card' />);

    await waitFor(() => {
      expect(screen.getByTestId('custom-card')).toBeInTheDocument();
    });
  });

  it('uses id as row key', async () => {
    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      const rows = container.querySelectorAll(
        'tbody tr:not(.ant-table-measure-row)',
      );
      expect(rows.length).toBeGreaterThan(0);
      expect(rows[0]).toHaveAttribute('data-row-key', '1');
      expect(rows[1]).toHaveAttribute('data-row-key', '2');
    });
  });

  it('displays formalized_report content', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(
        screen.getByText('This is a formalized report for test 1'),
      ).toBeInTheDocument();
      expect(
        screen.getByText('This is a formalized report for test 2'),
      ).toBeInTheDocument();
    });
  });

  it('exposes refetchData method via ref', async () => {
    const ref = React.createRef<any>();
    renderLayout(<Reports {...defaultProps} componentRef={ref} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    expect(ref.current).toBeTruthy();
    expect(ref.current.refetchData).toBeInstanceOf(Function);
  });

  it('refetchData reloads reports from page 1', async () => {
    const ref = React.createRef<any>();
    renderLayout(<Reports {...defaultProps} componentRef={ref} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.getByText('REPORT-001')).toBeInTheDocument();
    });

    mockGetBetaReports.mockClear();

    await ref.current.refetchData();

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalledWith({
        page: 1,
        limit: DEFAULT_PAGE_SIZE,
        start_date: '2025-10-01',
        end_date: '2025-10-31',
        platform: PlatformEnum.ATV,
        release: 1,
        device: 'test-device',
      });
    });
  });

  it('updates pagination total when data is loaded', async () => {
    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(mockGetBetaReports).toHaveBeenCalled();
    });

    await waitFor(() => {
      const pagination = container.querySelector('.ant-pagination');
      expect(pagination).toBeInTheDocument();
    });
  });

  it('renders table with sticky header', async () => {
    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(container.querySelector('table')).toBeInTheDocument();
    });
  });

  it('renders table with horizontal scroll', async () => {
    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      const table = container.querySelector('.ant-table');
      expect(table).toBeInTheDocument();
    });
  });

  it('shows loading state while fetching', async () => {
    let resolvePromise: (value: any) => void;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });
    mockGetBetaReports.mockReturnValue(promise as any);

    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      const loadingIndicator = container.querySelector('.ant-spin');
      expect(loadingIndicator).toBeInTheDocument();
    });

    resolvePromise!(mockPaginationResponse);
  });

  it('renders all column headers', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getAllByText('report_id').length).toBeGreaterThan(0);
      expect(screen.getAllByText('url').length).toBeGreaterThan(0);
      expect(screen.getAllByText('title').length).toBeGreaterThan(0);
      expect(screen.getAllByText('event_time').length).toBeGreaterThan(0);
      expect(screen.getAllByText('category').length).toBeGreaterThan(0);
      expect(screen.getAllByText('formalized_report').length).toBeGreaterThan(
        0,
      );
      expect(screen.getAllByText('release').length).toBeGreaterThan(0);
      expect(screen.getAllByText('ingest_date').length).toBeGreaterThan(0);
      expect(screen.getAllByText('platform').length).toBeGreaterThan(0);
      expect(screen.getAllByText('has_attachment').length).toBeGreaterThan(0);
    });
  });

  it('renders expandable formalized_report text', async () => {
    const { container } = renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      const expandableText = container.querySelector(
        '.ant-typography-ellipsis',
      );
      expect(expandableText).toBeInTheDocument();
    });
  });

  it('displays release_name column', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Release 1.0')).toBeInTheDocument();
      expect(screen.getByText('Release 2.0')).toBeInTheDocument();
    });
  });

  it('does not load reports when release is undefined', async () => {
    const { release, ...propsWithoutRelease } = defaultProps;
    renderLayout(<Reports {...propsWithoutRelease} />);

    await waitFor(() => {
      expect(mockGetBetaReports).not.toHaveBeenCalled();
    });
  });

  it('displays report_display_id instead of internal id', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('REPORT-001')).toBeInTheDocument();
      expect(screen.getByText('REPORT-002')).toBeInTheDocument();
    });
  });

  it('displays titles correctly', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Report 1')).toBeInTheDocument();
      expect(screen.getByText('Test Report 2')).toBeInTheDocument();
    });
  });

  it('displays categories correctly', async () => {
    renderLayout(<Reports {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Bug')).toBeInTheDocument();
      expect(screen.getByText('Feature')).toBeInTheDocument();
    });
  });
});
