import { renderHook, act } from '@testing-library/react';
import useDebouncedCallback from '@shared/ui/hooks/useDebounceCallback.hook';

// Mock timers
jest.useFakeTimers();

describe('useDebouncedCallback', () => {
  let mockFunction: jest.MockedFunction<(value: any) => void>;

  beforeEach(() => {
    mockFunction = jest.fn();
    jest.clearAllTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.clearAllTimers();
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  describe('Basic functionality', () => {
    it('should return a function', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      expect(typeof result.current).toBe('function');
    });

    it('should call the function after the default wait time (200ms)', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      act(() => {
        result.current('test');
      });

      expect(mockFunction).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('test');
    });

    it('should call the function after custom wait time', () => {
      const customWait = 500;
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, customWait),
      );

      act(() => {
        result.current('test');
      });

      expect(mockFunction).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(499);
      });

      expect(mockFunction).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('test');
    });
  });

  describe('Debouncing behavior', () => {
    it('should cancel previous call when called again before wait time', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      act(() => {
        result.current('first');
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      act(() => {
        result.current('second');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('second');
      expect(mockFunction).not.toHaveBeenCalledWith('first');
    });

    it('should handle multiple rapid calls and only execute the last one', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      act(() => {
        result.current('call1');
        result.current('call2');
        result.current('call3');
        result.current('call4');
        result.current('call5');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('call5');
    });

    it('should allow multiple executions if calls are spaced apart', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      // First call
      act(() => {
        result.current('first');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      // Second call after debounce period
      act(() => {
        result.current('second');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(2);
      expect(mockFunction).toHaveBeenNthCalledWith(1, 'first');
      expect(mockFunction).toHaveBeenNthCalledWith(2, 'second');
    });
  });

  describe('Arguments handling', () => {
    it('should handle single argument', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      act(() => {
        result.current('single-arg');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledWith('single-arg');
    });

    it('should handle multiple arguments', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      act(() => {
        result.current('arg1', 'arg2', 'arg3');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledWith('arg1', 'arg2', 'arg3');
    });

    it('should handle no arguments', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      act(() => {
        result.current();
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledWith();
    });

    it('should handle different argument types', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      const obj = { key: 'value' };
      const arr = [1, 2, 3];

      act(() => {
        result.current('string', 123, true, obj, arr, null, undefined);
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledWith(
        'string',
        123,
        true,
        obj,
        arr,
        null,
        undefined,
      );
    });
  });

  describe('Hook dependencies and memoization', () => {
    it('should return the same function reference when dependencies do not change', () => {
      const { result, rerender } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      const firstCallback = result.current;

      rerender();

      const secondCallback = result.current;

      expect(firstCallback).toBe(secondCallback);
    });

    it('should return a new function reference when func changes', () => {
      const secondMockFunction = jest.fn();

      const { result, rerender } = renderHook(
        ({ func }) => useDebouncedCallback(func, 200),
        { initialProps: { func: mockFunction } },
      );

      const firstCallback = result.current;

      rerender({ func: secondMockFunction });

      const secondCallback = result.current;

      expect(firstCallback).not.toBe(secondCallback);
    });

    it('should return a new function reference when wait time changes', () => {
      const { result, rerender } = renderHook(
        ({ wait }) => useDebouncedCallback(mockFunction, wait),
        { initialProps: { wait: 200 } },
      );

      const firstCallback = result.current;

      rerender({ wait: 300 });

      const secondCallback = result.current;

      expect(firstCallback).not.toBe(secondCallback);
    });

    it('should call the original function when dependencies change before timeout', () => {
      const secondMockFunction = jest.fn();

      const { result, rerender } = renderHook(
        ({ func }) => useDebouncedCallback(func, 200),
        { initialProps: { func: mockFunction } },
      );

      // Call with first function
      act(() => {
        result.current('test');
      });

      // Change function before timeout
      rerender({ func: secondMockFunction });

      // Advance time - the original function should still be called
      // because the timeout closure captured the original function
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledWith('test');
      expect(secondMockFunction).not.toHaveBeenCalled();
    });

    it('should use new function for subsequent calls after dependency change', () => {
      const secondMockFunction = jest.fn();

      const { result, rerender } = renderHook(
        ({ func }) => useDebouncedCallback(func, 200),
        { initialProps: { func: mockFunction } },
      );

      // Change function
      rerender({ func: secondMockFunction });

      // Call with new function
      act(() => {
        result.current('test-new');
      });

      // Advance time
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(secondMockFunction).toHaveBeenCalledWith('test-new');
      expect(mockFunction).not.toHaveBeenCalled();
    });
  });

  describe('Edge cases', () => {
    it('should handle zero wait time', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 0),
      );

      act(() => {
        result.current('test');
      });

      act(() => {
        jest.advanceTimersByTime(0);
      });

      expect(mockFunction).toHaveBeenCalledWith('test');
    });

    it('should handle very large wait times', () => {
      const largeWait = 10000;
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, largeWait),
      );

      act(() => {
        result.current('test');
      });

      act(() => {
        jest.advanceTimersByTime(largeWait - 1);
      });

      expect(mockFunction).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(1);
      });

      expect(mockFunction).toHaveBeenCalledWith('test');
    });

    it('should handle function that throws an error', () => {
      const errorFunction = jest.fn(() => {
        throw new Error('Test error');
      });

      const { result } = renderHook(() => useDebouncedCallback(errorFunction));

      act(() => {
        result.current('test');
      });

      expect(() => {
        act(() => {
          jest.advanceTimersByTime(200);
        });
      }).toThrow('Test error');

      expect(errorFunction).toHaveBeenCalledWith('test');
    });

    it('should execute pending timeout even after component unmount', () => {
      const { result, unmount } = renderHook(() =>
        useDebouncedCallback(mockFunction),
      );

      act(() => {
        result.current('test');
      });

      unmount();

      act(() => {
        jest.advanceTimersByTime(200);
      });

      // Function should still be called after unmount since there's no cleanup
      expect(mockFunction).toHaveBeenCalledWith('test');
    });

    it('should handle negative wait times (treated as 0)', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, -100),
      );

      act(() => {
        result.current('test');
      });

      act(() => {
        jest.advanceTimersByTime(0);
      });

      expect(mockFunction).toHaveBeenCalledWith('test');
    });
  });

  describe('Performance and behavior', () => {
    it('should not execute function immediately', () => {
      const { result } = renderHook(() => useDebouncedCallback(mockFunction));

      act(() => {
        result.current('test');
      });

      expect(mockFunction).not.toHaveBeenCalled();
    });

    it('should handle rapid successive calls efficiently', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 100),
      );

      // Simulate rapid typing
      act(() => {
        for (let i = 0; i < 100; i++) {
          result.current(`input-${i}`);
        }
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('input-99');
    });

    it('should maintain correct execution order with overlapping calls', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      act(() => {
        result.current('first');
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      act(() => {
        result.current('second');
      });

      act(() => {
        jest.advanceTimersByTime(100);
      });

      act(() => {
        result.current('third');
      });

      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('third');
    });

    it('should properly clear previous timeouts', () => {
      const { result } = renderHook(() =>
        useDebouncedCallback(mockFunction, 200),
      );

      // Set up multiple calls
      act(() => {
        result.current('first');
      });

      act(() => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current('second');
      });

      act(() => {
        jest.advanceTimersByTime(50);
      });

      act(() => {
        result.current('third');
      });

      // Only the last call should execute
      act(() => {
        jest.advanceTimersByTime(200);
      });

      expect(mockFunction).toHaveBeenCalledTimes(1);
      expect(mockFunction).toHaveBeenCalledWith('third');
    });
  });

  describe('Real-world usage scenarios', () => {
    it('should work like a search input debouncer', () => {
      const searchFunction = jest.fn();
      const { result } = renderHook(() =>
        useDebouncedCallback(searchFunction, 300),
      );

      // Simulate user typing
      const searchTerms = ['a', 'ap', 'app', 'appl', 'apple'];

      act(() => {
        searchTerms.forEach((term) => {
          result.current(term);
        });
      });

      // Should not call during typing
      expect(searchFunction).not.toHaveBeenCalled();

      // Should call after user stops typing
      act(() => {
        jest.advanceTimersByTime(300);
      });

      expect(searchFunction).toHaveBeenCalledTimes(1);
      expect(searchFunction).toHaveBeenCalledWith('apple');
    });

    it('should work for API call debouncing', () => {
      const apiCall = jest.fn();
      const { result } = renderHook(() => useDebouncedCallback(apiCall, 500));

      // Simulate multiple API triggers
      act(() => {
        result.current({ userId: 1, action: 'update' });
        result.current({ userId: 1, action: 'update' });
        result.current({ userId: 1, action: 'update' });
      });

      act(() => {
        jest.advanceTimersByTime(500);
      });

      expect(apiCall).toHaveBeenCalledTimes(1);
      expect(apiCall).toHaveBeenCalledWith({ userId: 1, action: 'update' });
    });

    it('should handle form validation debouncing', () => {
      const validateFunction = jest.fn();
      const { result } = renderHook(() =>
        useDebouncedCallback(validateFunction, 250),
      );

      // Simulate user input in form field
      act(() => {
        result.current('user@');
        result.current('user@ex');
        result.current('user@exa');
        result.current('user@exam');
        result.current('user@example');
        result.current('user@example.');
        result.current('user@example.c');
        result.current('user@example.co');
        result.current('user@example.com');
      });

      expect(validateFunction).not.toHaveBeenCalled();

      act(() => {
        jest.advanceTimersByTime(250);
      });

      expect(validateFunction).toHaveBeenCalledTimes(1);
      expect(validateFunction).toHaveBeenCalledWith('user@example.com');
    });

    it('should handle function changes in real-world scenario', () => {
      const logSearch = jest.fn();
      const logFilter = jest.fn();

      const { result, rerender } = renderHook(
        ({ action }) => useDebouncedCallback(action, 300),
        { initialProps: { action: logSearch } },
      );

      // User starts typing in search
      act(() => {
        result.current('search term');
      });

      // User switches to filter mode before search executes
      rerender({ action: logFilter });

      // Original search should still execute
      act(() => {
        jest.advanceTimersByTime(300);
      });

      expect(logSearch).toHaveBeenCalledWith('search term');
      expect(logFilter).not.toHaveBeenCalled();

      // Now user uses filter
      act(() => {
        result.current('filter term');
      });

      act(() => {
        jest.advanceTimersByTime(300);
      });

      expect(logFilter).toHaveBeenCalledWith('filter term');
    });
  });
});
