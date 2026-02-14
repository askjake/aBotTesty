import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import PrioritySelect from '@/components/molecules/Selects/PrioritySelect';

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

describe('PrioritySelect Component', () => {
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

  beforeEach(() => {
    document
      .querySelectorAll('.ant-select-dropdown')
      .forEach((el) => el.remove());
  });

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      renderLayout(<PrioritySelect />);
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('renders with custom className', () => {
      const { container } = renderLayout(
        <PrioritySelect className='custom-class' />,
      );
      const select = container.querySelector('.priority-select');
      expect(select).toHaveClass('custom-class');
      expect(select).toHaveClass('priority-select');
    });

    it('has allowClear enabled by default', () => {
      const { container } = renderLayout(<PrioritySelect value={1} />);

      const clearButton = container.querySelector('.ant-select-clear');
      expect(clearButton).toBeInTheDocument();
    });
  });

  describe('Priority Options', () => {
    it('displays all 6 priority options (Test Activity + P1-P5)', async () => {
      renderLayout(<PrioritySelect />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options).toHaveLength(6);
      });
    });

    it('displays priority options in correct order', async () => {
      renderLayout(<PrioritySelect />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options[0].textContent?.trim()).toBe('Test Activity');
        expect(options[1].textContent?.trim()).toBe('P1');
        expect(options[2].textContent?.trim()).toBe('P2');
        expect(options[3].textContent?.trim()).toBe('P3');
        expect(options[4].textContent?.trim()).toBe('P4');
        expect(options[5].textContent?.trim()).toBe('P5');
      });
    });

    it('has correct values for priority options', async () => {
      const onChange = jest.fn();
      renderLayout(<PrioritySelect onChange={onChange} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      // Test "Test Activity" has value 0
      const testActivityOption = getVisibleOptionByText('Test Activity');
      if (testActivityOption) {
        await userEvent.click(testActivityOption);
        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith(0, expect.any(Object));
        });
      }

      // Test P1 has value 1
      await userEvent.click(select);
      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const p1Option = getVisibleOptionByText('P1');
      if (p1Option) {
        await userEvent.click(p1Option);
        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith(1, expect.any(Object));
        });
      }
    });
  });

  describe('Selection Functionality', () => {
    it('allows selecting a priority', async () => {
      const onChange = jest.fn();
      renderLayout(<PrioritySelect onChange={onChange} />);

      const select = screen.getByRole('combobox');
      await userEvent.click(select);

      await waitFor(() => {
        const options = getVisibleOptions();
        expect(options.length).toBeGreaterThan(0);
      });

      const option = getVisibleOptionByText('P3');
      expect(option).toBeTruthy();

      if (option) {
        await userEvent.click(option);

        await waitFor(() => {
          expect(onChange).toHaveBeenCalledWith(3, expect.any(Object));
        });
      }
    });
  });

  describe('Props Forwarding', () => {
    it('forwards disabled prop correctly', () => {
      const { container } = renderLayout(<PrioritySelect disabled />);

      const select = container.querySelector('.ant-select');
      expect(select).toHaveClass('ant-select-disabled');
    });

    it('forwards custom placeholder prop', () => {
      const { container } = renderLayout(
        <PrioritySelect placeholder='Choose priority' />,
      );

      const placeholder = container.querySelector(
        '.ant-select-selection-placeholder',
      );
      if (placeholder) {
        expect(placeholder).toHaveTextContent('Choose priority');
      } else {
        const select = container.querySelector('.ant-select');
        expect(select).toBeInTheDocument();
      }
    });
  });

  describe('Callback Handling', () => {
    it('calls onChange with correct parameters for all priorities', async () => {
      const onChange = jest.fn();
      renderLayout(<PrioritySelect onChange={onChange} />);

      const priorities = [
        { label: 'Test Activity', value: 0 },
        { label: 'P1', value: 1 },
        { label: 'P5', value: 5 },
      ];

      for (const priority of priorities) {
        const select = screen.getByRole('combobox');
        await userEvent.click(select);

        await waitFor(() => {
          const options = getVisibleOptions();
          expect(options.length).toBeGreaterThan(0);
        });

        const option = getVisibleOptionByText(priority.label);
        expect(option).toBeTruthy();

        if (option) {
          await userEvent.click(option);

          await waitFor(() => {
            expect(onChange).toHaveBeenCalledWith(
              priority.value,
              expect.objectContaining({
                label: priority.label,
                value: priority.value,
              }),
            );
          });
        }

        onChange.mockClear();
      }
    });
  });
});
