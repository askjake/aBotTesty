import {
  formatFileCountError,
  formatFileSize,
  handleZodError,
  handleServerError,
} from '@shared/ui/utils/errors.utils';
import { FileValidationErrorType } from '@shared/ui/types/attachments.types';
import { ZodFormattedError } from 'zod';
import { NotificationInstance } from 'antd/lib/notification/interface';

// Mock console.error to avoid noise in test output
const mockConsoleError = jest
  .spyOn(console, 'error')
  .mockImplementation(() => {});

describe('File Utils', () => {
  afterEach(() => {
    mockConsoleError.mockClear();
  });

  afterAll(() => {
    mockConsoleError.mockRestore();
  });

  describe('formatFileCountError', () => {
    it('should return the error message if no details are provided', () => {
      const error: FileValidationErrorType = {
        type: 'image_count',
        message: 'Too many files',
      };

      const result = formatFileCountError(error);

      expect(result).toBe('Too many files');
    });

    it('should format image count error correctly for single excess file', () => {
      const error: FileValidationErrorType = {
        type: 'image_count',
        message: 'Too many images',
        details: {
          current: 6,
          maximum: 5,
          files: [
            { name: 'image1.jpg', type: 'image/jpeg' },
            { name: 'image2.jpg', type: 'image/jpeg' },
            { name: 'image3.jpg', type: 'image/jpeg' },
            { name: 'image4.jpg', type: 'image/jpeg' },
            { name: 'image5.jpg', type: 'image/jpeg' },
            { name: 'image6.jpg', type: 'image/jpeg' },
          ],
        },
      };

      const result = formatFileCountError(error);

      const expected = ['Too many images', 'Please remove 1 image.'].join('\n');

      expect(result).toBe(expected);
    });

    it('should format image count error correctly for multiple excess files', () => {
      const error: FileValidationErrorType = {
        type: 'image_count',
        message: 'Too many images',
        details: {
          current: 7,
          maximum: 5,
          files: [
            { name: 'image1.jpg', type: 'image/jpeg' },
            { name: 'image2.jpg', type: 'image/jpeg' },
            { name: 'image3.jpg', type: 'image/jpeg' },
            { name: 'image4.jpg', type: 'image/jpeg' },
            { name: 'image5.jpg', type: 'image/jpeg' },
            { name: 'image6.jpg', type: 'image/jpeg' },
            { name: 'image7.jpg', type: 'image/jpeg' },
          ],
        },
      };

      const result = formatFileCountError(error);

      const expected = ['Too many images', 'Please remove 2 images.'].join(
        '\n',
      );

      expect(result).toBe(expected);
    });

    it('should format document count error correctly', () => {
      const error: FileValidationErrorType = {
        type: 'document_count',
        message: 'Too many documents',
        details: {
          current: 4,
          maximum: 2,
          files: [
            { name: 'doc1.pdf', type: 'application/pdf' },
            { name: 'doc2.pdf', type: 'application/pdf' },
            { name: 'doc3.pdf', type: 'application/pdf' },
            { name: 'doc4.pdf', type: 'application/pdf' },
          ],
        },
      };

      const result = formatFileCountError(error);

      const expected = [
        'Too many documents',
        'Please remove 2 documents.',
      ].join('\n');

      expect(result).toBe(expected);
    });

    it('should format total count error correctly', () => {
      const error: FileValidationErrorType = {
        type: 'total_count',
        message: 'Too many files in total',
        details: {
          current: 6,
          maximum: 5,
          files: [
            { name: 'file1.jpg', type: 'image/jpeg' },
            { name: 'file2.pdf', type: 'application/pdf' },
            { name: 'file3.jpg', type: 'image/jpeg' },
            { name: 'file4.pdf', type: 'application/pdf' },
            { name: 'file5.jpg', type: 'image/jpeg' },
            { name: 'file6.pdf', type: 'application/pdf' },
          ],
        },
      };

      const result = formatFileCountError(error);

      const expected = [
        'Too many files in total',
        'Please remove 1 file.',
      ].join('\n');

      expect(result).toBe(expected);
    });

    it('should format invalid type error correctly', () => {
      const error: FileValidationErrorType = {
        type: 'invalid_type',
        message: 'Invalid file type',
        details: {
          current: 1,
          maximum: 0,
          files: [{ name: 'file.exe', type: 'application/x-msdownload' }],
        },
      };

      const result = formatFileCountError(error);

      const expected = ['Invalid file type', 'Please remove 1 file.'].join(
        '\n',
      );

      expect(result).toBe(expected);
    });

    it('should format invalid size error correctly', () => {
      const error: FileValidationErrorType = {
        type: 'invalid_size',
        message: 'File too large',
        details: {
          current: 1,
          maximum: 0,
          files: [{ name: 'large_file.mp4', type: 'video/mp4' }],
        },
      };

      const result = formatFileCountError(error);

      const expected = ['File too large', 'Please remove 1 file.'].join('\n');

      expect(result).toBe(expected);
    });
  });

  describe('formatFileSize', () => {
    it('should format bytes to MB with one decimal place', () => {
      expect(formatFileSize(1024 * 1024)).toBe('1.0MB');
      expect(formatFileSize(1024 * 1024 * 2.5)).toBe('2.5MB');
      expect(formatFileSize(1024 * 1024 * 0.1)).toBe('0.1MB');
      expect(formatFileSize(1024 * 1024 * 10.75)).toBe('10.8MB');
      expect(formatFileSize(0)).toBe('0.0MB');
    });

    it('should handle very large file sizes', () => {
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1024.0MB');
      expect(formatFileSize(1024 * 1024 * 1024 * 2)).toBe('2048.0MB');
    });

    it('should handle very small file sizes', () => {
      expect(formatFileSize(1024)).toBe('0.0MB'); // 1KB
      expect(formatFileSize(1)).toBe('0.0MB'); // 1 byte
    });
  });

  describe('handleZodError', () => {
    let mockNotification: NotificationInstance;

    beforeEach(() => {
      mockNotification = {
        error: jest.fn(),
        success: jest.fn(),
        info: jest.fn(),
        warning: jest.fn(),
        open: jest.fn(),
        destroy: jest.fn(),
      };
    });

    it('should handle simple zod error with one field', () => {
      const error = {
        _errors: [],
        name: { _errors: ['Name is required'] },
      } as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).toHaveBeenCalledTimes(1);
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "name"',
        description: 'Name is required',
      });
    });

    it('should handle zod error with multiple fields', () => {
      const error = {
        _errors: [],
        name: { _errors: ['Name is required'] },
        email: { _errors: ['Invalid email format'] },
      } as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).toHaveBeenCalledTimes(2);
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "name"',
        description: 'Name is required',
      });
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "email"',
        description: 'Invalid email format',
      });
    });

    it('should handle zod error with multiple errors in one field', () => {
      const error = {
        _errors: [],
        password: {
          _errors: [
            'Password is required',
            'Password must be at least 8 characters',
          ],
        },
      } as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).toHaveBeenCalledTimes(2);
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "password"',
        description: 'Password is required',
      });
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "password"',
        description: 'Password must be at least 8 characters',
      });
    });

    it('should handle nested zod errors', () => {
      // Use type assertion to allow nested structure
      const error = {
        _errors: [],
        user: {
          _errors: [],
          details: {
            _errors: [],
            address: {
              _errors: ['Invalid address'],
            },
          },
        },
      } as unknown as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).toHaveBeenCalledTimes(1);
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "address"',
        description: 'Invalid address',
      });
    });

    it('should handle deeply nested zod errors', () => {
      // Use type assertion to allow deeply nested structure
      const error = {
        _errors: [],
        form: {
          _errors: [],
          user: {
            _errors: [],
            contact: {
              _errors: [],
              details: {
                _errors: [],
                address: {
                  _errors: ['Invalid postal code'],
                },
              },
            },
          },
        },
      } as unknown as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).toHaveBeenCalledTimes(1);
      expect(mockNotification.error).toHaveBeenCalledWith({
        title: 'Validation error in the field "address"',
        description: 'Invalid postal code',
      });
    });

    it('should handle empty zod error object', () => {
      const error = {
        _errors: [],
      } as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).not.toHaveBeenCalled();
    });

    it('should handle zod error with empty _errors arrays', () => {
      const error = {
        _errors: [],
        name: { _errors: [] },
        email: { _errors: [] },
      } as ZodFormattedError<any>;

      handleZodError({ error, notification: mockNotification });

      expect(mockNotification.error).not.toHaveBeenCalled();
    });
  });

  describe('handleServerError', () => {
    it('should return notFound for 404 status', () => {
      const error = {
        response: {
          status: 404,
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({ notFound: true });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 404,
        }),
      );
    });

    it('should redirect to 403 page for 403 status', () => {
      const error = {
        response: {
          status: 403,
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination: '/403',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 403,
        }),
      );
    });

    it('should redirect to 500 page with error details from response.data.detail', () => {
      const error = {
        response: {
          status: 500,
          data: {
            type: 'Internal Server Error',
            detail: 'Database connection failed',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Internal%20Server%20Error&message=Database%20connection%20failed',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 500,
          type: 'Internal Server Error',
          message: 'Database connection failed',
        }),
      );
    });

    it('should redirect to 500 page with error details from response.data.description', () => {
      const error = {
        response: {
          status: 400,
          data: {
            type: 'Bad Request',
            description: 'Invalid request parameters',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Bad%20Request&message=Invalid%20request%20parameters',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 400,
          type: 'Bad Request',
          message: 'Invalid request parameters',
        }),
      );
    });

    it('should redirect to 500 page with error details from response.data.message', () => {
      const error = {
        response: {
          status: 422,
          data: {
            type: 'Validation Error',
            message: 'Required field missing',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Validation%20Error&message=Required%20field%20missing',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 422,
          type: 'Validation Error',
          message: 'Required field missing',
        }),
      );
    });

    it('should use default values when error details are missing', () => {
      const error = {
        response: {
          status: 500,
          data: {},
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Unknown%20error&message=Something%20went%20wrong',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Backend API Error',
          status: 500,
          type: 'Unknown error',
          message: 'Something went wrong',
        }),
      );
    });

    it('should handle error without response object', () => {
      const error = new Error('Network error');

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Unknown%20error&message=Something%20went%20wrong',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Internal Server Error',
          type: 'Unknown error',
          message: 'Something went wrong',
        }),
      );
    });

    it('should handle null/undefined error', () => {
      const result = handleServerError({ error: null });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Unknown%20error&message=Something%20went%20wrong',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          timestamp: expect.any(String),
          page: 'Unknown page',
          errorType: 'Internal Server Error',
          type: 'Unknown error',
          message: 'Something went wrong',
        }),
      );
    });

    it('should properly encode special characters in URL parameters', () => {
      const error = {
        response: {
          status: 500,
          data: {
            type: 'Error & Warning',
            detail: 'Message with spaces & special chars!',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Error%20%26%20Warning&message=Message%20with%20spaces%20%26%20special%20chars!',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalled();
    });

    it('should prioritize detail over description and message', () => {
      const error = {
        response: {
          status: 500,
          data: {
            type: 'Multiple Messages',
            detail: 'Detail message',
            description: 'Description message',
            message: 'Message field',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination: '/500?type=Multiple%20Messages&message=Detail%20message',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalled();
    });

    it('should prioritize description over message when detail is not available', () => {
      const error = {
        response: {
          status: 500,
          data: {
            type: 'Multiple Messages',
            description: 'Description message',
            message: 'Message field',
          },
        },
      };

      const result = handleServerError({ error });

      expect(result).toEqual({
        redirect: {
          destination:
            '/500?type=Multiple%20Messages&message=Description%20message',
          permanent: false,
        },
      });
      expect(mockConsoleError).toHaveBeenCalled();
    });

    it('should include ctx.resolvedUrl when ctx is provided', () => {
      const error = {
        response: {
          status: 500,
          data: {},
        },
      };
      const ctx = {
        resolvedUrl: '/test-page',
      } as any;

      handleServerError({ error, ctx });

      expect(mockConsoleError).toHaveBeenCalledWith(
        '[Server Error]',
        expect.objectContaining({
          page: '/test-page',
        }),
      );
    });
  });
});
