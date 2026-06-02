// __tests__/services/chatsGroups.services.test.ts
import axiosLibs from '@shared/ui/libs/axios.libs';
import { pickKeys } from '@shared/ui/utils/common.utils';
import { updateOrCreateChatGroupValidator } from '@/validators/chatsGroups.validators';
import { PaginationType } from '@shared/ui/types/pagination.types';
import { ChatGroupType } from '@shared/ui/types/chatGroup.types';
import {
  createChatGroup,
  deleteChatGroup,
  getChatsGroups,
  updateChatGroup,
} from '@/services/chatGroup.service';

// Mock dependencies
jest.mock('@shared/ui/libs/axios.libs');
jest.mock('@shared/ui/utils/common.utils');
jest.mock('@/validators/chatsGroups.validators');

const mockAxiosLib = axiosLibs as jest.Mocked<typeof axiosLibs>;
const mockPickKeys = pickKeys as jest.MockedFunction<typeof pickKeys>;
const mockValidator = updateOrCreateChatGroupValidator as jest.Mocked<
  typeof updateOrCreateChatGroupValidator
>;

describe('chatsGroups.services', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockValidator.parseAsync = jest.fn().mockResolvedValue({});
  });

  describe('getChatsGroups', () => {
    const mockChatGroup: ChatGroupType = {
      group_id: 'group-1',
      title: 'Test Group',
    };

    const mockPaginationResponse: PaginationType<ChatGroupType> = {
      docs: [mockChatGroup],
      totalDocs: 1,
      limit: 50,
      page: 1,
      totalPages: 1,
      hasNextPage: false,
      nextPage: 1,
      hasPrevPage: false,
      prevPage: 1,
    };

    it('should fetch chat groups with default parameters', async () => {
      mockAxiosLib.get.mockResolvedValue({ data: mockPaginationResponse });

      const result = await getChatsGroups({
        page: 1,
        limit: 50,
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 1,
          limit: 50,
          search: '',
        },
      });
      expect(result).toEqual(mockPaginationResponse);
    });

    it('should fetch chat groups with custom parameters', async () => {
      mockAxiosLib.get.mockResolvedValue({ data: mockPaginationResponse });

      const result = await getChatsGroups({
        page: 2,
        limit: 25,
        search: 'test search',
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 2,
          limit: 25,
          search: 'test search',
        },
      });
      expect(result).toEqual(mockPaginationResponse);
    });

    it('should include headers when incomingHeaders are provided', async () => {
      const incomingHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
        'other-header': 'should-be-filtered',
      };

      const pickedHeaders = {
        'x-auth-request-email': 'test@example.com',
        cookie: 'session=abc123',
      };

      mockPickKeys.mockReturnValue(pickedHeaders);
      mockAxiosLib.get.mockResolvedValue({ data: mockPaginationResponse });

      const result = await getChatsGroups({
        page: 1,
        limit: 50,
        incomingHeaders,
      });

      expect(mockPickKeys).toHaveBeenCalledWith({
        obj: incomingHeaders,
        keysToPick: ['x-auth-request-email', 'cookie'],
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 1,
          limit: 50,
          search: '',
        },
        headers: pickedHeaders,
      });

      expect(result).toEqual(mockPaginationResponse);
    });

    it('should handle API errors', async () => {
      const error = new Error('API Error');
      mockAxiosLib.get.mockRejectedValue(error);

      await expect(
        getChatsGroups({
          page: 1,
          limit: 50,
        }),
      ).rejects.toThrow('API Error');
    });

    it('should use default values for optional parameters', async () => {
      mockAxiosLib.get.mockResolvedValue({ data: mockPaginationResponse });

      await getChatsGroups({
        page: 1,
        limit: 50,
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 1,
          limit: 50,
          search: '',
        },
      });
    });
  });

  describe('createChatGroup', () => {
    const mockChatGroup: ChatGroupType = {
      group_id: 'new-group-1',
      title: 'New Test Group',
    };

    it('should create a chat group successfully', async () => {
      mockAxiosLib.post.mockResolvedValue({ data: mockChatGroup });

      const result = await createChatGroup({
        title: 'New Test Group',
      });

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: 'New Test Group',
      });

      expect(mockAxiosLib.post).toHaveBeenCalledWith('/chats-groups', {
        title: 'New Test Group',
      });

      expect(result).toEqual(mockChatGroup);
    });

    it('should validate input before making API call', async () => {
      const validationError = new Error('Validation failed');
      mockValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        createChatGroup({
          title: '',
        }),
      ).rejects.toThrow('Validation failed');

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: '',
      });

      expect(mockAxiosLib.post).not.toHaveBeenCalled();
    });

    it('should handle API errors during creation', async () => {
      const apiError = new Error('API Error');
      mockAxiosLib.post.mockRejectedValue(apiError);

      await expect(
        createChatGroup({
          title: 'Valid Title',
        }),
      ).rejects.toThrow('API Error');

      expect(mockValidator.parseAsync).toHaveBeenCalled();
      expect(mockAxiosLib.post).toHaveBeenCalled();
    });

    it('should handle different title lengths', async () => {
      mockAxiosLib.post.mockResolvedValue({ data: mockChatGroup });

      // Test minimum length
      await createChatGroup({
        title: 'A',
      });

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: 'A',
      });

      // Test maximum length (40 characters)
      const longTitle = 'A'.repeat(40);
      await createChatGroup({
        title: longTitle,
      });

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: longTitle,
      });
    });
  });

  describe('updateChatGroup', () => {
    const mockUpdatedChatGroup: ChatGroupType = {
      group_id: 'group-1',
      title: 'Updated Test Group',
    };

    it('should update a chat group successfully', async () => {
      mockAxiosLib.put.mockResolvedValue({ data: mockUpdatedChatGroup });

      const result = await updateChatGroup({
        id: 'group-1',
        title: 'Updated Test Group',
      });

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: 'Updated Test Group',
      });

      expect(mockAxiosLib.put).toHaveBeenCalledWith('/chats-groups/group-1', {
        title: 'Updated Test Group',
      });

      expect(result).toEqual(mockUpdatedChatGroup);
    });

    it('should validate input before making API call', async () => {
      const validationError = new Error('Validation failed');
      mockValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        updateChatGroup({
          id: 'group-1',
          title: '',
        }),
      ).rejects.toThrow('Validation failed');

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: '',
      });

      expect(mockAxiosLib.put).not.toHaveBeenCalled();
    });

    it('should handle API errors during update', async () => {
      const apiError = new Error('API Error');
      mockAxiosLib.put.mockRejectedValue(apiError);

      await expect(
        updateChatGroup({
          id: 'group-1',
          title: 'Valid Title',
        }),
      ).rejects.toThrow('API Error');

      expect(mockValidator.parseAsync).toHaveBeenCalled();
      expect(mockAxiosLib.put).toHaveBeenCalled();
    });

    it('should handle different group IDs', async () => {
      mockAxiosLib.put.mockResolvedValue({ data: mockUpdatedChatGroup });

      await updateChatGroup({
        id: 'different-group-id',
        title: 'Updated Title',
      });

      expect(mockAxiosLib.put).toHaveBeenCalledWith(
        '/chats-groups/different-group-id',
        {
          title: 'Updated Title',
        },
      );
    });

    it('should handle special characters in group ID', async () => {
      mockAxiosLib.put.mockResolvedValue({ data: mockUpdatedChatGroup });

      const specialId = 'group-with-special-chars-123';
      await updateChatGroup({
        id: specialId,
        title: 'Updated Title',
      });

      expect(mockAxiosLib.put).toHaveBeenCalledWith(
        `/chats-groups/${specialId}`,
        {
          title: 'Updated Title',
        },
      );
    });
  });

  describe('deleteChatGroup', () => {
    const mockDeleteResponse: Pick<ChatGroupType, 'group_id'> = {
      group_id: 'deleted-group-1',
    };

    it('should delete a chat group successfully', async () => {
      mockAxiosLib.delete.mockResolvedValue({ data: mockDeleteResponse });

      const result = await deleteChatGroup('group-1');

      expect(mockAxiosLib.delete).toHaveBeenCalledWith('/chats-groups/group-1');
      expect(result).toEqual(mockDeleteResponse);
    });

    it('should handle API errors during deletion', async () => {
      const apiError = new Error('API Error');
      mockAxiosLib.delete.mockRejectedValue(apiError);

      await expect(deleteChatGroup('group-1')).rejects.toThrow('API Error');

      expect(mockAxiosLib.delete).toHaveBeenCalledWith('/chats-groups/group-1');
    });

    it('should handle different group IDs', async () => {
      mockAxiosLib.delete.mockResolvedValue({ data: mockDeleteResponse });

      await deleteChatGroup('different-group-id');

      expect(mockAxiosLib.delete).toHaveBeenCalledWith(
        '/chats-groups/different-group-id',
      );
    });

    it('should handle special characters in group ID', async () => {
      mockAxiosLib.delete.mockResolvedValue({ data: mockDeleteResponse });

      const specialId = 'group-with-special-chars-123';
      await deleteChatGroup(specialId);

      expect(mockAxiosLib.delete).toHaveBeenCalledWith(
        `/chats-groups/${specialId}`,
      );
    });

    it('should handle empty string ID', async () => {
      mockAxiosLib.delete.mockResolvedValue({ data: mockDeleteResponse });

      await deleteChatGroup('');

      expect(mockAxiosLib.delete).toHaveBeenCalledWith('/chats-groups/');
    });
  });

  describe('Error Handling', () => {
    it('should propagate network errors', async () => {
      const networkError = new Error('Network Error');
      mockAxiosLib.get.mockRejectedValue(networkError);

      await expect(
        getChatsGroups({
          page: 1,
          limit: 50,
        }),
      ).rejects.toThrow('Network Error');
    });

    it('should handle timeout errors', async () => {
      const timeoutError = new Error('Timeout');
      mockAxiosLib.post.mockRejectedValue(timeoutError);

      await expect(
        createChatGroup({
          title: 'Test',
        }),
      ).rejects.toThrow('Timeout');
    });

    it('should handle validation errors with specific messages', async () => {
      const validationError = new Error('Title must be at least 1 character');
      mockValidator.parseAsync.mockRejectedValue(validationError);

      await expect(
        updateChatGroup({
          id: 'group-1',
          title: '',
        }),
      ).rejects.toThrow('Title must be at least 1 character');
    });
  });

  describe('Edge Cases', () => {
    it('should handle null group_id in response', async () => {
      const chatGroupWithNullId: ChatGroupType = {
        group_id: null,
        title: 'Test Group',
      };

      mockAxiosLib.get.mockResolvedValue({
        data: {
          docs: [chatGroupWithNullId],
          totalDocs: 1,
          limit: 50,
          page: 1,
          totalPages: 1,
          hasNextPage: false,
          nextPage: 1,
          hasPrevPage: false,
          prevPage: 1,
        },
      });

      const result = await getChatsGroups({
        page: 1,
        limit: 50,
      });

      expect(result?.docs[0]?.group_id).toBeNull();
    });

    it('should handle empty docs array', async () => {
      const emptyResponse: PaginationType<ChatGroupType> = {
        docs: [],
        totalDocs: 0,
        limit: 50,
        page: 1,
        totalPages: 0,
        hasNextPage: false,
        nextPage: 1,
        hasPrevPage: false,
        prevPage: 1,
      };

      mockAxiosLib.get.mockResolvedValue({ data: emptyResponse });

      const result = await getChatsGroups({
        page: 1,
        limit: 50,
      });

      expect(result.docs).toHaveLength(0);
      expect(result.totalDocs).toBe(0);
    });

    it('should handle large pagination numbers', async () => {
      mockAxiosLib.get.mockResolvedValue({ data: {} });

      await getChatsGroups({
        page: 999999,
        limit: 1000,
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 999999,
          limit: 1000,
          search: '',
        },
      });
    });

    it('should handle Unicode characters in search', async () => {
      mockAxiosLib.get.mockResolvedValue({ data: {} });

      await getChatsGroups({
        page: 1,
        limit: 50,
        search: '测试 🚀 émojis',
      });

      expect(mockAxiosLib.get).toHaveBeenCalledWith('/chats-groups', {
        params: {
          page: 1,
          limit: 50,
          search: '测试 🚀 émojis',
        },
      });
    });

    it('should handle Unicode characters in titles', async () => {
      mockAxiosLib.post.mockResolvedValue({ data: {} });

      await createChatGroup({
        title: '测试组 🚀',
      });

      expect(mockValidator.parseAsync).toHaveBeenCalledWith({
        title: '测试组 🚀',
      });

      expect(mockAxiosLib.post).toHaveBeenCalledWith('/chats-groups', {
        title: '测试组 🚀',
      });
    });
  });
});
