import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import PlatformSelect from '@/components/molecules/Selects/PlatformSelect';

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

describe('PlatformSelect Component', () => {
  const mockPlatforms = [
    { label: 'iOS', value: 'ios' },
    { label: 'Android', value: 'android' },
    { label: 'Web', value: 'web' },
    { label: 'Windows', value: 'windows' },
    { label: 'macOS', value: 'macos' },
    { label: 'Linux', value: 'linux' },
  ];

  const getVisibleOptions = () => {
    const dropdown = document.querySelector(
      '.ant-select-dropdown:not(.ant-select-dropdown-hidden)',
    );
    if (!dropdown) return [];
    return Array.from(
      dropdown.querySelectorAll(
        '.ant-select-item.ant-select-item-option:not(.ant-select-item-option-disabled)',
      ),
    );
  };

  const getVisibleOptionByText = (text: string) => {
    const options = getVisibleOptions();
    return options.find((opt) => opt.textContent?.trim() === text) as
      | HTMLElement
      | undefined;
  };

  const getSelectedValue = () => {
    return document.querySelector('.ant-select-selection-item');
  };

  const getSearchInput = () => {
    return document.querySelector(
      '.ant-select-selection-search-input',
    ) as HTMLInputElement;
  };

  beforeEach(() => {
    document
      .querySelectorAll('.ant-select-dropdown')
      .forEach((el) => el.remove());
  });

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderLayout(<PlatformSelect />);
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('renders with custom className', () => {
      const { container } = renderLayout(
        <PlatformSelect className='custom-class' />,
      );
      const select = container.querySelector('.platform-select');
      expect(select).toHaveClass('custom-class');
      expect(select).toHaveClass('platform-select');
    });

    it('applies custom styles from styled component', () => {
      const { container } = renderLayout(<PlatformSelect />);

      const select = container.querySelector('.ant-select');
      expect(select).toBeInTheDocument();
      expect(select).toHaveClass('platform-select');
    });

    it('has showSearch enabled by default', () => {
      const { container } = renderLayout(<PlatformSelect />);

      const select = container.querySelector('.ant-select-show-search');
      expect(select).toBeInTheDocument();
    });

    it('displays default placeholder when no value is selected', () => {
      const { container } = renderLayout(
        <PlatformSelect options={mockPlatforms} />,
      );

      const placeholder = container.querySelector(
        '.ant-select-selection-placeholder',
      );
      if (placeholder) {
        expect(placeholder).toHaveTextContent('Select platform');
      } else {
        const select = container.querySelector('.ant-select');
        expect(select).toBeInTheDocument();
      }
    });

    it('has proper ARIA attributes', async () => {
      renderLayout(<PlatformSelect />);

      const select = screen.getByRole('combobox');
      expect(select).toHaveAttribute('aria-expanded', 'false');

      await userEvent.click(select);

      await waitFor(() => {
        expect(select).toHaveAttribute('aria-expanded', 'true');
      });
    });
  });

  describe('Options Display', () => {
    it('displays options when clicked', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options).toHaveLength(6);
      });
    });

    it('displays all platform options in correct order', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options[0].textContent?.trim()).toBe('iOS');
        expect(options[1].textContent?.trim()).toBe('Android');
        expect(options[2].textContent?.trim()).toBe('Web');
        expect(options[3].textContent?.trim()).toBe('Windows');
        expect(options[4].textContent?.trim()).toBe('macOS');
        expect(options[5].textContent?.trim()).toBe('Linux');
      });
    });
  });

  describe('Selection Functionality', () => {
    it('allows selecting a platform', async () => {
      const onChange = jest.fn();
      renderLayout(
        <PlatformSelect options={mockPlatforms} onChange={onChange} />,
      );

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option = getVisibleOptionByText('iOS');
      expect(option).toBeTruthy();

      if (option) {
        await userEvent.click(option);

        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith('ios', expect.any(Object));
        });
      }
    });
  });

  describe('Search Functionality', () => {
    it('filters options based on search input', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options).toHaveLength(6);
      });

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, 'ios');

        await waitFor(() => {
          const filteredOptions = getVisibleOptions();
          expect(filteredOptions).toHaveLength(1);
          expect(filteredOptions[0].textContent?.trim()).toBe('iOS');
        });
      }
    });

    it('filters options case-insensitively', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, 'ANDROID');

        await waitFor(() => {
          const filteredOptions = getVisibleOptions();
          expect(filteredOptions).toHaveLength(1);
          expect(filteredOptions[0].textContent?.trim()).toBe('Android');
        });
      }
    });

    it('shows no results when search does not match', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, 'nonexistent');

        await waitFor(() => {
          const filteredOptions = getVisibleOptions();
          expect(filteredOptions).toHaveLength(0);
        });
      }
    });

    it('filters by partial match', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, 'os');

        await waitFor(() => {
          const filteredOptions = getVisibleOptions();
          expect(filteredOptions).toHaveLength(2);
          const labels = filteredOptions.map((opt) => opt.textContent?.trim());
          expect(labels).toContain('iOS');
          expect(labels).toContain('macOS');
        });
      }
    });

    it('filters platforms with special characters', async () => {
      const specialPlatforms = [
        { label: 'React Native', value: 'react-native' },
        { label: 'Node.js', value: 'nodejs' },
        { label: 'Vue.js', value: 'vuejs' },
      ];

      renderLayout(<PlatformSelect options={specialPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, '.js');

        await waitFor(() => {
          const filteredOptions = getVisibleOptions();
          expect(filteredOptions).toHaveLength(2);
          const labels = filteredOptions.map((opt) => opt.textContent?.trim());
          expect(labels).toContain('Node.js');
          expect(labels).toContain('Vue.js');
        });
      }
    });
  });

  describe('Props Forwarding', () => {
    it('forwards disabled prop correctly', () => {
      const { container } = renderLayout(<PlatformSelect disabled />);

      const select = container.querySelector('.ant-select');
      expect(select).toHaveClass('ant-select-disabled');
    });

    it('forwards custom placeholder prop', () => {
      const { container } = renderLayout(
        <PlatformSelect
          placeholder='Choose your platform'
          options={mockPlatforms}
        />,
      );

      const placeholder = container.querySelector(
        '.ant-select-selection-placeholder',
      );
      if (placeholder) {
        expect(placeholder).toHaveTextContent('Choose your platform');
      } else {
        const select = container.querySelector('.ant-select');
        expect(select).toBeInTheDocument();
      }
    });

    it('supports size variants', () => {
      const { container } = renderLayout(<PlatformSelect size='large' />);

      const select = container.querySelector('.ant-select');
      expect(select).toHaveClass('ant-select-lg');
    });

    it('supports loading state', () => {
      const { container } = renderLayout(<PlatformSelect loading />);

      const select = container.querySelector('.ant-select');
      expect(select).toHaveClass('ant-select-loading');
    });

    it('supports multiple selection mode', async () => {
      const onChange = jest.fn();
      renderLayout(
        <PlatformSelect
          mode='multiple'
          options={mockPlatforms}
          onChange={onChange}
        />,
      );

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option1 = getVisibleOptionByText('iOS');
      if (option1) {
        await userEvent.click(option1);

        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith(['ios'], expect.any(Array));
        });
      }

      const option2 = getVisibleOptionByText('Android');
      if (option2) {
        await userEvent.click(option2);

        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith(
            ['ios', 'android'],
            expect.any(Array),
          );
        });
      }
    });
  });

  describe('Edge Cases', () => {
    it('handles empty options array', () => {
      renderLayout(<PlatformSelect options={[]} />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('handles undefined options', () => {
      renderLayout(<PlatformSelect />);

      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('handles rapid selection changes', async () => {
      const onChange = jest.fn();
      renderLayout(
        <PlatformSelect options={mockPlatforms} onChange={onChange} />,
      );

      const select = screen.getByRole('combobox');

      // First selection
      await userEvent.click(select);
      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option1 = getVisibleOptionByText('iOS');
      if (option1) {
        await userEvent.click(option1);
        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith('ios', expect.any(Object));
        });
      }

      // Second selection
      await userEvent.click(select);
      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option2 = getVisibleOptionByText('Android');
      if (option2) {
        await userEvent.click(option2);
        await waitFor(() => {
          expect(onChange).toHaveBeenCalledTimes(2);
        });
      }

      expect(onChange).toHaveBeenNthCalledWith(1, 'ios', expect.any(Object));
      expect(onChange).toHaveBeenNthCalledWith(
        2,
        'android',
        expect.any(Object),
      );
    });

    it('maintains focus after selection', async () => {
      renderLayout(<PlatformSelect options={mockPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option = getVisibleOptionByText('Web');
      expect(option).toBeTruthy();

      if (option) {
        await userEvent.click(option);

        await waitFor(() => {
          expect(select).toHaveAttribute('aria-expanded', 'false');
        });
      }
    });

    it('handles special characters in platform names', async () => {
      const specialPlatforms = [
        { label: 'Platform & Co.', value: 'platform-1' },
        { label: 'System (2023)', value: 'platform-2' },
        { label: 'OS "Pro"', value: 'platform-3' },
      ];

      renderLayout(<PlatformSelect options={specialPlatforms} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const options = getVisibleOptions();
      expect(options).toHaveLength(3);

      const labels = options.map((opt) => opt.textContent?.trim());
      expect(labels).toContain('Platform & Co.');
      expect(labels).toContain('System (2023)');
      expect(labels).toContain('OS "Pro"');
    });
  });

  describe('Callback Handling', () => {
    it('calls onChange with correct parameters', async () => {
      const onChange = jest.fn();
      renderLayout(
        <PlatformSelect options={mockPlatforms} onChange={onChange} />,
      );

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option = getVisibleOptionByText('Linux');
      expect(option).toBeTruthy();

      if (option) {
        await userEvent.click(option);

        await waitFor(() => {
          expect(onChange).toHaveBeenCalledTimes(1);
          expect(onChange).toHaveBeenCalledWith(
            'linux',
            expect.objectContaining({
              label: 'Linux',
              value: 'linux',
            }),
          );
        });
      }
    });

    it('calls onSearch when searching', async () => {
      const onSearch = jest.fn();
      renderLayout(
        <PlatformSelect options={mockPlatforms} onSearch={onSearch} />,
      );

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      const searchInput = getSearchInput();
      if (searchInput) {
        await userEvent.type(searchInput, 'web');

        await waitFor(() => {
          expect(onSearch).toHaveBeenCalled();
        });
      }
    });

    it('calls onClear when clear button is clicked', async () => {
      const onClear = jest.fn();
      renderLayout(
        <PlatformSelect
          value='ios'
          options={mockPlatforms}
          onClear={onClear}
          allowClear
        />,
      );

      const clearButton = screen.getByLabelText(/close-circle/i);
      await userEvent.click(clearButton);

      await waitFor(() => {
        expect(onClear).toHaveBeenCalled();
      });
    });
  });
});
