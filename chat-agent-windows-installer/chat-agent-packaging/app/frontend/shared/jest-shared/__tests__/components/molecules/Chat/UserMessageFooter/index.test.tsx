import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import UserMessageFooter from '@shared/ui/components/molecules/Chat/UserMessageFooter';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { UserMessageFooterProps } from '@shared/ui/components/molecules/Chat/UserMessageFooter/UserMessageFooter.props';

// Mock Ant Design components
jest.mock('antd', () => ({
  Button: ({ children, onClick, icon, ...props }: any) => (
    <button onClick={onClick} data-testid='edit-button' {...props}>
      {icon && <span data-testid='edit-icon'>Edit Icon</span>}
      {children}
    </button>
  ),
  Flex: ({ children, ...props }: any) => (
    <div data-testid='flex-container' {...props}>
      {children}
    </div>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid='tooltip' title={title}>
      {children}
    </div>
  ),
}));

// Mock VersionsSwitcher component
jest.mock('@shared/ui/components/atoms/VersionsSwitcher', () => {
  return function MockVersionsSwitcher({
    totalVersions,
    currentIndex,
    updateCurrentVersion,
  }: any) {
    return (
      <div data-testid='versions-switcher'>
        <span data-testid='total-versions'>{totalVersions}</span>
        <span data-testid='current-index'>{currentIndex}</span>
        <button
          data-testid='version-change-button'
          onClick={() => updateCurrentVersion(2)}
        >
          Change Version
        </button>
      </div>
    );
  };
});

// Mock react-icons
jest.mock('react-icons/gr', () => ({
  GrEdit: () => <span data-testid='edit-icon'>Edit Icon</span>,
}));

const defaultProps: UserMessageFooterProps = {
  version_count: 1,
  version_index: 0,
  message_id: 'test-message-id',
  onChangeVersion: jest.fn(),
  onToggleEdit: jest.fn(),
  showEditBtn: true,
};

