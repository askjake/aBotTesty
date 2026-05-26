import MockAdapter from 'axios-mock-adapter';
import axiosLibs from '@shared/ui/libs/axios.libs';
import {
  createMessage,
  getMessage,
  getMessages,
  getMessageVersion,
  createMessageVersion,
  changeMessageVersion,
} from '@shared/ui/services/messages.services';
import { ZodError } from 'zod';
import { RoleEnum } from '@shared/ui/enums/chats.enums';
import {
  MessageVersionsType,
  MessageVersionsInfoType,
  RawMessageType,
  OriginalMessageType,
} from '@shared/ui/types/messages.types';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';
import { PaginationType } from '@shared/ui/types/pagination.types';

// Create a mock for axios - use passThrough for unhandled requests to see what's happening
const mock = new MockAdapter(axiosLibs, { onNoMatch: 'throwException' });

// Define a mock stream class that can be used in tests
class MockStream {
  constructor() {
    // Empty constructor
  }
}

describe('Messages Services', () => {
  // Mock data
  const mockChatId = 'chat-123';
  const mockMessageId = 'msg-123';

  const mockMessage: RawMessageType = {
    [mockMessageId]: {
      content: {
        0: {
          type: MessageTypeEnum.TEXT,
          text: 'Test message content',
        },
      },
      role: RoleEnum.USER,
      version_count: 1,
      version_index: 0,
      created_at: '2023-01-01T00:00:00Z',
      attachments: [],
    },
  };

  const mockOriginalMessage: OriginalMessageType = {
    message_id: mockMessageId,
    content: {
      0: {
        type: MessageTypeEnum.TEXT,
        text: 'Test message content',
      },
    },
    role: RoleEnum.USER,
    version_count: 1,
    version_index: 0,
    created_at: '2023-01-01T00:00:00Z',
    attachments: [],
  };

  const mockMessagesResponse: PaginationType<OriginalMessageType> = {
    docs: [mockOriginalMessage],
    totalDocs: 1,
    limit: 25,
    totalPages: 1,
    page: 1,
    hasPrevPage: false,
    hasNextPage: false,
    prevPage: 0,
    nextPage: 0,
  };

  const mockMessageVersions: MessageVersionsType = {
    version: [
      {
        version_index: 0,
        content: 'Original content',
        created_at: '2023-01-01T00:00:00Z',
      },
      {
        version_index: 1,
        content: 'Updated content',
        created_at: '2023-01-02T00:00:00Z',
      },
    ],
  };

  const mockMessageVersionsInfo: MessageVersionsInfoType = {
    active_message: mockMessage,
    branched_history: [],
  };

  const mockAttachment = {
    attachment_id: '123e4567-e89b-12d3-a456-426614174000',
    filename: 'test.jpg',
    media_type: 'image/jpeg',
    owner_id: 'user-123',
  };

  const mockConfig = {
    reasoning: false,
  };

  // Mock implementations
  const mockStreamResponse = new MockStream();

  beforeEach(() => {
    // Reset the mock before each test
    mock.reset();

    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('createMessage', () => {
    it('should create a message successfully', async () => {
      // Mock the axios post method for stream responses
      jest.spyOn(axiosLibs, 'post').mockResolvedValueOnce({
        data: mockStreamResponse,
      } as any);

      const result = await createMessage({
        chat_id: mockChatId,
        content: 'Test message content',
        attachments: [],
        message_config: mockConfig,
      });

      // Check that the function was called with correct parameters
      expect(axiosLibs.post).toHaveBeenCalledWith(
        `/chats/${mockChatId}/messages`,
        {
          content: 'Test message content',
          attachments: [],
          message_config: mockConfig,
        },
        expect.objectContaining({
          responseType: 'stream',
          adapter: 'fetch',
        }),
      );

      // Check the result is our mocked stream
      expect(result).toBe(mockStreamResponse);
    });

    it('should create a message with attachments successfully', async () => {
      // Mock the axios post method for stream responses
      jest.spyOn(axiosLibs, 'post').mockResolvedValueOnce({
        data: mockStreamResponse,
      } as any);

      const result = await createMessage({
        chat_id: mockChatId,
        content: 'Test message with attachment',
        attachments: [mockAttachment],
        message_config: mockConfig,
      });

      // Check that the function was called with correct parameters
      expect(axiosLibs.post).toHaveBeenCalledWith(
        `/chats/${mockChatId}/messages`,
        {
          content: 'Test message with attachment',
          attachments: [mockAttachment],
          message_config: mockConfig,
        },
        expect.objectContaining({
          responseType: 'stream',
          adapter: 'fetch',
        }),
      );

      // Check the result is our mocked stream
      expect(result).toBe(mockStreamResponse);
    });

    it('should create a message with reasoning config enabled', async () => {
      // Mock the axios post method for stream responses
      jest.spyOn(axiosLibs, 'post').mockResolvedValueOnce({
        data: mockStreamResponse,
      } as any);

      const reasoningConfig = { reasoning: true };

      const result = await createMessage({
        chat_id: mockChatId,
        content: 'Test message with reasoning',
        attachments: [],
        message_config: reasoningConfig,
      });

      // Check that the function was called with correct parameters
      expect(axiosLibs.post).toHaveBeenCalledWith(
        `/chats/${mockChatId}/messages`,
        {
          content: 'Test message with reasoning',
          attachments: [],
          message_config: reasoningConfig,
        },
        expect.objectContaining({
          responseType: 'stream',
          adapter: 'fetch',
        }),
      );

      // Check the result is our mocked stream
      expect(result).toBe(mockStreamResponse);
    });

    it('should use default values when not provided', async () => {
      // Mock the axios post method for stream responses
      jest.spyOn(axiosLibs, 'post').mockResolvedValueOnce({
        data: mockStreamResponse,
      } as any);

      const result = await createMessage({
        chat_id: mockChatId,
        content: 'Test message content',
        message_config: mockConfig,
        attachments: [],
      });

      // Check that the function was called with default attachments array
      expect(axiosLibs.post).toHaveBeenCalledWith(
        `/chats/${mockChatId}/messages`,
        {
          content: 'Test message content',
          attachments: [],
          message_config: mockConfig,
        },
        expect.objectContaining({
          responseType: 'stream',
          adapter: 'fetch',
        }),
      );

      // Check the result is our mocked stream
      expect(result).toBe(mockStreamResponse);
    });

    it('should throw validation error for empty content', async () => {
      // Expect the function to throw a ZodError for empty content
      await expect(
        createMessage({
          chat_id: mockChatId,
          content: '',
          attachments: [],
          message_config: mockConfig,
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should throw validation error for whitespace-only content', async () => {
      // Expect the function to throw a ZodError for whitespace-only content
      await expect(
        createMessage({
          chat_id: mockChatId,
          content: '   ',
          attachments: [],
          message_config: mockConfig,
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should throw validation error for invalid attachment UUID', async () => {
      const invalidAttachment = {
        attachment_id: 'invalid-uuid',
        filename: 'test.jpg',
        media_type: 'image/jpeg',
        owner_id: 'user-123',
      };

      // Expect the function to throw a ZodError for invalid attachment
      await expect(
        createMessage({
          chat_id: mockChatId,
          content: 'Test message content',
          attachments: [invalidAttachment],
          message_config: mockConfig,
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should throw validation error for empty attachment fields', async () => {
      const invalidAttachment = {
        attachment_id: '123e4567-e89b-12d3-a456-426614174000',
        filename: '',
        media_type: '',
        owner_id: '',
      };

      // Expect the function to throw a ZodError for invalid attachment
      await expect(
        createMessage({
          chat_id: mockChatId,
          content: 'Test message content',
          attachments: [invalidAttachment],
          message_config: mockConfig,
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should handle API errors', async () => {
      // Mock the axios implementation to throw an error
      jest
        .spyOn(axiosLibs, 'post')
        .mockRejectedValueOnce(new Error('Server error'));

      // Expect the function to throw an error
      await expect(
        createMessage({
          chat_id: mockChatId,
          content: 'Test message content',
          attachments: [],
          message_config: mockConfig,
        }),
      ).rejects.toThrow('Server error');
    });
  });

  describe('getMessage', () => {
    it('should fetch a message successfully', async () => {
      // Mock the response
      mock
        .onGet(`/chats/${mockChatId}/messages/${mockMessageId}`)
        .reply(200, mockMessage);

      const result = await getMessage({
        chat_id: mockChatId,
        message_id: mockMessageId,
      });

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe(
        `/chats/${mockChatId}/messages/${mockMessageId}`,
      );

      // Check the result
      expect(result).toEqual(mockMessage);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onGet(`/chats/${mockChatId}/messages/${mockMessageId}`)
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        getMessage({
          chat_id: mockChatId,
          message_id: mockMessageId,
        }),
      ).rejects.toThrow();
    });

    it('should handle not found errors', async () => {
      // Mock the response with a not found error
      mock
        .onGet(`/chats/${mockChatId}/messages/non-existent`)
        .reply(404, { message: 'Message not found' });

      // Expect the function to throw an error
      await expect(
        getMessage({
          chat_id: mockChatId,
          message_id: 'non-existent',
        }),
      ).rejects.toThrow();
    });
  });

  describe('getMessages', () => {
    it('should fetch messages successfully with default pagination', async () => {
      // Use regex to match URL with or without trailing slash and any query params
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, mockMessagesResponse);
      // @ts-ignore
      const result = await getMessages({
        chat_id: mockChatId,
      });

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.params).toEqual({ page: 1, limit: 15 });

      // Check the result
      expect(result).toEqual(mockMessagesResponse);
      expect(result.docs.length).toBe(1);
      expect(result.docs[0]?.message_id).toBe(mockMessageId);
    });

    it('should fetch messages with custom pagination', async () => {
      const customPaginationResponse: PaginationType<OriginalMessageType> = {
        ...mockMessagesResponse,
        page: 2,
        limit: 10,
      };

      // Mock the response
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, customPaginationResponse);

      const result = await getMessages({
        chat_id: mockChatId,
        page: 2,
        limit: 10,
      });

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.params).toEqual({ page: 2, limit: 10 });

      // Check the result
      expect(result).toEqual(customPaginationResponse);
      expect(result.page).toBe(2);
      expect(result.limit).toBe(10);
    });

    it('should fetch messages with incoming headers', async () => {
      const incomingHeaders = {
        'x-auth-request-email': 'test.test@dish.com',
        cookie: 'session=abc123',
      };

      // Mock the response
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, mockMessagesResponse);

      // @ts-ignore
      const result = await getMessages({
        chat_id: mockChatId,
        incomingHeaders,
      });

      // Check that the request was made with correct headers
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.headers).toMatchObject({
        'x-auth-request-email': 'test.test@dish.com',
        cookie: 'session=abc123',
      });

      // Check the result
      expect(result).toEqual(mockMessagesResponse);
    });

    it('should handle empty messages list', async () => {
      const emptyResponse: PaginationType<OriginalMessageType> = {
        docs: [],
        totalDocs: 0,
        limit: 25,
        totalPages: 0,
        page: 1,
        hasPrevPage: false,
        hasNextPage: false,
        prevPage: 0,
        nextPage: 0,
      };

      // Mock the response
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, emptyResponse);
      // @ts-ignore
      const result = await getMessages({
        chat_id: mockChatId,
      });

      // Check the result
      expect(result.docs).toEqual([]);
      expect(result.totalDocs).toBe(0);
      expect(result.hasNextPage).toBe(false);
      expect(result.hasPrevPage).toBe(false);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error

      await expect(
        // @ts-ignore
        getMessages({
          chat_id: mockChatId,
        }),
      ).rejects.toThrow();
    });

    it('should handle not found errors', async () => {
      // Mock the response with a not found error
      mock
        .onGet(new RegExp(`/chats/non-existent/messages/?`))
        .reply(404, { message: 'Chat not found' });

      // Expect the function to throw an error
      await expect(
        // @ts-ignore
        getMessages({
          chat_id: 'non-existent',
        }),
      ).rejects.toThrow();
    });

    it('should handle pagination with hasNextPage true', async () => {
      const paginatedResponse: PaginationType<OriginalMessageType> = {
        ...mockMessagesResponse,
        hasNextPage: true,
        nextPage: 2,
        totalPages: 5,
      };

      // Mock the response
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, paginatedResponse);
      // @ts-ignore
      const result = await getMessages({
        chat_id: mockChatId,
      });

      // Check pagination info
      expect(result.hasNextPage).toBe(true);
      expect(result.nextPage).toBe(2);
      expect(result.totalPages).toBe(5);
    });

    it('should handle pagination with hasPrevPage true', async () => {
      const paginatedResponse: PaginationType<OriginalMessageType> = {
        ...mockMessagesResponse,
        page: 3,
        hasPrevPage: true,
        prevPage: 2,
        hasNextPage: true,
        nextPage: 4,
      };

      // Mock the response
      mock
        .onGet(new RegExp(`/chats/${mockChatId}/messages/?`))
        .reply(200, paginatedResponse);

      // @ts-ignore
      const result = await getMessages({
        chat_id: mockChatId,
        page: 3,
      });

      // Check pagination info
      expect(result.page).toBe(3);
      expect(result.hasPrevPage).toBe(true);
      expect(result.prevPage).toBe(2);
      expect(result.hasNextPage).toBe(true);
      expect(result.nextPage).toBe(4);
    });
  });

  describe('getMessageVersion', () => {
    it('should fetch message versions successfully', async () => {
      // Mock the response
      mock
        .onGet(`/chats/${mockChatId}/messages/${mockMessageId}/version`)
        .reply(200, mockMessageVersions);

      const result = await getMessageVersion({
        chat_id: mockChatId,
        message_id: mockMessageId,
      });

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe(
        `/chats/${mockChatId}/messages/${mockMessageId}/version`,
      );

      // Check the result
      expect(result).toEqual(mockMessageVersions);
      expect(result.version.length).toBe(2);
      expect(result.version[0]?.version_index).toBe(0);
      expect(result.version[1]?.version_index).toBe(1);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onGet(`/chats/${mockChatId}/messages/${mockMessageId}/version`)
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        getMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
        }),
      ).rejects.toThrow();
    });
  });

  describe('createMessageVersion', () => {
    it('should create a message version successfully', async () => {
      // Mock the axios post method for stream responses
      jest.spyOn(axiosLibs, 'post').mockResolvedValueOnce({
        data: mockStreamResponse,
      } as any);

      const result = await createMessageVersion({
        chat_id: mockChatId,
        message_id: mockMessageId,
        content: 'New version content',
      });

      // Check that the function was called with correct parameters
      expect(axiosLibs.post).toHaveBeenCalledWith(
        `/chats/${mockChatId}/messages/${mockMessageId}/versions`,
        {
          content: 'New version content',
        },
        expect.objectContaining({
          responseType: 'stream',
          adapter: 'fetch',
        }),
      );

      // Check the result is our mocked stream
      expect(result).toBe(mockStreamResponse);
    });

    it('should throw validation error when content is not provided', async () => {
      // This should fail validation since content is required
      await expect(
        createMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
        } as any),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should throw validation error for empty content', async () => {
      // Expect the function to throw a ZodError for empty content
      await expect(
        createMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          content: '',
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should throw validation error for whitespace-only content', async () => {
      // Expect the function to throw a ZodError for whitespace-only content
      await expect(
        createMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          content: '   ',
        }),
      ).rejects.toThrow(ZodError);

      // Check that axios.post was not called
      expect(axiosLibs.post).not.toHaveBeenCalled();
    });

    it('should handle API errors', async () => {
      // Mock the axios implementation to throw an error
      jest
        .spyOn(axiosLibs, 'post')
        .mockRejectedValueOnce(new Error('Server error'));

      // Expect the function to throw an error
      await expect(
        createMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          content: 'New version content',
        }),
      ).rejects.toThrow('Server error');
    });
  });

  describe('changeMessageVersion', () => {
    it('should change message version successfully', async () => {
      // Mock the response
      mock
        .onPut(`/chats/${mockChatId}/messages/${mockMessageId}/versions`)
        .reply(200, mockMessageVersionsInfo);

      const result = await changeMessageVersion({
        chat_id: mockChatId,
        message_id: mockMessageId,
        version_index: 1,
      });

      // Check that the request was made correctly
      expect(mock.history.put.length).toBe(1);
      expect(mock.history.put[0]?.url).toBe(
        `/chats/${mockChatId}/messages/${mockMessageId}/versions`,
      );
      expect(JSON.parse(mock.history.put[0]?.data)).toEqual({
        version_index: 1,
      });

      // Check the result
      expect(result).toEqual(mockMessageVersionsInfo);
    });

    it('should change to version index 0 successfully', async () => {
      // Mock the response
      mock
        .onPut(`/chats/${mockChatId}/messages/${mockMessageId}/versions`)
        .reply(200, mockMessageVersionsInfo);

      const result = await changeMessageVersion({
        chat_id: mockChatId,
        message_id: mockMessageId,
        version_index: 0,
      });

      // Check that the request was made correctly
      expect(mock.history.put.length).toBe(1);
      expect(JSON.parse(mock.history.put[0]?.data)).toEqual({
        version_index: 0,
      });

      // Check the result
      expect(result).toEqual(mockMessageVersionsInfo);
    });

    it('should throw validation error for negative version index', async () => {
      // Expect the function to throw a ZodError for negative version index
      await expect(
        changeMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          version_index: -1,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.put.length).toBe(0);
    });

    it('should accept decimal version index (since z.number() allows it)', async () => {
      // Mock the response
      mock
        .onPut(`/chats/${mockChatId}/messages/${mockMessageId}/versions`)
        .reply(200, mockMessageVersionsInfo);

      // This should work since z.number() accepts decimal numbers
      const result = await changeMessageVersion({
        chat_id: mockChatId,
        message_id: mockMessageId,
        version_index: 1.5,
      });

      // Check that the request was made correctly
      expect(mock.history.put.length).toBe(1);
      expect(JSON.parse(mock.history.put[0]?.data)).toEqual({
        version_index: 1.5,
      });

      // Check the result
      expect(result).toEqual(mockMessageVersionsInfo);
    });

    it('should throw validation error for non-number version index', async () => {
      // Expect the function to throw a ZodError for non-number version index
      await expect(
        changeMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          version_index: 'invalid' as any,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.put.length).toBe(0);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onPut(`/chats/${mockChatId}/messages/${mockMessageId}/versions`)
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        changeMessageVersion({
          chat_id: mockChatId,
          message_id: mockMessageId,
          version_index: 1,
        }),
      ).rejects.toThrow();
    });
  });
});
