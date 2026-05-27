import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import ReleaseSelect from '@/components/molecules/Selects/ReleaseSelect';
import { getReportsReleases } from '@/services/beta-reports.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';

jest.mock('@/services/beta-reports.services');
jest.mock('@shared/ui/hooks/useHandleError.hook');

const mockGetReportsReleases = getReportsReleases as jest.MockedFunction<
  typeof getReportsReleases
>;
const mockUseHandleError = useHandleError as jest.MockedFunction<
  typeof useHandleError
>;

// Polyfill MessageChannel for JSDOM
if (typeof MessageChannel === 'undefined') {
  global.MessageChannel = class MessageChannel {
    port1: any;
    port2: any;

    constructor() {
      this.port1 = {
        onmessage: null,
        postMessage: (data: any) => {
          if (this.port2.onmessage) {
            setTimeout(() => {
              this.port2.onmessage({ data });
            }, 0);
          }
        },
      };
      this.port2 = {
        onmessage: null,
        postMessage: (data: any) => {
          if (this.port1.onmessage) {
            setTimeout(() => {
              this.port1.onmessage({ data });
            }, 0);
          }
        },
      };
    }
  } as any;
}

// Suppress act warnings
const originalError = console.error;
beforeAll(() => {
  console.error = (...args: any[]) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: An update to') ||
        args[0].includes('inside a test was not wrapped in act') ||
        args[0].includes('MessageChannel'))
    ) {
      return;
    }
    originalError.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
});

describe('ReleaseSelect Component', () => {
  const mockHandleError = jest.fn();

  const mockReleases = {
    docs: [
      { id: 1, release: 'v1.0.0', release_date: new Date('2024-01-01') },
      { id: 2, release: 'v1.1.0', release_date: new Date('2024-02-01') },
      { id: 3, release: 'v1.2.0', release_date: new Date('2024-03-01') },
    ],
    hasNextPage: false,
    totalDocs: 3,
    totalPages: 1,
    page: 1,
    limit: DEFAULT_PAGE_SIZE,
    nextPage: null,
    hasPrevPage: false,
    prevPage: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseHandleError.mockReturnValue(mockHandleError);
    mockGetReportsReleases.mockResolvedValue(mockReleases);

    document
      .querySelectorAll('.ant-select-dropdown')
      .forEach((el) => el.remove());
  });

  describe('Basic Rendering', () => {
    it('renders and loads releases on mount', async () => {
      renderLayout(<ReleaseSelect />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalledWith({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          platform: undefined,
        });
      });
    });

    it('renders with custom className', async () => {
      const { container } = renderLayout(
        <ReleaseSelect className='custom-class' />,
      );

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = container.querySelector('.release-select');
      expect(select).toHaveClass('custom-class');
      expect(select).toHaveClass('release-select');
    });

    it('has default placeholder', () => {
      const { container } = renderLayout(<ReleaseSelect />);

      const placeholder = container.querySelector('.ant-select-placeholder');
      expect(placeholder).toBeInTheDocument();
    });
  });

  describe('Platform-based Loading', () => {
    it('loads releases with platform parameter', async () => {
      renderLayout(<ReleaseSelect platform='AndroidTV' />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalledWith({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          platform: 'AndroidTV',
        });
      });
    });

    it('reloads releases when platform changes', async () => {
      const { rerender } = renderLayout(<ReleaseSelect platform='AndroidTV' />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalledTimes(1);
      });

      mockGetReportsReleases.mockClear();

      rerender(<ReleaseSelect platform='iOS' />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalledWith({
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
          platform: 'iOS',
        });
      });
    });
  });

  describe('Options Display', () => {
    it('displays loaded release options', async () => {
      renderLayout(<ReleaseSelect />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        expect(screen.getByText('v1.0.0')).toBeInTheDocument();
        expect(screen.getByText('v1.1.0')).toBeInTheDocument();
        expect(screen.getByText('v1.2.0')).toBeInTheDocument();
      });
    });

    it('shows "No data" when no releases are available', async () => {
      mockGetReportsReleases.mockResolvedValue({
        ...mockReleases,
        docs: [],
        totalDocs: 0,
      });

      renderLayout(<ReleaseSelect />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        expect(screen.getByText('No data')).toBeInTheDocument();
      });
    });
  });

  describe('onOptionsLoaded Callback', () => {
    it('calls onOptionsLoaded with first release id when data loads', async () => {
      const onOptionsLoaded = jest.fn();

      renderLayout(<ReleaseSelect onOptionsLoaded={onOptionsLoaded} />);

      await waitFor(() => {
        expect(onOptionsLoaded).toHaveBeenCalledWith(1);
      });
    });

    it('does not call onOptionsLoaded when no releases are loaded', async () => {
      const onOptionsLoaded = jest.fn();
      mockGetReportsReleases.mockResolvedValue({
        ...mockReleases,
        docs: [],
      });

      renderLayout(<ReleaseSelect onOptionsLoaded={onOptionsLoaded} />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      await new Promise((resolve) => setTimeout(resolve, 100));

      expect(onOptionsLoaded).not.toHaveBeenCalled();
    });
  });

  describe('Selection', () => {
    it('allows selecting a release', async () => {
      const onChange = jest.fn();

      renderLayout(<ReleaseSelect onChange={onChange} />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        expect(screen.getByText('v1.0.0')).toBeInTheDocument();
      });

      await userEvent.click(screen.getByText('v1.0.0'));

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(1, expect.any(Object));
      });
    });

    it('clears selection when clear button is clicked', async () => {
      const onChange = jest.fn();

      renderLayout(<ReleaseSelect value={1} onChange={onChange} />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const clearButton = screen.getByLabelText(/close-circle/i);
      await userEvent.click(clearButton);

      await waitFor(() => {
        expect(onChange).toHaveBeenCalledWith(undefined, undefined);
      });
    });
  });

  describe('Error Handling', () => {
    it('handles API errors', async () => {
      const error = new Error('API Error');
      mockGetReportsReleases.mockRejectedValue(error);

      renderLayout(<ReleaseSelect />);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner while fetching data', async () => {
      let resolvePromise: any;
      const promise = new Promise((resolve) => {
        resolvePromise = resolve;
      });
      mockGetReportsReleases.mockReturnValue(promise as any);

      renderLayout(<ReleaseSelect />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        expect(
          screen.getByRole('img', { name: /loading/i }),
        ).toBeInTheDocument();
      });

      resolvePromise(mockReleases);
    });
  });

  describe('Search', () => {
    it('filters releases based on search input', async () => {
      renderLayout(<ReleaseSelect />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        expect(screen.getByText('v1.0.0')).toBeInTheDocument();
      });

      await userEvent.type(select, 'v1.0');

      await waitFor(() => {
        expect(screen.getByText('v1.0.0')).toBeInTheDocument();
        expect(screen.queryByText('v1.1.0')).not.toBeInTheDocument();
      });
    });
  });

  describe('Props Forwarding', () => {
    it('forwards disabled prop', async () => {
      const { container } = renderLayout(<ReleaseSelect disabled />);

      await waitFor(() => {
        expect(mockGetReportsReleases).toHaveBeenCalled();
      });

      const select = container.querySelector('.ant-select');
      expect(select).toHaveClass('ant-select-disabled');
    });

    it('forwards custom placeholder', () => {
      const { container } = renderLayout(
        <ReleaseSelect placeholder='Choose release' />,
      );

      const placeholder = container.querySelector('.ant-select-placeholder');
      expect(placeholder).toBeInTheDocument();
    });
  });
});
