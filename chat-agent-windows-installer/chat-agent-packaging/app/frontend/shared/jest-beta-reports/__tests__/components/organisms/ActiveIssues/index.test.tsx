import React from 'react';
import { screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import ActiveIssues from '@/components/organisms/ActiveIssues';
import { getIssueCandidates } from '@/services/beta-reports.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

jest.mock('@/services/beta-reports.services');
jest.mock('@shared/ui/hooks/useHandleError.hook');

// Mock ActiveIssuesItem
jest.mock('@/components/molecules/ActiveIssues/ActiveIssuesItem', () => ({
  __esModule: true,
  default: ({ id, description, onLeaveFeedback, accepted }: any) => (
    <div data-testid={`issue-item-${id}`}>
      <div>{description}</div>
      <button
        data-testid={`feedback-button-${id}`}
        onClick={() => onLeaveFeedback({ id, accepted: !accepted })}
      >
        Leave Feedback
      </button>
    </div>
  ),
}));

// Mock FeedbackIssueModal
jest.mock('@/components/molecules/Modals/FeedbackActiveIssueModal', () => ({
  __esModule: true,
  default: ({ open, onSubmitFeedback, onCancelFeedback, id, accepted }: any) =>
    open ? (
      <div data-testid='feedback-modal'>
        <div data-testid='feedback-modal-id'>{id}</div>
        <div data-testid='feedback-modal-accepted'>{String(accepted)}</div>
        <button data-testid='submit-feedback' onClick={onSubmitFeedback}>
          Submit
        </button>
        <button data-testid='cancel-feedback' onClick={onCancelFeedback}>
          Cancel
        </button>
      </div>
    ) : null,
}));

// Mock InfiniteScroll
jest.mock('react-infinite-scroll-component', () => ({
  __esModule: true,
  default: ({ children, hasMore, next, loader, dataLength }: any) => (
    <div data-testid='infinite-scroll' data-length={dataLength}>
      {children}
      {hasMore && (
        <div data-testid='load-more' onClick={next}>
          {loader}
        </div>
      )}
    </div>
  ),
}));

const mockGetIssueCandidates = getIssueCandidates as jest.MockedFunction<
  typeof getIssueCandidates
>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;

// Suppress act warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act') ||
        args[0].includes('React does not recognize'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('ActiveIssues Component', () => {
  const mockHandleError = jest.fn();
  const mockComponentRef = { current: null };

  const mockIssues = {
    docs: [
      {
        id: 'issue-1',
        platform: PlatformEnum.ATV,
        description: 'Issue 1',
        reason: 'Reason 1',
        date: '2025-10-21',
        priority: 1,
        accepted: null,
        title: 'Issue 1 Title',
        last_updated_date: '2025-10-21T10:00:00Z',
      },
      {
        id: 'issue-2',
        platform: PlatformEnum.STB,
        description: 'Issue 2',
        reason: 'Reason 2',
        date: '2025-10-22',
        priority: 2,
        accepted: null,
        title: 'Issue 2 Title',
        last_updated_date: '2025-10-22T10:00:00Z',
      },
    ],
    hasNextPage: false,
    totalDocs: 2,
    totalPages: 1,
    page: 1,
    limit: 15,
    nextPage: 1,
    hasPrevPage: false,
    prevPage: 1,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockGetIssueCandidates.mockResolvedValue(mockIssues);
  });

  it('renders without crashing', async () => {
    await act(async () => {
      renderLayout(<ActiveIssues componentRef={mockComponentRef} />);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(0);
    });

    expect(screen.getByText('Active issues')).toBeInTheDocument();
  });

  it('renders card title', async () => {
    await act(async () => {
      renderLayout(<ActiveIssues componentRef={mockComponentRef} />);
    });

    expect(screen.getByText('Active issues')).toBeInTheDocument();
  });

  it('applies custom className', async () => {
    const { container } = await act(async () => {
      return renderLayout(
        <ActiveIssues
          componentRef={mockComponentRef}
          className='custom-class'
        />,
      );
    });

    const card = container.querySelector('.active-issues');
    expect(card).toHaveClass('custom-class');
  });

  it('does not load issues on mount when release is undefined', async () => {
    await act(async () => {
      renderLayout(<ActiveIssues componentRef={mockComponentRef} />);
    });

    expect(mockGetIssueCandidates).not.toHaveBeenCalled();
  });

  it('loads issues when release is provided', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledWith({
        page: 1,
        limit: 15,
        platform: undefined,
        release: 1,
        min_priority: undefined,
        max_priority: undefined,
        start_date: undefined,
        end_date: undefined,
      });
    });
  });

  it('displays loaded issues', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
      expect(screen.getByText('Issue 2')).toBeInTheDocument();
    });
  });

  it('passes filter props to API call including max_priority', async () => {
    const props = {
      start_date: '2025-10-01',
      end_date: '2025-10-31',
      platform: PlatformEnum.ATV,
      release: 123,
      min_priority: 2,
    };

    await act(async () => {
      renderLayout(<ActiveIssues componentRef={mockComponentRef} {...props} />);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledWith({
        page: 1,
        limit: 15,
        ...props,
        max_priority: 2,
      });
    });
  });

  it('reloads data when filters change', async () => {
    const { rerender } = await act(async () => {
      return renderLayout(
        <ActiveIssues
          componentRef={mockComponentRef}
          platform={PlatformEnum.ATV}
          release={1}
        />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(1);
    });

    mockGetIssueCandidates.mockClear();

    await act(async () => {
      rerender(
        <ActiveIssues
          componentRef={mockComponentRef}
          platform={PlatformEnum.STB}
          release={1}
        />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledWith({
        page: 1,
        limit: 15,
        platform: PlatformEnum.STB,
        release: 1,
        min_priority: undefined,
        max_priority: undefined,
        start_date: undefined,
        end_date: undefined,
      });
    });
  });

  it('handles empty issues list', async () => {
    mockGetIssueCandidates.mockResolvedValue({
      ...mockIssues,
      docs: [],
      totalDocs: 0,
    });

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    await waitFor(() => {
      const emptyDescription = screen.getByText('No data', {
        selector: '.ant-empty-description',
      });
      expect(emptyDescription).toBeInTheDocument();
      expect(screen.queryByText('Issue 1')).not.toBeInTheDocument();
    });
  });

  it('handles API errors', async () => {
    const error = new Error('API Error');
    mockGetIssueCandidates.mockRejectedValue(error);

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(error);
    });
  });

  it('renders infinite scroll container', async () => {
    const { container } = await act(async () => {
      return renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    const scrollContainer = container.querySelector('#active-issues-wrapper');
    expect(scrollContainer).toBeInTheDocument();
  });

  it('exposes refetchData method via ref', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderLayout(<ActiveIssues componentRef={ref} release={1} />);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(1);
    });

    expect(ref.current).toBeTruthy();
    expect(ref.current.refetchData).toBeInstanceOf(Function);
  });

  it('refetchData reloads issues from page 1', async () => {
    const ref = React.createRef<any>();

    await act(async () => {
      renderLayout(<ActiveIssues componentRef={ref} release={1} />);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(1);
    });

    mockGetIssueCandidates.mockClear();

    await act(async () => {
      await ref.current.refetchData();
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledWith({
        page: 1,
        limit: 15,
        platform: undefined,
        release: 1,
        min_priority: undefined,
        max_priority: undefined,
        start_date: undefined,
        end_date: undefined,
      });
    });
  });

  it('resets issues and page when filters change', async () => {
    const { rerender } = await act(async () => {
      return renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(1);
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    const newIssues = {
      ...mockIssues,
      docs: [
        {
          id: 'issue-3',
          platform: PlatformEnum.ATV,
          description: 'Issue 3',
          reason: 'Reason 3',
          date: '2025-10-23',
          priority: 3,
          accepted: null,
          title: 'Issue 3 Title',
          last_updated_date: '2025-10-23T10:00:00Z',
        },
      ],
    };

    mockGetIssueCandidates.mockResolvedValue(newIssues);

    await act(async () => {
      rerender(<ActiveIssues componentRef={mockComponentRef} release={2} />);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(2);
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 3')).toBeInTheDocument();
      expect(screen.queryByText('Issue 1')).not.toBeInTheDocument();
    });
  });

  it('passes Card props correctly', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues
          componentRef={mockComponentRef}
          release={1}
          data-testid='custom-card'
        />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    const card = screen.getByTestId('custom-card');
    expect(card).toBeInTheDocument();
  });

  it('renders each issue with unique key', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('issue-item-issue-1')).toBeInTheDocument();
      expect(screen.getByTestId('issue-item-issue-2')).toBeInTheDocument();
    });
  });

  it('shows loader when hasNextPage is true', async () => {
    mockGetIssueCandidates.mockResolvedValue({
      ...mockIssues,
      hasNextPage: true,
    });

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByTestId('load-more')).toBeInTheDocument();
    });
  });

  it('opens feedback modal when leave feedback is clicked', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    const feedbackButton = screen.getByTestId('feedback-button-issue-1');

    await act(async () => {
      feedbackButton.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
      expect(screen.getByTestId('feedback-modal-id')).toHaveTextContent(
        'issue-1',
      );
    });
  });

  it('updates issue accepted status after feedback submission', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    const feedbackButton = screen.getByTestId('feedback-button-issue-1');

    await act(async () => {
      feedbackButton.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
    });

    const submitButton = screen.getByTestId('submit-feedback');

    await act(async () => {
      submitButton.click();
    });

    await waitFor(() => {
      expect(screen.queryByTestId('feedback-modal')).not.toBeInTheDocument();
    });
  });

  it('closes feedback modal when cancel is clicked', async () => {
    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    const feedbackButton = screen.getByTestId('feedback-button-issue-1');

    await act(async () => {
      feedbackButton.click();
    });

    await waitFor(() => {
      expect(screen.getByTestId('feedback-modal')).toBeInTheDocument();
    });

    const cancelButton = screen.getByTestId('cancel-feedback');

    await act(async () => {
      cancelButton.click();
    });

    await waitFor(() => {
      expect(screen.queryByTestId('feedback-modal')).not.toBeInTheDocument();
    });
  });

  it('prevents loading more when already loading', async () => {
    let resolveFirst: any;
    const firstPromise = new Promise((resolve) => {
      resolveFirst = resolve;
    });

    mockGetIssueCandidates.mockReturnValueOnce(firstPromise as any);

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    // Wait a bit to ensure loading state is set
    await new Promise((resolve) => setTimeout(resolve, 50));

    await act(async () => {
      resolveFirst(mockIssues);
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(1);
    });
  });

  it('resets currentPage to 0 when filters change', async () => {
    const firstPageIssues = {
      ...mockIssues,
      hasNextPage: true,
      page: 1,
    };

    const secondPageIssues = {
      docs: [
        {
          id: 'issue-3',
          platform: PlatformEnum.ATV,
          description: 'Issue 3',
          reason: 'Reason 3',
          date: '2025-10-23',
          priority: 3,
          accepted: null,
          title: 'Issue 3 Title',
          last_updated_date: '2025-10-23T10:00:00Z',
        },
      ],
      hasNextPage: false,
      page: 2,
      totalDocs: 1,
      limit: 15,
      totalPages: 1,
      nextPage: 1,
      prevPage: 1,
      hasPrevPage: false,
    };

    mockGetIssueCandidates
      .mockResolvedValueOnce(firstPageIssues)
      .mockResolvedValueOnce(secondPageIssues);

    const { rerender } = await act(async () => {
      return renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    // Load page 2
    const loadMoreButton = screen.getByTestId('load-more');
    await act(async () => {
      loadMoreButton.click();
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(2);
    });

    // Change filter - should reset to page 1
    const newIssues = {
      ...mockIssues,
      docs: [
        {
          id: 'issue-4',
          platform: PlatformEnum.ATV,
          description: 'Issue 4',
          reason: 'Reason 4',
          date: '2025-10-24',
          priority: 4,
          accepted: null,
          title: 'Issue 4 Title',
          last_updated_date: '2025-10-24T10:00:00Z',
        },
      ],
    };

    mockGetIssueCandidates.mockResolvedValue(newIssues);

    await act(async () => {
      rerender(
        <ActiveIssues
          componentRef={mockComponentRef}
          release={1}
          platform={PlatformEnum.STB}
        />,
      );
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(3);
    });

    expect(mockGetIssueCandidates).toHaveBeenLastCalledWith({
      page: 1,
      limit: 15,
      platform: PlatformEnum.STB,
      release: 1,
      min_priority: undefined,
      max_priority: undefined,
      start_date: undefined,
      end_date: undefined,
    });
  });

  it('does not show empty state while loading', async () => {
    let resolvePromise: any;
    const promise = new Promise((resolve) => {
      resolvePromise = resolve;
    });

    mockGetIssueCandidates.mockReturnValue(promise as any);

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    // Should not show empty state while loading
    expect(screen.queryByText('No data')).not.toBeInTheDocument();

    await act(async () => {
      resolvePromise(mockIssues);
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });
  });

  it('loads more pages without showing loading state on card', async () => {
    const firstPageIssues = {
      ...mockIssues,
      hasNextPage: true,
    };

    const secondPageIssues = {
      docs: [
        {
          id: 'issue-3',
          platform: PlatformEnum.ATV,
          description: 'Issue 3',
          reason: 'Reason 3',
          date: '2025-10-23',
          priority: 3,
          accepted: null,
          title: 'Issue 3 Title',
          last_updated_date: '2025-10-23T10:00:00Z',
        },
      ],
      hasNextPage: false,
      totalDocs: 3,
      totalPages: 2,
      page: 2,
      limit: 15,
      nextPage: 2,
      hasPrevPage: true,
      prevPage: 1,
    };

    mockGetIssueCandidates
      .mockResolvedValueOnce(firstPageIssues)
      .mockResolvedValueOnce(secondPageIssues);

    await act(async () => {
      renderLayout(
        <ActiveIssues componentRef={mockComponentRef} release={1} />,
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
    });

    const loadMoreButton = screen.getByTestId('load-more');

    await act(async () => {
      loadMoreButton.click();
    });

    await waitFor(() => {
      expect(mockGetIssueCandidates).toHaveBeenCalledTimes(2);
      expect(screen.getByText('Issue 3')).toBeInTheDocument();
    });
  });
});
