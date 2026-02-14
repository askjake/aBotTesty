import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatSettings from '@/components/organisms/ChatSettings';

// Mock the styled component
jest.mock('@/components/organisms/ChatSettings/ChatSettings.styled', () => ({
  ChatSettingsStyled: ({ children, icon, shape, trigger, ...props }: any) => (
    <div
      data-testid='chat-settings-styled'
      data-shape={shape}
      data-trigger={trigger}
      {...props}
    >
      <div data-testid='settings-icon'>{icon}</div>
      <div data-testid='settings-children'>{children}</div>
    </div>
  ),
}));

// Mock the child components
jest.mock('@/components/molecules/FloatButtons/ExportChatButton', () => ({
  __esModule: true,
  // eslint-disable-next-line react/display-name
  default: () => <div data-testid='export-chat-button'>Export Chat Button</div>,
}));

jest.mock('@/components/molecules/FloatButtons/ChatInfoButton', () => ({
  __esModule: true,
  // eslint-disable-next-line react/display-name
  default: () => <div data-testid='chat-info-button'>Chat Info Button</div>,
}));

// Mock react-icons
jest.mock('react-icons/io5', () => ({
  IoSettingsOutline: () => (
    <svg
      data-testid='settings-outline-icon'
      xmlns='http://www.w3.org/2000/svg'
      fill='currentColor'
      viewBox='0 0 512 512'
    >
      <path d='M settings-icon-path' />
    </svg>
  ),
}));

// Mock Ant Design components
jest.mock('antd', () => ({
  Tooltip: ({ children, title, placement }: any) => (
    <div data-testid='tooltip' data-title={title} data-placement={placement}>
      {children}
    </div>
  ),
  FloatButton: {
    Group: ({ children, shape, trigger, icon, ...props }: any) => (
      <div
        data-testid='float-button-group'
        data-shape={shape}
        data-trigger={trigger}
        {...props}
      >
        {icon && <div data-testid='group-icon'>{icon}</div>}
        {children}
      </div>
    ),
  },
}));

