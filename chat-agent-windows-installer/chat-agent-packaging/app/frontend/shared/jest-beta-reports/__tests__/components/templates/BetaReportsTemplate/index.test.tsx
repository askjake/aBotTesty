import React from 'react';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import BetaReportsTemplate from '@/components/templates/BetaReportsTemplate';
import { ChatStatusEnum, RoleEnum } from '@shared/ui/enums/chats.enums';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import Cookies from 'js-cookie';

// Mock Cookies
jest.mock('js-cookie', () => ({
  set: jest.fn(),
  remove: jest.fn(),
  get: jest.fn(),
}));

// Mock useHandleError
jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: jest.fn(() => jest.fn()),
}));

// Suppress act warnings from Ant Design components
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

// Mock child components
jest.mock('@shared/ui/components/containers/AppsContainer', () => {
  return function AppsContainer({ children }: any) {
    return <div data-testid='apps-container'>{children}</div>;
  };
});

jest.mock('@/components/organisms/Reports', () => {
  return React.forwardRef(function Reports(props: any, ref: any) {
    React.useImperativeHandle(ref, () => ({
      refetchData: jest.fn(),
    }));
    return (
      <div data-testid='reports' data-props={JSON.stringify(props)}>
        Reports Component
      </div>
    );
  });
});

jest.mock('@/components/organisms/ActiveIssues', () => {
  return React.forwardRef(function ActiveIssues(props: any, ref: any) {
    React.useImperativeHandle(ref, () => ({
      refetchData: jest.fn(),
    }));
    return (
      <div data-testid='active-issues' data-props={JSON.stringify(props)}>
        ActiveIssues Component
      </div>
    );
  });
});

jest.mock('@/components/organisms/ReportsChat', () => {
  return React.forwardRef(function ReportsChat(props: any, ref: any) {
    React.useImperativeHandle(ref, () => ({
      refetchData: jest.fn(),
    }));
    return (
      <div data-testid='reports-chat' data-props={JSON.stringify(props)}>
        ReportsChat Component
      </div>
    );
  });
});

jest.mock('@/components/organisms/ReportsAccessBlock', () => {
  return function ReportsAccessBlock() {
    return <div data-testid='reports-access-block'>Access Denied</div>;
  };
});

jest.mock('@shared/ui/components/atoms/DatePickers/CustomRangePicker', () => {
  return function CustomRangePicker({ value, onChange }: any) {
    return (
      <input
        data-testid='date-range-picker'
        value={value ? JSON.stringify(value) : ''}
        onChange={(e) =>
          onChange(e.target.value ? JSON.parse(e.target.value) : null)
        }
      />
    );
  };
});

jest.mock('@/components/molecules/Selects/DeviceSelect', () => {
  return function DeviceSelect({ value, onChange, placeholder }: any) {
    return (
      <select
        data-testid='device-select'
        value={value || ''}
        onChange={(e) => onChange(e.target.value || undefined)}
      >
        <option value=''>{placeholder || 'Select device'}</option>
        <option value='device-1'>Device 1</option>
        <option value='device-2'>Device 2</option>
      </select>
    );
  };
});

jest.mock('@/components/molecules/Selects/PlatformSelect', () => {
  return function PlatformSelect({ value, onChange, placeholder }: any) {
    return (
      <select
        data-testid='platform-select'
        value={value || ''}
        onChange={(e) => onChange(e.target.value || undefined)}
      >
        <option value=''>{placeholder || 'Select platform'}</option>
        <option value='AndroidTV'>AndroidTV</option>
        <option value='DishTV'>DishTV</option>
      </select>
    );
  };
});

jest.mock('@/components/molecules/Selects/ReleaseSelect', () => {
  return function ReleaseSelect({
    value,
    onChange,
    placeholder,
    onOptionsLoaded,
  }: any) {
    React.useEffect(() => {
      if (onOptionsLoaded) {
        onOptionsLoaded(1);
      }
    }, []);
    return (
      <select
        data-testid='release-select'
        value={value || ''}
        onChange={(e) => onChange(e.target.value ? +e.target.value : undefined)}
      >
        <option value=''>{placeholder || 'Select release'}</option>
        <option value='1'>1.0.0</option>
        <option value='2'>2.0.0</option>
      </select>
    );
  };
});

jest.mock('@/components/molecules/Selects/PrioritySelect', () => {
  return function PrioritySelect({ value, onChange, placeholder }: any) {
    return (
      <select
        data-testid='priority-select'
        value={value || ''}
        onChange={(e) => onChange(e.target.value ? +e.target.value : undefined)}
      >
        <option value=''>{placeholder || 'Select priority'}</option>
        <option value='1'>Priority 1</option>
        <option value='2'>Priority 2</option>
        <option value='3'>Priority 3</option>
      </select>
    );
  };
});

