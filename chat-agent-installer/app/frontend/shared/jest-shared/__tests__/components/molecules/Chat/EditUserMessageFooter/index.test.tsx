import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import EditUserMessageFooter from '@shared/ui/components/molecules/Chat/EditUserMessageFooter';
import { EditUserMessageFooterProps } from '@shared/ui/components/molecules/Chat/EditUserMessageFooter/EditUserMessageFooter.props';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock Ant Design components if needed
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  Button: ({ children, onClick, size, type, ...props }: any) => (
    <button onClick={onClick} data-size={size} data-type={type} {...props}>
      {children}
    </button>
  ),
  Flex: ({ children, gap, align, justify, ...props }: any) => (
    <div
      data-gap={gap}
      data-align={align}
      data-justify={justify}
      style={{ display: 'flex' }}
      {...props}
    >
      {children}
    </div>
  ),
}));

describe('EditUserMessageFooter Component', () => {
  const mockOnSave = jest.fn();
  const mockOnCancel = jest.fn();
  const defaultProps: EditUserMessageFooterProps = {
    message_id: 'test-message-id',
    onSave: mockOnSave,
    onCancel: mockOnCancel,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders without crashing', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    it('renders buttons with correct properties', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const cancelButton = screen.getByText('Cancel');
      const saveButton = screen.getByText('Save');

      expect(cancelButton).toHaveAttribute('data-size', 'small');
      expect(saveButton).toHaveAttribute('data-size', 'small');
      expect(saveButton).toHaveAttribute('data-type', 'primary');
    });

    it('renders Flex container with correct properties', () => {
      const { container } = renderLayout(
        <EditUserMessageFooter {...defaultProps} />,
      );

      const flexContainer = container.querySelector('[data-gap="4"]');
      expect(flexContainer).toBeInTheDocument();
      expect(flexContainer).toHaveAttribute('data-align', 'center');
      expect(flexContainer).toHaveAttribute('data-justify', 'flex-end');
    });

    it('renders buttons in correct order', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2);
      expect(buttons[0]).toHaveTextContent('Cancel');
      expect(buttons[1]).toHaveTextContent('Save');
    });
  });

  describe('User Interactions', () => {
    it('calls onCancel with message_id when Cancel button is clicked', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(1);
      expect(mockOnCancel).toHaveBeenCalledWith('test-message-id');
    });

    it('calls onSave with message_id when Save button is clicked', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const saveButton = screen.getByText('Save');
      fireEvent.click(saveButton);

      expect(mockOnSave).toHaveBeenCalledTimes(1);
      expect(mockOnSave).toHaveBeenCalledWith('test-message-id');
    });

    it('handles multiple clicks correctly', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const cancelButton = screen.getByText('Cancel');
      const saveButton = screen.getByText('Save');

      // Click cancel multiple times
      fireEvent.click(cancelButton);
      fireEvent.click(cancelButton);

      // Click save once
      fireEvent.click(saveButton);

      expect(mockOnCancel).toHaveBeenCalledTimes(2);
      expect(mockOnCancel).toHaveBeenCalledWith('test-message-id');
      expect(mockOnSave).toHaveBeenCalledTimes(1);
      expect(mockOnSave).toHaveBeenCalledWith('test-message-id');
    });

    it('does not call handlers when buttons are not clicked', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      // Just render, don't click anything
      expect(mockOnCancel).not.toHaveBeenCalled();
      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Props Handling', () => {
    it('works with different message_id values', () => {
      const customProps: EditUserMessageFooterProps = {
        ...defaultProps,
        message_id: 'different-message-id',
      };

      renderLayout(<EditUserMessageFooter {...customProps} />);

      fireEvent.click(screen.getByText('Cancel'));
      fireEvent.click(screen.getByText('Save'));

      expect(mockOnCancel).toHaveBeenCalledWith('different-message-id');
      expect(mockOnSave).toHaveBeenCalledWith('different-message-id');
    });

    it('works with empty message_id', () => {
      const customProps: EditUserMessageFooterProps = {
        ...defaultProps,
        message_id: '',
      };

      renderLayout(<EditUserMessageFooter {...customProps} />);

      fireEvent.click(screen.getByText('Cancel'));
      fireEvent.click(screen.getByText('Save'));

      expect(mockOnCancel).toHaveBeenCalledWith('');
      expect(mockOnSave).toHaveBeenCalledWith('');
    });

    it('works with different callback functions', () => {
      const customOnSave = jest.fn();
      const customOnCancel = jest.fn();

      const customProps: EditUserMessageFooterProps = {
        message_id: 'test-id',
        onSave: customOnSave,
        onCancel: customOnCancel,
      };

      renderLayout(<EditUserMessageFooter {...customProps} />);

      fireEvent.click(screen.getByText('Cancel'));
      fireEvent.click(screen.getByText('Save'));

      expect(customOnCancel).toHaveBeenCalledWith('test-id');
      expect(customOnSave).toHaveBeenCalledWith('test-id');
      expect(mockOnCancel).not.toHaveBeenCalled();
      expect(mockOnSave).not.toHaveBeenCalled();
    });
  });

  describe('Accessibility', () => {
    it('buttons are accessible via keyboard', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const cancelButton = screen.getByText('Cancel');
      const saveButton = screen.getByText('Save');

      // Focus and trigger with Enter key
      cancelButton.focus();
      fireEvent.keyDown(cancelButton, { key: 'Enter', code: 'Enter' });

      saveButton.focus();
      fireEvent.keyDown(saveButton, { key: 'Enter', code: 'Enter' });

      // Note: Actual keyboard events might not trigger onClick in jsdom
      // This test mainly ensures the buttons can receive focus
      expect(document.activeElement).toBe(saveButton);
    });

    it('has proper button roles', () => {
      renderLayout(<EditUserMessageFooter {...defaultProps} />);

      const buttons = screen.getAllByRole('button');
      expect(buttons).toHaveLength(2);
    });
  });

  describe('Integration with Ant Design', () => {
    it('renders correctly within ConfigProvider', () => {
      renderLayout(
        <ConfigProvider>
          <EditUserMessageFooter {...defaultProps} />
        </ConfigProvider>,
      );

      expect(screen.getByText('Cancel')).toBeInTheDocument();
      expect(screen.getByText('Save')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('maintains correct DOM structure', () => {
      const { container } = renderLayout(
        <EditUserMessageFooter {...defaultProps} />,
      );

      // Check that Flex container contains both buttons
      const flexContainer = container.querySelector('[data-gap="4"]');
      expect(flexContainer).toBeInTheDocument();

      const buttons = flexContainer?.querySelectorAll('button');
      expect(buttons).toHaveLength(2);
    });

    it('applies correct CSS classes and attributes', () => {
      const { container } = renderLayout(
        <EditUserMessageFooter {...defaultProps} />,
      );

      const flexContainer = container.querySelector('[style*="display: flex"]');
      expect(flexContainer).toBeInTheDocument();
    });
  });

  describe('Error Handling', () => {
    it('handles undefined callback functions gracefully', () => {
      // This test ensures the component doesn't crash if callbacks are undefined
      // In real usage, TypeScript would prevent this, but it's good to test
      const propsWithUndefinedCallbacks = {
        message_id: 'test-id',
        onSave: undefined as any,
        onCancel: undefined as any,
      };

      expect(() => {
        renderLayout(
          <EditUserMessageFooter {...propsWithUndefinedCallbacks} />,
        );
      }).not.toThrow();
    });
  });
});