describe('ChatSettings', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render the ChatSettingsStyled component with correct props', () => {
      render(<ChatSettings />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      expect(styledComponent).toBeInTheDocument();
      expect(styledComponent).toHaveAttribute('data-shape', 'circle');
      expect(styledComponent).toHaveAttribute('data-trigger', 'click');
    });

    it('should render the settings icon', () => {
      render(<ChatSettings />);

      const settingsIconContainer = screen.getByTestId('settings-icon');
      const svg = settingsIconContainer.querySelector('svg');
      expect(svg).toBeInTheDocument();
      expect(svg).toHaveAttribute('viewBox', '0 0 512 512');
      expect(svg).toHaveAttribute('fill', 'currentColor');
      expect(svg).toHaveAttribute('xmlns', 'http://www.w3.org/2000/svg');
    });

    it('should render without crashing', () => {
      expect(() => render(<ChatSettings />)).not.toThrow();
    });

    it('should have correct component structure', () => {
      render(<ChatSettings />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      const settingsIcon = screen.getByTestId('settings-icon');
      const settingsChildren = screen.getByTestId('settings-children');

      expect(styledComponent).toContainElement(settingsIcon);
      expect(styledComponent).toContainElement(settingsChildren);
    });
  });

  describe('Export and Info Buttons', () => {
    it('should render ExportChatButton with tooltip', () => {
      render(<ChatSettings />);

      const exportButton = screen.getByTestId('export-chat-button');
      expect(exportButton).toBeInTheDocument();

      const tooltips = screen.getAllByTestId('tooltip');
      const exportTooltip = tooltips.find(
        (tooltip) =>
          tooltip.getAttribute('data-title') ===
          'Export chat history to the json file',
      );
      expect(exportTooltip).toBeInTheDocument();
      expect(exportTooltip).toHaveAttribute('data-placement', 'left');
    });

    it('should render ChatInfoButton with tooltip', () => {
      render(<ChatSettings />);

      const infoButton = screen.getByTestId('chat-info-button');
      expect(infoButton).toBeInTheDocument();

      const tooltips = screen.getAllByTestId('tooltip');
      const infoTooltip = tooltips.find(
        (tooltip) =>
          tooltip.getAttribute('data-title') ===
          'Information about the current chat',
      );
      expect(infoTooltip).toBeInTheDocument();
      expect(infoTooltip).toHaveAttribute('data-placement', 'left');
    });

    it('should render all child components', () => {
      render(<ChatSettings />);

      expect(screen.getByTestId('export-chat-button')).toBeInTheDocument();
      expect(screen.getByTestId('chat-info-button')).toBeInTheDocument();
    });
  });

  describe('Component Structure', () => {
    it('should render all tooltips with correct placement', () => {
      render(<ChatSettings />);

      const tooltips = screen.getAllByTestId('tooltip');

      // Should have 2 tooltips: export and info
      expect(tooltips).toHaveLength(2);

      tooltips.forEach((tooltip) => {
        expect(tooltip).toHaveAttribute('data-placement', 'left');
      });
    });

    it('should render all expected components', () => {
      render(<ChatSettings />);

      expect(screen.getByTestId('export-chat-button')).toBeInTheDocument();
      expect(screen.getByTestId('chat-info-button')).toBeInTheDocument();
      expect(screen.getByTestId('chat-settings-styled')).toBeInTheDocument();
    });

    it('should contain all child elements in the correct structure', () => {
      render(<ChatSettings />);

      const settingsChildren = screen.getByTestId('settings-children');

      expect(settingsChildren).toContainElement(
        screen.getByTestId('export-chat-button'),
      );
      expect(settingsChildren).toContainElement(
        screen.getByTestId('chat-info-button'),
      );
    });

    it('should render tooltips wrapping the buttons', () => {
      render(<ChatSettings />);

      const tooltips = screen.getAllByTestId('tooltip');

      // Each tooltip should contain one of the buttons
      const exportTooltip = tooltips.find((t) =>
        t.getAttribute('data-title')?.includes('Export'),
      );
      const infoTooltip = tooltips.find((t) =>
        t.getAttribute('data-title')?.includes('Information'),
      );

      expect(exportTooltip).toContainElement(
        screen.getByTestId('export-chat-button'),
      );
      expect(infoTooltip).toContainElement(
        screen.getByTestId('chat-info-button'),
      );
    });
  });

  describe('Props Handling', () => {
    it('should pass additional props to ChatSettingsStyled', () => {
      render(<ChatSettings data-custom-prop='test-value' />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      expect(styledComponent).toHaveAttribute('data-custom-prop', 'test-value');
    });

    it('should handle custom shape prop', () => {
      render(<ChatSettings shape='square' />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      expect(styledComponent).toHaveAttribute('data-shape', 'square');
    });

    it('should handle custom trigger prop', () => {
      render(<ChatSettings trigger='hover' />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      expect(styledComponent).toHaveAttribute('data-trigger', 'hover');
    });

    it('should use default props when none provided', () => {
      render(<ChatSettings />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      expect(styledComponent).toHaveAttribute('data-shape', 'circle');
      expect(styledComponent).toHaveAttribute('data-trigger', 'click');
    });
  });

  describe('Accessibility', () => {
    it('should have descriptive tooltip titles', () => {
      render(<ChatSettings />);

      const tooltips = screen.getAllByTestId('tooltip');
      const tooltipTitles = tooltips.map((tooltip) =>
        tooltip.getAttribute('data-title'),
      );

      expect(tooltipTitles).toContain('Export chat history to the json file');
      expect(tooltipTitles).toContain('Information about the current chat');
    });

    it('should render settings icon with proper structure', () => {
      render(<ChatSettings />);

      const settingsIconContainer = screen.getByTestId('settings-icon');
      const svg = settingsIconContainer.querySelector('svg');

      expect(svg).toBeInTheDocument();
      expect(svg).toHaveAttribute('xmlns', 'http://www.w3.org/2000/svg');
      expect(svg).toHaveAttribute('fill', 'currentColor');
    });

    it('should have proper semantic structure', () => {
      render(<ChatSettings />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      const settingsChildren = screen.getByTestId('settings-children');

      expect(styledComponent).toBeInTheDocument();
      expect(settingsChildren).toBeInTheDocument();
      expect(styledComponent).toContainElement(settingsChildren);
    });
  });

  describe('Integration', () => {
    it('should render complete component hierarchy', () => {
      render(<ChatSettings />);

      // Check main container
      expect(screen.getByTestId('chat-settings-styled')).toBeInTheDocument();

      // Check icon
      expect(screen.getByTestId('settings-icon')).toBeInTheDocument();

      // Check children container
      expect(screen.getByTestId('settings-children')).toBeInTheDocument();

      // Check tooltips
      expect(screen.getAllByTestId('tooltip')).toHaveLength(2);

      // Check buttons
      expect(screen.getByTestId('export-chat-button')).toBeInTheDocument();
      expect(screen.getByTestId('chat-info-button')).toBeInTheDocument();
    });

    it('should maintain correct nesting structure', () => {
      render(<ChatSettings />);

      const styledComponent = screen.getByTestId('chat-settings-styled');
      const settingsChildren = screen.getByTestId('settings-children');
      const tooltips = screen.getAllByTestId('tooltip');

      // Settings children should be inside styled component
      expect(styledComponent).toContainElement(settingsChildren);

      // Tooltips should be inside settings children
      tooltips.forEach((tooltip) => {
        expect(settingsChildren).toContainElement(tooltip);
      });

      // Buttons should be inside tooltips
      const exportButton = screen.getByTestId('export-chat-button');
      const infoButton = screen.getByTestId('chat-info-button');

      const hasExportButton = tooltips.some((tooltip) =>
        tooltip.contains(exportButton),
      );
      const hasInfoButton = tooltips.some((tooltip) =>
        tooltip.contains(infoButton),
      );

      expect(hasExportButton).toBe(true);
      expect(hasInfoButton).toBe(true);
    });
  });
});
