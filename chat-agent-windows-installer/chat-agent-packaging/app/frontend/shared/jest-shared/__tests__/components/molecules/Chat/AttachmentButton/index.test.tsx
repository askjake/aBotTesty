import { screen, fireEvent, cleanup } from '@testing-library/react';
import AttachmentButton from '@shared/ui/components/molecules/Chat/AttachmentButton';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { HTMLProps, ReactNode } from 'react';

// Mock Ant Design components
jest.mock('antd', () => ({
  Badge: ({ children, dot }: { children: ReactNode; dot: string }) => (
    <div data-testid='badge' data-dot={dot}>
      {children}
    </div>
  ),
  Button: ({
    children,
    icon,
    onClick,
    type,
  }: HTMLProps<HTMLButtonElement> & { icon: ReactNode }) => (
    <button data-testid='attachment-button' onClick={onClick} data-type={type}>
      {icon}
      {children}
    </button>
  ),
}));

// Mock Ant Design icons
jest.mock('@ant-design/icons', () => ({
  PaperClipOutlined: () => <span data-testid='paperclip-icon'>📎</span>,
}));

describe('AttachmentButton', () => {
  const defaultProps = {
    hasFiles: false,
    headerOpen: false,
    setHeaderOpen: jest.fn(),
    disabled: false,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterEach(() => {
    cleanup(); // Clean up after each test
  });

  describe('Rendering', () => {
    test('should render the attachment button with paperclip icon', () => {
      renderLayout(<AttachmentButton {...defaultProps} />);

      expect(screen.getByTestId('attachment-button')).toBeInTheDocument();
      expect(screen.getByTestId('paperclip-icon')).toBeInTheDocument();
    });

    test('should render button with text type', () => {
      renderLayout(<AttachmentButton {...defaultProps} />);

      const button = screen.getByTestId('attachment-button');
      expect(button).toHaveAttribute('data-type', 'text');
    });

    test('should wrap button in Badge component', () => {
      renderLayout(<AttachmentButton {...defaultProps} />);

      expect(screen.getByTestId('badge')).toBeInTheDocument();
    });
  });

  describe('Badge dot visibility', () => {
    test('should show badge dot when hasFiles is true and headerOpen is false', () => {
      renderLayout(
        <AttachmentButton
          {...defaultProps}
          hasFiles={true}
          headerOpen={false}
        />,
      );

      const badge = screen.getByTestId('badge');
      expect(badge).toHaveAttribute('data-dot', 'true');
    });

    test('should not show badge dot when hasFiles is false', () => {
      renderLayout(
        <AttachmentButton
          {...defaultProps}
          hasFiles={false}
          headerOpen={false}
        />,
      );

      const badge = screen.getByTestId('badge');
      expect(badge).toHaveAttribute('data-dot', 'false');
    });

    test('should not show badge dot when headerOpen is true (even with hasFiles true)', () => {
      renderLayout(
        <AttachmentButton
          {...defaultProps}
          hasFiles={true}
          headerOpen={true}
        />,
      );

      const badge = screen.getByTestId('badge');
      expect(badge).toHaveAttribute('data-dot', 'false');
    });

    test('should not show badge dot when both hasFiles and headerOpen are false', () => {
      renderLayout(
        <AttachmentButton
          {...defaultProps}
          hasFiles={false}
          headerOpen={false}
        />,
      );

      const badge = screen.getByTestId('badge');
      expect(badge).toHaveAttribute('data-dot', 'false');
    });
  });

  describe('Click behavior', () => {
    test('should call setHeaderOpen with true when headerOpen is false', () => {
      const mockSetHeaderOpen = jest.fn();

      renderLayout(
        <AttachmentButton
          {...defaultProps}
          headerOpen={false}
          setHeaderOpen={mockSetHeaderOpen}
        />,
      );

      fireEvent.click(screen.getByTestId('attachment-button'));

      expect(mockSetHeaderOpen).toHaveBeenCalledTimes(1);
      expect(mockSetHeaderOpen).toHaveBeenCalledWith(true);
    });

    test('should call setHeaderOpen with false when headerOpen is true', () => {
      const mockSetHeaderOpen = jest.fn();

      renderLayout(
        <AttachmentButton
          {...defaultProps}
          headerOpen={true}
          setHeaderOpen={mockSetHeaderOpen}
        />,
      );

      fireEvent.click(screen.getByTestId('attachment-button'));

      expect(mockSetHeaderOpen).toHaveBeenCalledTimes(1);
      expect(mockSetHeaderOpen).toHaveBeenCalledWith(false);
    });

    test('should toggle headerOpen state correctly', () => {
      const mockSetHeaderOpen = jest.fn();

      // Test first scenario: headerOpen = false
      renderLayout(
        <AttachmentButton
          {...defaultProps}
          headerOpen={false}
          setHeaderOpen={mockSetHeaderOpen}
        />,
      );

      fireEvent.click(screen.getByTestId('attachment-button'));
      expect(mockSetHeaderOpen).toHaveBeenCalledWith(true);
    });
  });

  describe('Default props', () => {
    test('should handle missing headerOpen prop (defaults to false)', () => {
      const mockSetHeaderOpen = jest.fn();
      const propsWithoutHeaderOpen = {
        hasFiles: false,
        setHeaderOpen: mockSetHeaderOpen,
      };

      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      renderLayout(<AttachmentButton {...propsWithoutHeaderOpen} />);

      fireEvent.click(screen.getByTestId('attachment-button'));

      expect(mockSetHeaderOpen).toHaveBeenCalledWith(true);
    });

    test('should handle missing hasFiles prop (defaults to false)', () => {
      const propsWithoutHasFiles = {
        headerOpen: false,
        setHeaderOpen: jest.fn(),
      };
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      renderLayout(<AttachmentButton {...propsWithoutHasFiles} />);

      const badge = screen.getByTestId('badge');
      expect(badge).toHaveAttribute('data-dot', 'false');
    });
  });

  describe('Component integration', () => {
    test.each([
      {
        hasFiles: true,
        headerOpen: true,
        expectedDot: 'false',
        expectedToggle: false,
      },
      {
        hasFiles: true,
        headerOpen: false,
        expectedDot: 'true',
        expectedToggle: true,
      },
      {
        hasFiles: false,
        headerOpen: true,
        expectedDot: 'false',
        expectedToggle: false,
      },
      {
        hasFiles: false,
        headerOpen: false,
        expectedDot: 'false',
        expectedToggle: true,
      },
    ])(
      'should work correctly with hasFiles=$hasFiles and headerOpen=$headerOpen',
      ({ hasFiles, headerOpen, expectedDot, expectedToggle }) => {
        const mockSetHeaderOpen = jest.fn();

        renderLayout(
          <AttachmentButton
            disabled={false}
            hasFiles={hasFiles}
            headerOpen={headerOpen}
            setHeaderOpen={mockSetHeaderOpen}
          />,
        );

        const badge = screen.getByTestId('badge');
        expect(badge).toHaveAttribute('data-dot', expectedDot);

        fireEvent.click(screen.getByTestId('attachment-button'));
        expect(mockSetHeaderOpen).toHaveBeenCalledWith(expectedToggle);
      },
    );
  });
});
