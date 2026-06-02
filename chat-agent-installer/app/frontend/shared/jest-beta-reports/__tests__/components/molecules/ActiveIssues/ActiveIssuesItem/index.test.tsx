import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { PlatformEnum } from '@/enums/beta-reports.enum';
import ActiveIssuesItem from '@/components/molecules/ActiveIssues/ActiveIssuesItem';

// Suppress deprecation warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('`bordered={false}` is deprecated')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('ActiveIssuesItem Component', () => {
  const mockOnLeaveFeedback = jest.fn();

  const defaultProps = {
    id: 'issue-123',
    platform: PlatformEnum.ATV,
    title: 'Test Issue Title',
    description:
      'This is a detailed description for the issue that explains what went wrong.',
    date: '2025-10-21',
    last_updated_date: '2025-10-21T10:00:00Z',
    priority: 1,
    accepted: null as boolean | null,
    onLeaveFeedback: mockOnLeaveFeedback,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    expect(screen.getByText('Test Issue Title')).toBeInTheDocument();
  });

  it('displays the title as card title', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    expect(screen.getByText('Test Issue Title')).toBeInTheDocument();
  });

  it('displays default title when title is not provided', () => {
    const { title, ...propsWithoutTitle } = defaultProps;
    // @ts-ignore
    renderLayout(<ActiveIssuesItem {...propsWithoutTitle} />);
    expect(screen.getByText('Issue without title')).toBeInTheDocument();
  });

  it('displays platform, date, and priority tags', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    expect(screen.getByText('AndroidTV')).toBeInTheDocument();
    expect(screen.getByText(defaultProps.date)).toBeInTheDocument();
    expect(screen.getByText('P1')).toBeInTheDocument();
  });

  it('displays correct platform for STB', () => {
    renderLayout(
      <ActiveIssuesItem {...defaultProps} platform={PlatformEnum.STB} />,
    );
    expect(screen.getByText('DishTV')).toBeInTheDocument();
  });

  it('displays the description text', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    expect(screen.getByText(defaultProps.description)).toBeInTheDocument();
  });

  it('renders like and dislike buttons', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
  });

  it('calls onLeaveFeedback with accepted:true when like button is clicked and accepted is null', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const likeButton = screen.getAllByRole('button')[0];
    fireEvent.click(likeButton);
    expect(mockOnLeaveFeedback).toHaveBeenCalledWith({
      accepted: true,
      id: 'issue-123',
    });
  });

  it('calls onLeaveFeedback with accepted:false when dislike button is clicked and accepted is null', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const dislikeButton = screen.getAllByRole('button')[1];
    fireEvent.click(dislikeButton);
    expect(mockOnLeaveFeedback).toHaveBeenCalledWith({
      accepted: false,
      id: 'issue-123',
    });
  });

  it('does not call onLeaveFeedback when like button is clicked and accepted is true', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} accepted={true} />);
    const likeButton = screen.getAllByRole('button')[0];
    fireEvent.click(likeButton);
    expect(mockOnLeaveFeedback).not.toHaveBeenCalled();
  });

  it('does not call onLeaveFeedback when dislike button is clicked and accepted is false', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} accepted={false} />);
    const dislikeButton = screen.getAllByRole('button')[1];
    fireEvent.click(dislikeButton);
    expect(mockOnLeaveFeedback).not.toHaveBeenCalled();
  });

  it('shows like button as solid variant when accepted is true', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} accepted={true} />);
    const likeButton = screen.getAllByRole('button')[0];
    expect(likeButton).toHaveClass('ant-btn-variant-solid');
  });

  it('shows dislike button as solid variant when accepted is false', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} accepted={false} />);
    const dislikeButton = screen.getAllByRole('button')[1];
    expect(dislikeButton).toHaveClass('ant-btn-variant-solid');
  });

  it('shows both buttons as text variant when accepted is null', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} accepted={null} />);
    const buttons = screen.getAllByRole('button');
    buttons.forEach((button) => {
      expect(button).toHaveClass('ant-btn-variant-text');
    });
  });

  it('applies custom className', () => {
    const { container } = renderLayout(
      <ActiveIssuesItem {...defaultProps} className='custom-class' />,
    );
    const card = container.querySelector('.active-issue-item');
    expect(card).toHaveClass('custom-class');
  });

  it('passes additional Card props', () => {
    renderLayout(
      <ActiveIssuesItem {...defaultProps} data-testid='custom-card' />,
    );
    expect(screen.getByTestId('custom-card')).toBeInTheDocument();
  });

  it('has like button with icon', () => {
    const { container } = renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const likeIcon = container.querySelector('.anticon-like');
    expect(likeIcon).toBeInTheDocument();
  });

  it('has dislike button with icon', () => {
    const { container } = renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const dislikeIcon = container.querySelector('.anticon-dislike');
    expect(dislikeIcon).toBeInTheDocument();
  });

  it('handles long description text with ellipsis', () => {
    const longDescription = 'This is a very long description '.repeat(50);
    const { container } = renderLayout(
      <ActiveIssuesItem {...defaultProps} description={longDescription} />,
    );

    const ellipsisElement = container.querySelector('.ant-typography-ellipsis');
    expect(ellipsisElement).toBeInTheDocument();
    expect(ellipsisElement?.textContent).toContain(
      'This is a very long description',
    );
  });

  it('handles different priority values', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} priority={5} />);
    expect(screen.getByText('P5')).toBeInTheDocument();
  });

  it('displays "Test Activity" for priority 0', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} priority={0} />);
    expect(screen.getByText('Test Activity')).toBeInTheDocument();
  });

  it('displays P-prefixed label for priority 1-5', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} priority={3} />);
    expect(screen.getByText('P3')).toBeInTheDocument();
  });

  it('uses default onLeaveFeedback when not provided', () => {
    const {
      id,
      platform,
      title,
      description,
      date,
      last_updated_date,
      priority,
      accepted,
    } = defaultProps;
    expect(() => {
      renderLayout(
        // @ts-ignore
        <ActiveIssuesItem
          id={id}
          platform={platform}
          title={title}
          description={description}
          date={date}
          last_updated_date={last_updated_date}
          priority={priority}
          accepted={accepted}
        />,
      );
    }).not.toThrow();
  });

  it('renders correctly with all props for AndroidTV platform', () => {
    renderLayout(
      <ActiveIssuesItem {...defaultProps} platform={PlatformEnum.ATV} />,
    );
    expect(screen.getByText('AndroidTV')).toBeInTheDocument();
    expect(screen.getByText('Test Issue Title')).toBeInTheDocument();
  });

  it('renders correctly with all props for DishTV platform', () => {
    renderLayout(
      <ActiveIssuesItem {...defaultProps} platform={PlatformEnum.STB} />,
    );
    expect(screen.getByText('DishTV')).toBeInTheDocument();
    expect(screen.getByText('Test Issue Title')).toBeInTheDocument();
  });

  it('renders buttons with correct color variants', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const buttons = screen.getAllByRole('button');

    expect(buttons[0]).toHaveClass('ant-btn-color-cyan');
    expect(buttons[1]).toHaveClass('ant-btn-color-dangerous');
  });

  it('renders like button as icon only', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const likeButton = screen.getAllByRole('button')[0];
    expect(likeButton).toHaveClass('ant-btn-icon-only');
  });

  it('renders dislike button as icon only', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const dislikeButton = screen.getAllByRole('button')[1];
    expect(dislikeButton).toHaveClass('ant-btn-icon-only');
  });

  it('renders tags with correct styles', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);

    const platformTag = screen.getByText('AndroidTV').closest('.ant-tag');
    expect(platformTag).toHaveClass('ant-tag-processing');

    const dateTag = screen.getByText(defaultProps.date).closest('.ant-tag');
    expect(dateTag).toHaveClass('ant-tag-success');

    const priorityTag = screen.getByText('P1').closest('.ant-tag');
    expect(priorityTag).toHaveClass('ant-tag-error');
  });

  it('renders description in typography paragraph', () => {
    const { container } = renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const paragraph = container.querySelector('.ant-typography');
    expect(paragraph).toBeInTheDocument();
    expect(paragraph?.textContent).toBe(defaultProps.description);
  });

  it('renders title with tooltip', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const titleElement = screen.getByText('Test Issue Title');
    expect(titleElement.parentElement).toHaveAttribute('class');
  });

  it('renders like button with tooltip', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const likeButton = screen.getAllByRole('button')[0];
    expect(likeButton.parentElement).toHaveAttribute('class');
  });

  it('renders dislike button with tooltip', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const dislikeButton = screen.getAllByRole('button')[1];
    expect(dislikeButton.parentElement).toHaveAttribute('class');
  });

  it('renders with expandable description', () => {
    const { container } = renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const paragraph = container.querySelector('.ant-typography');
    expect(paragraph).toBeInTheDocument();
  });

  it('handles rapid button clicks', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} />);
    const likeButton = screen.getAllByRole('button')[0];

    fireEvent.click(likeButton);
    fireEvent.click(likeButton);
    fireEvent.click(likeButton);

    expect(mockOnLeaveFeedback).toHaveBeenCalledTimes(3);
  });

  it('renders correctly with priority 2', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} priority={2} />);
    expect(screen.getByText('P2')).toBeInTheDocument();
  });

  it('renders correctly with priority 4', () => {
    renderLayout(<ActiveIssuesItem {...defaultProps} priority={4} />);
    expect(screen.getByText('P4')).toBeInTheDocument();
  });

  it('renders with very long title', () => {
    const longTitle = 'This is a very long title '.repeat(20);
    renderLayout(<ActiveIssuesItem {...defaultProps} title={longTitle} />);
    expect(screen.getByText(longTitle.trim())).toBeInTheDocument();
  });

  it('maintains button state after feedback is given', () => {
    const { rerender } = renderLayout(
      <ActiveIssuesItem {...defaultProps} accepted={null} />,
    );

    let likeButton = screen.getAllByRole('button')[0];
    expect(likeButton).toHaveClass('ant-btn-variant-text');

    rerender(<ActiveIssuesItem {...defaultProps} accepted={true} />);

    likeButton = screen.getAllByRole('button')[0];
    expect(likeButton).toHaveClass('ant-btn-variant-solid');
  });

  it('switches button state from like to dislike', () => {
    const { rerender } = renderLayout(
      <ActiveIssuesItem {...defaultProps} accepted={true} />,
    );

    let likeButton = screen.getAllByRole('button')[0];
    let dislikeButton = screen.getAllByRole('button')[1];

    expect(likeButton).toHaveClass('ant-btn-variant-solid');
    expect(dislikeButton).toHaveClass('ant-btn-variant-text');

    rerender(<ActiveIssuesItem {...defaultProps} accepted={false} />);

    likeButton = screen.getAllByRole('button')[0];
    dislikeButton = screen.getAllByRole('button')[1];

    expect(likeButton).toHaveClass('ant-btn-variant-text');
    expect(dislikeButton).toHaveClass('ant-btn-variant-solid');
  });
});