describe('UserMessageFooter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the component with flex container', () => {
      renderLayout(<UserMessageFooter {...defaultProps} />);

      expect(screen.getByTestId('flex-container')).toBeInTheDocument();
    });

    it('renders edit button when showEditBtn is true', () => {
      renderLayout(<UserMessageFooter {...defaultProps} showEditBtn={true} />);

      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
      expect(screen.getByTestId('edit-icon')).toBeInTheDocument();
      expect(screen.getByTestId('tooltip')).toBeInTheDocument();
    });

    it('does not render edit button when showEditBtn is false', () => {
      renderLayout(<UserMessageFooter {...defaultProps} showEditBtn={false} />);

      expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
      expect(screen.queryByTestId('tooltip')).not.toBeInTheDocument();
    });

    it('renders versions switcher when version_count > 1 and showEditBtn is true', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={3}
          version_index={1}
          showEditBtn={true}
        />,
      );

      expect(screen.getByTestId('versions-switcher')).toBeInTheDocument();
      expect(screen.getByTestId('total-versions')).toHaveTextContent('3');
      expect(screen.getByTestId('current-index')).toHaveTextContent('1');
    });

    it('does not render versions switcher when version_count is 1', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={1}
          showEditBtn={true}
        />,
      );

      expect(screen.queryByTestId('versions-switcher')).not.toBeInTheDocument();
    });

    it('does not render versions switcher when showEditBtn is false even if version_count > 1', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={3}
          showEditBtn={false}
        />,
      );

      expect(screen.queryByTestId('versions-switcher')).not.toBeInTheDocument();
    });

    it('renders tooltip with correct title for edit button', () => {
      renderLayout(<UserMessageFooter {...defaultProps} showEditBtn={true} />);

      const tooltip = screen.getByTestId('tooltip');
      expect(tooltip).toHaveAttribute('title', 'Edit message');
    });

    it('renders with dark theme', () => {
      renderLayout(<UserMessageFooter {...defaultProps} />, { theme: 'dark' });

      expect(screen.getByTestId('flex-container')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('calls onToggleEdit with message_id when edit button is clicked', () => {
      const mockOnToggleEdit = jest.fn();

      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          onToggleEdit={mockOnToggleEdit}
          message_id='test-message-123'
          showEditBtn={true}
        />,
      );

      fireEvent.click(screen.getByTestId('edit-button'));

      expect(mockOnToggleEdit).toHaveBeenCalledTimes(1);
      expect(mockOnToggleEdit).toHaveBeenCalledWith('test-message-123');
    });

    it('calls onChangeVersion with correct parameters when version is changed', () => {
      const mockOnChangeVersion = jest.fn();

      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          onChangeVersion={mockOnChangeVersion}
          version_count={3}
          version_index={1}
          message_id='test-message-456'
          showEditBtn={true}
        />,
      );

      fireEvent.click(screen.getByTestId('version-change-button'));

      expect(mockOnChangeVersion).toHaveBeenCalledTimes(1);
      expect(mockOnChangeVersion).toHaveBeenCalledWith({
        message_id: 'test-message-456',
        version_index: 2,
      });
    });

    it('does not call onToggleEdit when edit button is not rendered', () => {
      const mockOnToggleEdit = jest.fn();

      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          onToggleEdit={mockOnToggleEdit}
          showEditBtn={false}
        />,
      );

      // Edit button should not be present
      expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();
      expect(mockOnToggleEdit).not.toHaveBeenCalled();
    });
  });

  describe('Conditional Rendering Logic', () => {
    it('renders both versions switcher and edit button when conditions are met', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={5}
          version_index={2}
          showEditBtn={true}
        />,
      );

      expect(screen.getByTestId('versions-switcher')).toBeInTheDocument();
      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
    });

    it('renders only edit button when version_count is 1', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={1}
          showEditBtn={true}
        />,
      );

      expect(screen.queryByTestId('versions-switcher')).not.toBeInTheDocument();
      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
    });

    it('renders nothing when showEditBtn is false and version_count is 1', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={1}
          showEditBtn={false}
        />,
      );

      expect(screen.queryByTestId('versions-switcher')).not.toBeInTheDocument();
      expect(screen.queryByTestId('edit-button')).not.toBeInTheDocument();

      // Only the flex container should be present
      expect(screen.getByTestId('flex-container')).toBeInTheDocument();
    });
  });

  describe('Props Validation', () => {
    it('handles zero version_count correctly', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={0}
          showEditBtn={true}
        />,
      );

      expect(screen.queryByTestId('versions-switcher')).not.toBeInTheDocument();
      expect(screen.getByTestId('edit-button')).toBeInTheDocument();
    });

    it('handles negative version_index correctly', () => {
      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          version_count={3}
          version_index={-1}
          showEditBtn={true}
        />,
      );

      expect(screen.getByTestId('versions-switcher')).toBeInTheDocument();
      expect(screen.getByTestId('current-index')).toHaveTextContent('-1');
    });

    it('handles empty message_id correctly', () => {
      const mockOnToggleEdit = jest.fn();

      renderLayout(
        <UserMessageFooter
          {...defaultProps}
          message_id=''
          onToggleEdit={mockOnToggleEdit}
          showEditBtn={true}
        />,
      );

      fireEvent.click(screen.getByTestId('edit-button'));

      expect(mockOnToggleEdit).toHaveBeenCalledWith('');
    });
  });

  describe('Button Properties', () => {
    it('renders edit button with correct properties', () => {
      renderLayout(<UserMessageFooter {...defaultProps} showEditBtn={true} />);

      const editButton = screen.getByTestId('edit-button');

      // Check if button has the expected attributes from Ant Design Button props
      expect(editButton).toBeInTheDocument();
      expect(screen.getByTestId('edit-icon')).toBeInTheDocument();
    });
  });
});
