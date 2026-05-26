import React from 'react';
import { screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';

// Mock console.error to avoid noise in tests
const mockConsoleError = jest
  .spyOn(console, 'error')
  .mockImplementation(() => {});

// Mock Ant Design components
const mockMessageError = jest.fn();
const mockNotificationError = jest.fn();

jest.mock('antd', () => ({
  App: {
    useApp: () => ({
      message: {
        error: mockMessageError,
      },
      notification: {
        error: mockNotificationError,
      },
    }),
  },
  GetProp: jest.fn(),
  Upload: {
    LIST_IGNORE: 'LIST_IGNORE',
  },
}));

jest.mock('@ant-design/x', () => ({
  Attachments: ({ onChange, items, beforeUpload, placeholder }: any) => {
    const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file && onChange) {
        const fileObj = {
          uid: `test-${file.name}`,
          name: file.name,
          type: file.type,
          size: file.size,
          status: 'uploading',
          originFileObj: file,
        };

        if (beforeUpload) {
          const result = beforeUpload(fileObj);
          if (result === false || result === 'LIST_IGNORE') {
            return;
          }
        }

        onChange({
          file: fileObj,
          fileList: [...(items || []), fileObj],
        });
      }
    };

    const handleRemove = (file: any) => {
      onChange({
        file,
        fileList: items.filter((item: any) => item.uid !== file.uid),
      });
    };

    const placeholderContent =
      typeof placeholder === 'function' ? placeholder('click') : placeholder;

    return (
      <div data-testid='attachments'>
        <div data-testid='placeholder-title'>{placeholderContent?.title}</div>
        <div data-testid='attached-files-count'>{items?.length || 0}</div>
        <input
          type='file'
          onChange={handleFileSelect}
          data-testid='file-input'
        />
        {items?.map((file: any) => (
          <div key={file.uid} data-testid={`file-item-${file.uid}`}>
            <span>{file.name}</span>
            <button
              data-testid={`remove-file-${file.uid}`}
              onClick={() => handleRemove(file)}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    );
  },
}));

jest.mock('@ant-design/icons', () => ({
  CloudUploadOutlined: () => <div data-testid='cloud-upload-icon'>☁️</div>,
}));

jest.mock('axios', () => ({
  create: jest.fn(() => ({
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  })),
  isAxiosError: jest.fn(),
}));

const mockHandleError = jest.fn();

jest.mock('@shared/ui/hooks/useHandleError.hook', () => ({
  __esModule: true,
  default: () => mockHandleError,
}));

jest.mock('@shared/ui/hooks/useDebounceCallback.hook', () => ({
  __esModule: true,
  default: (callback: any) => callback,
}));

jest.mock('@shared/ui/services/attachments.services', () => ({
  getAttachmentStatuses: jest.fn(),
}));

jest.mock(
  '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.styled',
  () => ({
    StyledSenderHeaderBlockContainer: ({ children, title, open }: any) => (
      <div data-testid='sender-header-container' data-open={open}>
        <div data-testid='container-title'>{title}</div>
        <div data-testid='container-content'>{children}</div>
      </div>
    ),
  }),
);

jest.mock('@shared/ui/constants/validation.constants', () => ({
  ALLOWED_DOCUMENTS_MIME_TYPES: { 'application/pdf': true },
  ALLOWED_IMAGES_MIME_TYPES: { 'image/jpeg': true, 'image/png': true },
  ALLOWED_FILES_MIME_TYPES_STRING: 'application/pdf,image/jpeg,image/png',
  MAX_DOCUMENT_COUNT: 5,
  MAX_IMAGE_COUNT: 10,
}));

jest.mock('@shared/ui/validators/attachments.validators', () => ({
  checkAttachmentValidator: {
    safeParse: jest.fn(() => ({ success: true })),
  },
  uploadAttachmentsValidator: jest.fn(),
}));

jest.mock('@shared/ui/utils/attachments.utils', () => ({
  calcTotalAttachments: jest.fn(() => 0),
}));

jest.mock('@shared/ui/utils/errors.utils', () => ({
  formatFileCountError: jest.fn(() => 'File count error'),
}));

import { AttachmentType } from '@shared/ui/types/attachments.types';
import { AttachmentStatusEnum } from '@shared/ui/enums/chats.enums';
import * as attachmentServices from '@shared/ui/services/attachments.services';
import * as attachmentValidators from '@shared/ui/validators/attachments.validators';
import axios from 'axios';
import { SenderHeaderBlockProps } from '@shared/ui/components/molecules/Chat/SenderHeaderBlock/SenderHeaderBlock.props';
import SenderHeaderBlock from '@shared/ui/components/molecules/Chat/SenderHeaderBlock';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

const mockGetAttachmentStatuses =
  attachmentServices.getAttachmentStatuses as jest.MockedFunction<
    typeof attachmentServices.getAttachmentStatuses
  >;

const mockCheckAttachmentValidator =
  attachmentValidators.checkAttachmentValidator as jest.Mocked<
    typeof attachmentValidators.checkAttachmentValidator
  >;

const mockAxios = axios as jest.Mocked<typeof axios>;

const defaultProps: SenderHeaderBlockProps = {
  open: true,
  onOpenChange: jest.fn(),
  onAddAttachment: jest.fn().mockResolvedValue({ attachments: [] }),
  onRemoveAttachment: jest.fn(),
  setLoading: jest.fn(),
  componentRef: { current: null },
};

const createMockFile = (name: string, type: string, size = 1000): File => {
  return new File(['content'], name, { type });
};

const createMockAttachment = (
  overrides: Partial<AttachmentType> = {},
): AttachmentType => ({
  attachment_id: 'att-123',
  filename: 'test.pdf',
  media_type: 'application/pdf',
  status: AttachmentStatusEnum.READY,
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-01T00:00:00Z',
  vault_mode: false,
  owner_id: 'user-123',
  ...overrides,
});

describe('SenderHeaderBlock', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAxios.isAxiosError.mockReturnValue(false);
    mockConsoleError.mockClear();
    mockMessageError.mockClear();
    mockNotificationError.mockClear();
    // @ts-ignore
    mockCheckAttachmentValidator.safeParse.mockReturnValue({ success: true });
    mockGetAttachmentStatuses.mockResolvedValue({ status: {} });
  });

  it('renders component with attachments interface', async () => {
    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(<SenderHeaderBlock {...defaultProps} />, { store });

    await waitFor(() => {
      expect(screen.getByTestId('sender-header-container')).toBeInTheDocument();
    });

    expect(screen.getByTestId('container-title')).toHaveTextContent(
      'Attachments',
    );
    expect(screen.getByTestId('file-input')).toBeInTheDocument();
  });

  it('renders when closed', async () => {
    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(<SenderHeaderBlock {...defaultProps} open={false} />, {
      store,
    });

    await waitFor(() => {
      expect(screen.getByTestId('sender-header-container')).toBeInTheDocument();
    });

    expect(screen.getByTestId('sender-header-container')).toHaveAttribute(
      'data-open',
      'false',
    );
  });

  it('handles successful file upload', async () => {
    const mockFile = createMockFile('test.pdf', 'application/pdf');
    const mockAttachment = createMockAttachment({
      filename: 'test.pdf',
      media_type: 'application/pdf',
    });

    const mockOnAddAttachment = jest
      .fn()
      .mockResolvedValue({ attachments: [mockAttachment] });

    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(
      <SenderHeaderBlock
        {...defaultProps}
        onAddAttachment={mockOnAddAttachment}
      />,
      { store },
    );

    await waitFor(() => {
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input');

    await userEvent.upload(fileInput, mockFile);

    await waitFor(() => {
      expect(mockOnAddAttachment).toHaveBeenCalled();
    });
  });

  it('handles upload errors', async () => {
    const mockFile = createMockFile('test.pdf', 'application/pdf');
    const axiosError = {
      response: {
        data: { type: 'Upload Error', description: 'Server error' },
      },
    };

    mockAxios.isAxiosError.mockReturnValue(true);
    const mockOnAddAttachment = jest.fn().mockRejectedValue(axiosError);

    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(
      <SenderHeaderBlock
        {...defaultProps}
        onAddAttachment={mockOnAddAttachment}
      />,
      { store },
    );

    await waitFor(() => {
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input');

    await userEvent.upload(fileInput, mockFile);

    await waitFor(() => {
      expect(mockNotificationError).toHaveBeenCalledWith({
        title: 'Upload Error',
        description: 'Server error',
      });
    });
  });

  it('handles validation errors', async () => {
    mockCheckAttachmentValidator.safeParse.mockReturnValue({
      success: false,
      error: {
        format: () => ({
          attachment: { _errors: ['Invalid file type'] },
        }),
      } as any,
    });

    const mockFile = createMockFile('test.txt', 'text/plain');

    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(<SenderHeaderBlock {...defaultProps} />, { store });

    await waitFor(() => {
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input');

    await userEvent.upload(fileInput, mockFile);

    await waitFor(() => {
      expect(mockMessageError).toHaveBeenCalledWith('Invalid file type');
    });
  });

  it('prevents duplicate file uploads', async () => {
    const mockFile1 = createMockFile('test.pdf', 'application/pdf');
    const mockFile2 = createMockFile('test.pdf', 'application/pdf');

    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(<SenderHeaderBlock {...defaultProps} />, { store });

    await waitFor(() => {
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input');

    await userEvent.upload(fileInput, mockFile1);

    mockMessageError.mockClear();

    await userEvent.upload(fileInput, mockFile2);

    await waitFor(() => {
      expect(mockMessageError).toHaveBeenCalledWith(
        'File "test.pdf" is already uploaded',
      );
    });
  });

  it('handles file removal', async () => {
    const mockFile = createMockFile('test.pdf', 'application/pdf');
    const mockAttachment = createMockAttachment({
      attachment_id: 'att-123',
      filename: 'test.pdf',
    });

    const mockOnAddAttachment = jest
      .fn()
      .mockResolvedValue({ attachments: [mockAttachment] });

    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(
      <SenderHeaderBlock
        {...defaultProps}
        onAddAttachment={mockOnAddAttachment}
      />,
      { store },
    );

    await waitFor(() => {
      expect(screen.getByTestId('file-input')).toBeInTheDocument();
    });

    const fileInput = screen.getByTestId('file-input');

    await userEvent.upload(fileInput, mockFile);

    await waitFor(() => {
      expect(screen.getByTestId('attached-files-count')).toHaveTextContent('1');
    });

    const removeButton = screen.getByTestId(/remove-file-test-test\.pdf/);

    await userEvent.click(removeButton);

    await waitFor(() => {
      expect(defaultProps.onRemoveAttachment).toHaveBeenCalledWith('att-123');
      expect(screen.getByTestId('attached-files-count')).toHaveTextContent('0');
    });
  });

  it('exposes resetAttachments method through ref', async () => {
    const ref = React.createRef<any>();
    const store = mockStore({
      chats: { aiTyping: false },
      settings: {},
    });

    renderLayout(<SenderHeaderBlock {...defaultProps} componentRef={ref} />, {
      store,
    });

    await waitFor(() => {
      expect(ref.current).toBeTruthy();
    });

    expect(ref.current).toHaveProperty('resetAttachments');
    expect(typeof ref.current?.resetAttachments).toBe('function');
  });
});
