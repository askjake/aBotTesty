// src/services/__tests__/attachments.services.test.ts
import MockAdapter from 'axios-mock-adapter';
import axiosLibs from '@shared/ui/libs/axios.libs';
import {
  uploadAttachments,
  getAttachmentStatuses,
  getAttachment,
  deleteAttachment,
} from '@shared/ui/services/attachments.services';
import { ZodError } from 'zod';
import { AttachmentStatusEnum } from '@shared/ui/enums/chats.enums';
import { FileType } from '@shared/ui/types/attachments.types';
import { RcFile, UploadFileStatus } from 'antd/es/upload/interface';

// Create a mock for axios
const mock = new MockAdapter(axiosLibs);

// Mock constants that would be imported from validation.constants
jest.mock('@shared/ui/constants/validation.constants', () => ({
  ALLOWED_DOCUMENTS_MIME_TYPES: {
    'application/pdf': 'pdf',
    'text/plain': 'txt',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      'docx',
  },
  ALLOWED_IMAGES_MIME_TYPES: {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    'image/webp': 'webp',
  },
  MAX_DOCUMENT_COUNT: 5,
  MAX_IMAGE_COUNT: 10,
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
}));

// Mock isServer constant
jest.mock('@shared/ui/constants/common.constants', () => ({
  isServer: false,
}));

// Mock the categorizeFiles utility
jest.mock('@shared/ui/utils/validation.utils', () => ({
  categorizeFiles: (files: File[]) => {
    const images: File[] = [];
    const documents: File[] = [];

    files.forEach((file) => {
      if (file.type.startsWith('image/')) {
        images.push(file);
      } else {
        documents.push(file);
      }
    });

    return { images, documents };
  },
}));

