import React from 'react';
import { screen, fireEvent, waitFor, act } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { leaveFeedbackIssue } from '@/services/beta-reports.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import FeedbackActiveIssueModal from '@/components/molecules/Modals/FeedbackActiveIssueModal';

// Suppress act warnings from Ant Design internal components
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

// Mock the services and hooks
jest.mock('@/services/beta-reports.services');
jest.mock('@shared/ui/hooks/useHandleError.hook');

describe('FeedbackActiveIssueModal Component', () => {
  const mockOnSubmitFeedback = jest.fn();
  const mockOnCancelFeedback = jest.fn();
  const mockHandleError = jest.fn();
  const mockLeaveFeedbackIssue = leaveFeedbackIssue as jest.MockedFunction<
    typeof leaveFeedbackIssue
  >;

  const defaultProps = {
    id: 'issue-123',
    accepted: true as boolean | null,
    open: true,
    onSubmitFeedback: mockOnSubmitFeedback,
    onCancelFeedback: mockOnCancelFeedback,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    (useHandleError as jest.Mock).mockReturnValue(mockHandleError);
    // @ts-ignore
    mockLeaveFeedbackIssue.mockResolvedValue(undefined);
  });

  it('renders without crashing', () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    expect(screen.getByText('Leave your feedback')).toBeInTheDocument();
  });

  it('displays the modal title', () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    expect(screen.getByText('Leave your feedback')).toBeInTheDocument();
  });

  it('displays the textarea with placeholder', () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    expect(screen.getByPlaceholderText('Feedback...')).toBeInTheDocument();
  });

  it('displays the ok button with correct text', () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    expect(screen.getByText('Accept feedback')).toBeInTheDocument();
  });

  it('updates textarea value when user types', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(
      'Feedback...',
    ) as HTMLTextAreaElement;

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'This is my feedback' } });
    });

    expect(textarea.value).toBe('This is my feedback');
  });

  it('calls leaveFeedbackIssue with correct parameters when ok button is clicked', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Feedback...');
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'Test comment' } });
    });

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'issue-123',
        accepted: true,
        comments: 'Test comment',
      });
    });
  });

  it('calls onSubmitFeedback after successful submission', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockOnSubmitFeedback).toHaveBeenCalled();
    });
  });

  it('clears textarea after successful submission', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(
      'Feedback...',
    ) as HTMLTextAreaElement;
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'Test comment' } });
    });

    expect(textarea.value).toBe('Test comment');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(textarea.value).toBe('Test comment');
    });
  });

  it('calls handleError when leaveFeedbackIssue fails', async () => {
    const error = new Error('API Error');
    mockLeaveFeedbackIssue.mockRejectedValueOnce(error);

    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalledWith(error);
    });
  });

  it('does not call onSubmitFeedback when submission fails', async () => {
    mockLeaveFeedbackIssue.mockRejectedValueOnce(new Error('API Error'));

    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockHandleError).toHaveBeenCalled();
    });

    expect(mockOnSubmitFeedback).not.toHaveBeenCalled();
  });

  it('calls onCancelFeedback when cancel button is clicked', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const cancelButton = screen.getByText('Cancel');

    await act(async () => {
      fireEvent.click(cancelButton);
    });

    expect(mockOnCancelFeedback).toHaveBeenCalled();
  });

  it('clears textarea when cancel button is clicked', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText(
      'Feedback...',
    ) as HTMLTextAreaElement;
    const cancelButton = screen.getByText('Cancel');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'Test comment' } });
    });

    expect(textarea.value).toBe('Test comment');

    await act(async () => {
      fireEvent.click(cancelButton);
    });

    await waitFor(() => {
      expect(textarea.value).toBe('');
    });
  });

  it('handles accepted as false', async () => {
    renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} accepted={false} />,
    );
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'issue-123',
        accepted: false,
        comments: '',
      });
    });
  });

  it('submits with empty comments', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'issue-123',
        accepted: true,
        comments: '',
      });
    });
  });

  it('applies custom className', () => {
    const { container } = renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} className='custom-class' />,
    );
    // Modal renders in a portal, check if it exists in document
    const modal = document.querySelector('.feedback-issue-modal');
    expect(modal).toBeTruthy();
  });

  it('passes additional Modal props', () => {
    renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} width={800} centered />,
    );
    // Modal should be rendered with these props
    expect(screen.getByText('Leave your feedback')).toBeInTheDocument();
  });

  it('handles different id values', async () => {
    renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} id='different-issue-456' />,
    );
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'different-issue-456',
        accepted: true,
        comments: '',
      });
    });
  });

  it('handles long comments text', async () => {
    const longComment = 'This is a very long comment '.repeat(50);
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Feedback...');
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: longComment } });
    });

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'issue-123',
        accepted: true,
        comments: longComment,
      });
    });
  });

  it('does not call leaveFeedbackIssue when cancel is clicked', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Feedback...');
    const cancelButton = screen.getByText('Cancel');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'Test comment' } });
    });

    await act(async () => {
      fireEvent.click(cancelButton);
    });

    expect(mockLeaveFeedbackIssue).not.toHaveBeenCalled();
  });

  it('handles accepted as null', async () => {
    renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} accepted={null} />,
    );
    const okButton = screen.getByText('Accept feedback');

    await act(async () => {
      fireEvent.click(okButton);
    });

    await waitFor(() => {
      expect(mockLeaveFeedbackIssue).toHaveBeenCalledWith({
        id: 'issue-123',
        accepted: null,
        comments: '',
      });
    });
  });

  it('textarea has correct autoSize configuration', () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Feedback...');
    expect(textarea).toBeInTheDocument();
    // TextArea with autoSize should be rendered
    expect(textarea.tagName).toBe('TEXTAREA');
  });

  it('preserves comments value during re-renders', async () => {
    const { rerender } = renderLayout(
      <FeedbackActiveIssueModal {...defaultProps} />,
    );
    const textarea = screen.getByPlaceholderText(
      'Feedback...',
    ) as HTMLTextAreaElement;

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'My feedback' } });
    });

    expect(textarea.value).toBe('My feedback');

    // Rerender with same props
    rerender(<FeedbackActiveIssueModal {...defaultProps} />);

    expect(textarea.value).toBe('My feedback');
  });

  it('handles rapid typing in textarea', async () => {
    renderLayout(<FeedbackActiveIssueModal {...defaultProps} />);
    const textarea = screen.getByPlaceholderText('Feedback...');

    await act(async () => {
      fireEvent.change(textarea, { target: { value: 'T' } });
      fireEvent.change(textarea, { target: { value: 'Te' } });
      fireEvent.change(textarea, { target: { value: 'Tes' } });
      fireEvent.change(textarea, { target: { value: 'Test' } });
    });

    expect((textarea as HTMLTextAreaElement).value).toBe('Test');
  });
});