jest.mock('@shared/ui/components/atoms/Buttons/IconButton', () => {
  return function IconButton({ onClick, loading, icon, ...props }: any) {
    return (
      <button
        data-testid='refetch-button'
        onClick={onClick}
        disabled={loading}
        {...props}
      >
        {loading ? 'Loading...' : 'Refetch'}
      </button>
    );
  };
});

describe('BetaReportsTemplate Component', () => {
  const mockChat = {
    chat_id: 'chat-1',
    title: 'Test Chat',
    created_at: '2025-01-01T00:00:00Z',
    owner_id: 'user-1',
    last_message_at: '2025-01-01T00:00:00Z',
    vault_mode: false,
    messages: {
      'msg-1': {
        content: {
          0: {
            type: MessageTypeEnum.TEXT,
            text: 'Hello',
          },
        },
        role: RoleEnum.USER,
        version_count: 1,
        version_index: 0,
        attachments: [],
      },
    },
    active: true,
    favorite: false,
    status: ChatStatusEnum.NORMAL,
    status_msg: null,
    group_id: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const clickTab = async (tabName: string) => {
    const tab = screen.getByRole('tab', { name: tabName });
    fireEvent.click(tab);
  };

  it('renders without crashing when user has access', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);
    expect(screen.getByText('Beta Reports Analysis')).toBeInTheDocument();
  });

  it('displays access denied block when user has no access', () => {
    renderLayout(<BetaReportsTemplate hasAccess={false} />);
    expect(screen.getByTestId('reports-access-block')).toBeInTheDocument();
    expect(screen.queryByText('Beta Reports Analysis')).not.toBeInTheDocument();
  });

  it('displays the title', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);
    expect(screen.getByText('Beta Reports Analysis')).toBeInTheDocument();
  });

  it('renders AppsContainer', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);
    expect(screen.getByTestId('apps-container')).toBeInTheDocument();
  });

  it('displays filters label', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);
    expect(screen.getByText('Filters:')).toBeInTheDocument();
  });

  it('renders all filter components', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);

    expect(screen.getByTestId('date-range-picker')).toBeInTheDocument();
    expect(screen.getByTestId('platform-select')).toBeInTheDocument();
    expect(screen.getByTestId('release-select')).toBeInTheDocument();
    expect(screen.getByTestId('device-select')).toBeInTheDocument();
    expect(screen.getByTestId('priority-select')).toBeInTheDocument();
  });

  it('renders refetch button', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);
    expect(screen.getByTestId('refetch-button')).toBeInTheDocument();
  });

  it('renders tabs with correct labels', () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    expect(
      screen.getByRole('tab', { name: 'Active Issue Candidates' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Reports' })).toBeInTheDocument();
  });

  it('displays Active Issue Candidates tab by default', () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    expect(screen.getByTestId('active-issues')).toBeInTheDocument();
  });

  it('renders ReportsChat when activeChat is provided', () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    expect(screen.getByTestId('reports-chat')).toBeInTheDocument();
  });

  it('does not render ReportsChat when activeChat is not provided', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);

    expect(screen.queryByTestId('reports-chat')).not.toBeInTheDocument();
  });

  it('switches to Reports tab when clicked', async () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);

    await clickTab('Reports');

    await waitFor(() => {
      expect(screen.getByTestId('reports')).toBeInTheDocument();
    });
  });

  it('updates date range filter and saves to cookies', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const dateRangePicker = screen.getByTestId('date-range-picker');
    const newDateRange = ['2025-10-01', '2025-10-31'];

    fireEvent.change(dateRangePicker, {
      target: { value: JSON.stringify(newDateRange) },
    });

    await waitFor(() => {
      expect(Cookies.set).toHaveBeenCalledWith(
        'dateRange',
        expect.any(String),
        expect.any(Object),
      );
    });
  });

  it('updates platform filter and saves to cookies', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const platformSelect = screen.getByTestId('platform-select');

    fireEvent.change(platformSelect, { target: { value: 'AndroidTV' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.platform).toBe('AndroidTV');
      expect(Cookies.set).toHaveBeenCalledWith(
        'platform',
        'AndroidTV',
        expect.any(Object),
      );
    });
  });

  it('updates release filter and saves to cookies', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const releaseSelect = screen.getByTestId('release-select');

    fireEvent.change(releaseSelect, { target: { value: '2' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.release).toBe(2);
      expect(Cookies.set).toHaveBeenCalledWith(
        'release',
        2,
        expect.any(Object),
      );
    });
  });

  it('updates device filter and saves to cookies', async () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);

    await clickTab('Reports');

    await waitFor(() => {
      expect(screen.getByTestId('reports')).toBeInTheDocument();
    });

    const deviceSelect = screen.getByTestId('device-select');

    fireEvent.change(deviceSelect, { target: { value: 'device-1' } });

    await waitFor(() => {
      const reports = screen.getByTestId('reports');
      const props = JSON.parse(reports.getAttribute('data-props') || '{}');
      expect(props.device).toBe('device-1');
      expect(Cookies.set).toHaveBeenCalledWith(
        'device',
        'device-1',
        expect.any(Object),
      );
    });
  });

  it('updates priority filter and saves to cookies', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const prioritySelect = screen.getByTestId('priority-select');

    fireEvent.change(prioritySelect, { target: { value: '2' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.min_priority).toBe(2);
      expect(Cookies.set).toHaveBeenCalledWith(
        'priority',
        2,
        expect.any(Object),
      );
    });
  });

  it('renders filter placeholders correctly', () => {
    renderLayout(<BetaReportsTemplate hasAccess={true} />);

    const deviceSelect = screen.getByTestId('device-select');
    const prioritySelect = screen.getByTestId('priority-select');

    expect(deviceSelect).toHaveTextContent('Select device');
    expect(prioritySelect).toHaveTextContent('Select priority');
  });

  it('maintains filter state when switching tabs', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const platformSelect = screen.getByTestId('platform-select');

    fireEvent.change(platformSelect, { target: { value: 'DishTV' } });

    await clickTab('Reports');

    await waitFor(() => {
      expect(screen.getByTestId('reports')).toBeInTheDocument();
    });

    await clickTab('Active Issue Candidates');

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.platform).toBe('DishTV');
    });
  });

  it('converts priority to number', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const prioritySelect = screen.getByTestId('priority-select');

    fireEvent.change(prioritySelect, { target: { value: '1' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(typeof props.min_priority).toBe('number');
      expect(props.min_priority).toBe(1);
    });
  });

  it('handles clearing date range and removes cookie', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const dateRangePicker = screen.getByTestId('date-range-picker');

    fireEvent.change(dateRangePicker, {
      target: { value: JSON.stringify(['2025-10-01', '2025-10-31']) },
    });

    await waitFor(() => {
      expect(Cookies.set).toHaveBeenCalled();
    });

    fireEvent.change(dateRangePicker, {
      target: { value: '' },
    });

    await waitFor(() => {
      expect(Cookies.remove).toHaveBeenCalledWith('dateRange');
    });
  });

  it('handles clearing platform filter and removes cookie', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const platformSelect = screen.getByTestId('platform-select');

    fireEvent.change(platformSelect, { target: { value: 'DishTV' } });
    fireEvent.change(platformSelect, { target: { value: '' } });

    await waitFor(() => {
      expect(Cookies.remove).toHaveBeenCalledWith('platform');
    });
  });

  it('uses default props correctly', () => {
    renderLayout(
      <BetaReportsTemplate
        hasAccess={true}
        activeChat={mockChat}
        defaultPlatform='DishTV'
        defaultRelease='2'
        defaultPriority='3'
        defaultDevice='device-2'
        defaultDateRange={['2025-01-01', '2025-01-31']}
      />,
    );

    const activeIssues = screen.getByTestId('active-issues');
    const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');

    expect(props.platform).toBe('DishTV');
    expect(props.release).toBe(2);
    expect(props.min_priority).toBe(3);
  });

  it('passes platform to ReportsChat component', () => {
    renderLayout(
      <BetaReportsTemplate
        hasAccess={true}
        activeChat={mockChat}
        defaultPlatform='DishTV'
      />,
    );

    const reportsChat = screen.getByTestId('reports-chat');
    const props = JSON.parse(reportsChat.getAttribute('data-props') || '{}');

    expect(props.platform).toBe('DishTV');
  });

  it('renders with correct layout structure', () => {
    const { container } = renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    expect(container.querySelector('.ant-row')).toBeInTheDocument();
    expect(container.querySelector('.ant-col')).toBeInTheDocument();
  });

  it('restores release when switching back to previously selected platform', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    const platformSelect = screen.getByTestId('platform-select');
    const releaseSelect = screen.getByTestId('release-select');

    // Select release for AndroidTV
    fireEvent.change(releaseSelect, { target: { value: '2' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.release).toBe(2);
    });

    // Switch to DishTV
    fireEvent.change(platformSelect, { target: { value: 'DishTV' } });

    // Switch back to AndroidTV
    fireEvent.change(platformSelect, { target: { value: 'AndroidTV' } });

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.release).toBe(2);
    });
  });

  it('sets release from onOptionsLoaded when no user selection exists', async () => {
    renderLayout(
      <BetaReportsTemplate hasAccess={true} activeChat={mockChat} />,
    );

    await waitFor(() => {
      const activeIssues = screen.getByTestId('active-issues');
      const props = JSON.parse(activeIssues.getAttribute('data-props') || '{}');
      expect(props.release).toBe(1);
    });
  });
});