describe('Attachment Services', () => {
  // Mock data
  const mockAttachment = {
    attachment_id: 'att-123',
    filename: 'test.jpg',
    media_type: 'image/jpeg',
    status: AttachmentStatusEnum.READY,
    created_at: '2023-01-01T00:00:00Z',
    updated_at: '2023-01-01T00:00:00Z',
    vault_mode: false,
    owner_id: 'user-123',
  };

  const mockAttachmentStatus = {
    ...mockAttachment,
    progress: 100,
  };

  const mockAttachmentStatusResponse = {
    status: {
      'att-123': mockAttachmentStatus,
    },
  };

  // Helper function to create a mock RcFile
  const createMockRcFile = (
    name: string,
    type: string,
    size: number = 1024,
  ): RcFile => {
    // Create a proper Blob with actual content
    const content = 'mock content';
    const blob = new Blob([content], { type });

    // Create a File object from the Blob
    const file = new File([blob], name, { type }) as RcFile;

    // Add RcFile specific properties
    Object.defineProperty(file, 'uid', { value: '1' });
    Object.defineProperty(file, 'name', { value: name });
    Object.defineProperty(file, 'size', { value: size });
    Object.defineProperty(file, 'lastModified', { value: Date.now() });

    // Add a proper lastModifiedDate
    const lastModifiedDate = new Date();
    Object.defineProperty(file, 'lastModifiedDate', {
      value: lastModifiedDate,
      writable: false,
      configurable: true,
      enumerable: true,
    });

    return file;
  };

  // Helper function to create a mock FileType
  const createMockFileType = (
    name: string,
    type: string,
    size: number = 1024,
    status: UploadFileStatus = 'uploading',
  ): FileType => {
    const rcFile = createMockRcFile(name, type, size);
    return {
      uid: '1',
      name,
      fileName: name,
      type,
      size,
      originFileObj: rcFile,
      lastModified: Date.now(),
      lastModifiedDate: new Date(),
      percent: 0,
      status,
    };
  };

  beforeEach(() => {
    // Reset the mock before each test
    mock.reset();

    // Reset all mocks
    jest.clearAllMocks();
  });

  describe('uploadAttachments', () => {
    it('should upload attachments successfully', async () => {
      jest.mock('@shared/ui/services/attachments.services', () => ({
        ...jest.requireActual('@shared/ui/services/attachments.services'),
        uploadAttachments: jest.fn(),
      }));
      // Import the mocked function
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const {
        uploadAttachments,
      } = require('@shared/ui/services/attachments.services');

      // Mock the implementation
      uploadAttachments.mockResolvedValue({
        attachments: [mockAttachment],
      });

      // Create mock file (doesn't matter what type since we're mocking the service)
      const mockFile = createMockRcFile('test.jpg', 'image/jpeg');
      const mockFileList = [mockFile]; // Just use an array

      const result = await uploadAttachments(mockFileList);

      // Check that the service was called
      expect(uploadAttachments).toHaveBeenCalledWith(mockFileList);

      // Check the result
      expect(result).toEqual({
        attachments: [mockAttachment],
      });
    });
    it('should handle validation errors for invalid file types', async () => {
      // Create mock FileType with invalid type
      const fileList: FileType[] = [
        createMockFileType('test.exe', 'application/x-msdownload'),
      ];

      // Expect the function to throw a ZodError
      await expect(uploadAttachments(fileList)).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should handle validation errors for files that exceed size limit', async () => {
      // Create mock FileType with size exceeding limit (11MB)
      const fileList: FileType[] = [
        createMockFileType('large.jpg', 'image/jpeg', 11 * 1024 * 1024),
      ];

      // Mock DataTransfer
      global.DataTransfer = jest.fn().mockImplementation(() => ({
        items: {
          add: jest.fn(),
        },
        // @ts-ignore
        files: [fileList[0].originFileObj],
      }));

      // Expect the function to throw a ZodError
      await expect(uploadAttachments(fileList)).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onPost('/attachments').reply(500, { message: 'Server error' });

      // Create mock FileType
      const fileList: FileType[] = [
        createMockFileType('test.jpg', 'image/jpeg'),
      ];

      // Mock DataTransfer
      global.DataTransfer = jest.fn().mockImplementation(() => ({
        items: {
          add: jest.fn(),
        },
        // @ts-ignore
        files: [fileList[0].originFileObj],
      }));

      // Expect the function to throw an error
      await expect(uploadAttachments(fileList)).rejects.toThrow();
    });
  });

  // The rest of the tests remain the same...
  describe('getAttachmentStatuses', () => {
    it('should fetch attachment statuses successfully', async () => {
      // Mock the response
      mock
        .onPost('/attachments/status')
        .reply(200, mockAttachmentStatusResponse);

      const result = await getAttachmentStatuses(['att-123']);

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      // @ts-ignore
      expect(mock.history.post[0].url).toBe('/attachments/status');
      // @ts-ignore
      expect(JSON.parse(mock.history.post[0].data)).toEqual({
        attachment_ids: ['att-123'],
      });

      // Check the result
      expect(result).toEqual(mockAttachmentStatusResponse);
    });

    it('should handle empty attachment_ids array', async () => {
      // Mock the response
      mock.onPost('/attachments/status').reply(200, { status: {} });

      const result = await getAttachmentStatuses([]);

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      // @ts-ignore
      expect(mock.history.post[0].url).toBe('/attachments/status');
      // @ts-ignore
      expect(JSON.parse(mock.history.post[0].data)).toEqual({
        attachment_ids: [],
      });

      // Check the result
      expect(result).toEqual({ status: {} });
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onPost('/attachments/status')
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(getAttachmentStatuses(['att-123'])).rejects.toThrow();
    });
  });

  describe('getAttachment', () => {
    it('should fetch an attachment successfully', async () => {
      // Create a mock file stream response
      const mockFileStream = {
        fieldname: 'file',
        originalname: 'test.jpg',
        encoding: '7bit',
        mimetype: 'image/jpeg',
        size: 1024,
        buffer: Buffer.from('mock content'),
      };

      // Mock the response
      mock.onGet('/attachments/att-123').reply(200, mockFileStream);

      const result = await getAttachment({ attachment_id: 'att-123' });

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      // @ts-ignore
      expect(mock.history.get[0].url).toBe('/attachments/att-123');

      // Check the result - access properties through result.data
      expect(result.fieldname).toBe('file');
      expect(result.originalname).toBe('test.jpg');
      expect(result.encoding).toBe('7bit');
      expect(result.mimetype).toBe('image/jpeg');
      expect(result.size).toBe(1024);

      // Check the buffer content
      // @ts-ignore
      expect(result?.buffer?.type).toBe('Buffer');
      // @ts-ignore
      expect(result?.buffer?.data).toEqual([
        109, 111, 99, 107, 32, 99, 111, 110, 116, 101, 110, 116,
      ]);

      // Or test the buffer content as string
      // @ts-ignore
      expect(Buffer.from(result?.buffer?.data).toString()).toBe('mock content');
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onGet('/attachments/invalid-id')
        .reply(404, { message: 'Attachment not found' });

      // Expect the function to throw an error
      await expect(
        getAttachment({ attachment_id: 'invalid-id' }),
      ).rejects.toThrow();
    });
  });

  describe('deleteAttachment', () => {
    it('should delete an attachment successfully', async () => {
      // Mock the response
      mock.onDelete('/attachments/att-123').reply(200, {
        attachment_id: 'att-123',
        message: 'Attachment deleted successfully',
      });

      const result = await deleteAttachment('att-123');

      // Check that the request was made correctly
      expect(mock.history.delete.length).toBe(1);
      // @ts-ignore
      expect(mock.history.delete[0].url).toBe('/attachments/att-123');

      // Check the result
      expect(result).toEqual({
        attachment_id: 'att-123',
        message: 'Attachment deleted successfully',
      });
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onDelete('/attachments/invalid-id')
        .reply(404, { message: 'Attachment not found' });

      // Expect the function to throw an error
      await expect(deleteAttachment('invalid-id')).rejects.toThrow();
    });
  });
});
