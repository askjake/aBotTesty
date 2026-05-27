import { renderHook } from '@testing-library/react';
import { App } from 'antd';
import axios from 'axios';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';

jest.mock('antd', () => ({
  App: {
    useApp: jest.fn(),
  },
}));

jest.mock('axios');
jest.mock('@shared/ui/utils/errors.utils');

describe('useHandleError', () => {
  let mockNotification: { error: jest.MockedFunction<any> };
  let consoleLogSpy: jest.SpyInstance;

  beforeEach(() => {
    mockNotification = { error: jest.fn() };
    (App.useApp as jest.Mock).mockReturnValue({
      notification: mockNotification,
    });
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    jest.clearAllMocks();
    (axios.isAxiosError as unknown as jest.Mock).mockReturnValue(false);
  });

  afterEach(() => {
    consoleLogSpy.mockRestore();
  });

  it('should return an error handler function', () => {
    const { result } = renderHook(() => useHandleError());
    expect(typeof result.current).toBe('function');
  });

  it('should log all errors to console', () => {
    const { result } = renderHook(() => useHandleError());
    const testError = new Error('Test error');

    result.current(testError);
    expect(consoleLogSpy).toHaveBeenCalledWith(testError);
  });

  describe('API errors (have response property OR axios.isAxiosError is true)', () => {
    it('should handle error with array detail', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: {
            detail: [{ msg: 'Error 1' }, { msg: 'Error 2' }],
          },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledTimes(2);
      expect(mockNotification.error).toHaveBeenNthCalledWith(1, {
        title: 'API error',
        description: 'Error 1',
      });
      expect(mockNotification.error).toHaveBeenNthCalledWith(2, {
        title: 'API error',
        description: 'Error 2',
      });
    });

    it('should handle error with response property', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: { description: 'Error with response' },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Error with response',
      });
    });

    it('should handle error with detail string', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: { detail: 'Test detail' },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Test detail',
      });
    });

    it('should handle error with message fallback when has response', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        message: 'Network error',
        response: { data: {} },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Network error',
      });
    });

    it('should handle axios error without response', () => {
      const { result } = renderHook(() => useHandleError());

      (axios.isAxiosError as unknown as jest.Mock).mockReturnValue(true);
      result.current({
        message: 'Network Error',
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Network Error',
      });
    });

    it('should handle error with default fallback when has response', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: { data: {} },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Something went wrong',
      });
    });

    it('should handle empty detail array (no notifications)', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: { detail: [] },
        },
      });

      expect(mockNotification.error).not.toHaveBeenCalled();
    });

    it('should handle null as API error when axios.isAxiosError returns true', () => {
      const { result } = renderHook(() => useHandleError());

      (axios.isAxiosError as unknown as jest.Mock).mockReturnValue(true);
      result.current(null);

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Something went wrong',
      });
    });

    it('should prioritize description over detail', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        title: 'Error message',
        response: {
          data: {
            description: 'Error description',
            detail: 'Error detail',
          },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Error description',
      });
    });
  });

  describe('Unknown errors (no response property AND axios.isAxiosError is false)', () => {
    it('should handle Error objects as unknown errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current(new Error('Generic error'));

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });

    it('should handle objects with message property as unknown errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        title: 'Custom error message',
        someOtherProperty: 'value',
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });

    it('should handle string errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current('String error');

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });

    it('should handle null errors when axios.isAxiosError returns false', () => {
      const { result } = renderHook(() => useHandleError());

      result.current(null);

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });

    it('should handle plain objects without response property', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({ someProperty: 'value' });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });

    it('should handle undefined errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current(undefined);

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Unknown internal error',
        description: 'Something went wrong',
      });
    });
  });

  describe('Real-world scenarios', () => {
    it('should handle API validation errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: {
            detail: [
              { msg: 'Email is required' },
              { msg: 'Password must be at least 8 characters' },
            ],
          },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledTimes(2);
      expect(mockNotification.error).toHaveBeenNthCalledWith(1, {
        title: 'API error',
        description: 'Email is required',
      });
      expect(mockNotification.error).toHaveBeenNthCalledWith(2, {
        title: 'API error',
        description: 'Password must be at least 8 characters',
      });
    });

    it('should handle server errors', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: {
            description: 'Internal server error',
          },
          status: 500,
        },
      });

      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'API error',
        description: 'Internal server error',
      });
    });

    it('should handle malformed detail array items', () => {
      const { result } = renderHook(() => useHandleError());

      result.current({
        response: {
          data: {
            detail: [
              { msg: 'Valid message' },
              { invalidProperty: 'No msg property' },
            ],
          },
        },
      });

      expect(mockNotification.error).toHaveBeenCalledTimes(2);
      expect(mockNotification.error).toHaveBeenNthCalledWith(1, {
        title: 'API error',
        description: 'Valid message',
      });
      expect(mockNotification.error).toHaveBeenNthCalledWith(2, {
        title: 'API error',
        description: undefined,
      });
    });
  });
});
