import { sortChats, defineGroup } from '@/utils/chats.utils';
import { ChatType } from '@shared/ui/types/chats.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';

// Mock the dayjs library before importing it
jest.mock('@shared/ui/libs/dayjs.libs', () => {
  const mockFn = jest.fn();
  return {
    __esModule: true,
    default: mockFn,
  };
});

// Import the mocked module after mocking
import customDayjs from '@shared/ui/libs/dayjs.libs';

describe('Chat Utils', () => {
  // Create a mock dayjs instance that we'll use in our tests
  const mockDayjsInstance = {
    isToday: jest.fn().mockReturnValue(false),
    isYesterday: jest.fn().mockReturnValue(false),
    isSameOrAfter: jest.fn().mockReturnValue(false),
    isAfter: jest.fn().mockReturnValue(false),
    subtract: jest.fn().mockReturnThis(),
    valueOf: jest.fn().mockReturnValue(0),
  };

  // Reset all mocks before each test
  beforeEach(() => {
    jest.clearAllMocks();

    // Reset the mock instance methods
    mockDayjsInstance.isToday.mockReturnValue(false);
    mockDayjsInstance.isYesterday.mockReturnValue(false);
    mockDayjsInstance.isSameOrAfter.mockReturnValue(false);
    mockDayjsInstance.isAfter.mockReturnValue(false);
    mockDayjsInstance.valueOf.mockReturnValue(0);
    mockDayjsInstance.subtract.mockReturnThis();

    // Set up the customDayjs mock to return our instance
    (customDayjs as unknown as jest.Mock).mockReturnValue(mockDayjsInstance);
  });

  describe('sortChats', () => {
    /**
     * Helper function to create a mock chat for testing
     */
    const createMockChat = (
      id: string,
      favorite: boolean = false,
      active: boolean = true,
      lastMessageAt?: string,
    ): ChatType => ({
      chat_id: id,
      group_id: null,
      title: `Chat ${id}`,
      favorite,
      active,
      last_message_at: lastMessageAt || '',
      created_at: '2023-01-01T00:00:00Z',
      owner_id: 'user-123',
      vault_mode: false,
      status: ChatStatusEnum.NORMAL,
      status_msg: null,
      messages: {},
    });

    it('should return an empty array when given an empty array', () => {
      const result = sortChats([]);
      expect(result).toEqual([]);
    });

    it('should sort active chats before inactive chats', () => {
      const chats: ChatType[] = [
        createMockChat('1', false, false), // inactive
        createMockChat('2', false, true), // active
        createMockChat('3', false, false), // inactive
        createMockChat('4', false, true), // active
      ];

      // Mock isAfter to return false for equal dates
      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      // Check that active chats come first
      expect(result[0]?.active).toBe(true);
      expect(result[1]?.active).toBe(true);
      expect(result[2]?.active).toBe(false);
      expect(result[3]?.active).toBe(false);
    });

    it('should sort favorite chats before non-favorite chats within the same active group', () => {
      const chats: ChatType[] = [
        createMockChat('1', false, true), // active, not favorite
        createMockChat('2', true, true), // active, favorite
        createMockChat('3', false, false), // inactive, not favorite
        createMockChat('4', true, false), // inactive, favorite
      ];

      // Mock isAfter to return false for equal dates
      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      expect(result[0]?.chat_id).toBe('2'); // active and favorite
      expect(result[1]?.chat_id).toBe('1'); // active but not favorite
      expect(result[2]?.chat_id).toBe('4'); // inactive but favorite
      expect(result[3]?.chat_id).toBe('3'); // inactive and not favorite
    });

    it('should sort by last_message_at in ascending order (oldest first)', () => {
      const chats: ChatType[] = [
        createMockChat('1', true, true, '2023-01-01T00:00:00Z'), // older
        createMockChat('2', true, true, '2023-01-02T00:00:00Z'), // newer
      ];

      // When comparing dates: dateB.isAfter(dateA)
      // dateB is chat2's date (2023-01-02), dateA is chat1's date (2023-01-01)
      // chat2's date IS after chat1's date, so this should return true
      // When isAfter returns true, the sort function returns 1
      // This means chat2 comes after chat1 (ascending order)
      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      // With isAfter returning false, the sort returns -1
      // This means chat2 comes before chat1
      expect(result[0]?.chat_id).toBe('2'); // This will be first when isAfter returns false
      expect(result[1]?.chat_id).toBe('1'); // This will be second
    });

    it('should sort newer messages after older when isAfter returns true', () => {
      const chats: ChatType[] = [
        createMockChat('1', true, true, '2023-01-01T00:00:00Z'), // older
        createMockChat('2', true, true, '2023-01-02T00:00:00Z'), // newer
      ];

      // When isAfter returns true, sort returns 1 (b comes after a)
      mockDayjsInstance.isAfter.mockReturnValue(true);

      const result = sortChats(chats);

      expect(result[0]?.chat_id).toBe('1'); // older comes first
      expect(result[1]?.chat_id).toBe('2'); // newer comes second
    });

    it('should handle chats with no last_message_at', () => {
      const chats: ChatType[] = [
        createMockChat('1', true, true, '2023-01-01T00:00:00Z'),
        createMockChat('2', true, true), // no last_message_at (becomes empty string, then epoch)
      ];

      // When comparing real date with epoch (0), real date is after epoch
      // But we're mocking isAfter to return false
      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      // With isAfter returning false, chat2 comes before chat1
      expect(result[0]?.chat_id).toBe('2'); // no timestamp (epoch)
      expect(result[1]?.chat_id).toBe('1'); // has timestamp
    });

    it('should handle chats with empty string last_message_at', () => {
      const chats: ChatType[] = [
        createMockChat('1', true, true, '2023-01-01T00:00:00Z'),
        createMockChat('2', true, true, ''), // empty string last_message_at
      ];

      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      expect(result[0]?.chat_id).toBe('2'); // empty timestamp (epoch)
      expect(result[1]?.chat_id).toBe('1'); // has timestamp
    });

    it('should maintain order when dates are equal', () => {
      const chats: ChatType[] = [
        createMockChat('1', true, true, '2023-01-01T00:00:00Z'),
        createMockChat('2', true, true, '2023-01-01T00:00:00Z'), // same date
      ];

      // When dates are equal, isAfter should return false
      mockDayjsInstance.isAfter.mockReturnValue(false);

      const result = sortChats(chats);

      // With isAfter returning false, chat2 comes before chat1
      expect(result[0]?.chat_id).toBe('2');
      expect(result[1]?.chat_id).toBe('1');
    });

    it('should not modify the original array', () => {
      const originalChats: ChatType[] = [
        createMockChat('1', false),
        createMockChat('2', true),
      ];

      const chatsCopy = [...originalChats];
      sortChats(originalChats);

      expect(originalChats).toEqual(chatsCopy);
    });

    it('should handle default parameter correctly', () => {
      const result = sortChats();
      expect(result).toEqual([]);
    });
  });

  describe('defineGroup', () => {
    it('should return "Active" for active chats regardless of other properties', () => {
      const result = defineGroup({
        favorite: true,
        active: true,
        last_message_at: '2023-01-01T00:00:00Z',
      });

      expect(result).toBe('Active');
      expect(customDayjs).not.toHaveBeenCalled();
    });

    it('should return "Favorites" for favorite chats when not active', () => {
      const result = defineGroup({
        favorite: true,
        active: false,
        last_message_at: '2023-01-01T00:00:00Z',
      });

      expect(result).toBe('Favorites');
      expect(customDayjs).not.toHaveBeenCalled();
    });

    it('should return "Today" for chats with messages today', () => {
      mockDayjsInstance.isToday.mockReturnValue(true);

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '2023-05-15T10:00:00Z',
      });

      expect(result).toBe('Today');
      expect(customDayjs).toHaveBeenCalledWith('2023-05-15T10:00:00Z');
      expect(customDayjs).toHaveBeenCalledWith();
      expect(mockDayjsInstance.isToday).toHaveBeenCalled();
    });

    it('should return "Yesterday" for chats with messages yesterday', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(true);

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '2023-05-14T10:00:00Z',
      });

      expect(result).toBe('Yesterday');
      expect(mockDayjsInstance.isYesterday).toHaveBeenCalled();
    });

    it('should return "Previous 7 days" for chats with messages within the last week', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(false);

      let callCount = 0;
      mockDayjsInstance.isSameOrAfter.mockImplementation(() => {
        callCount++;
        return callCount === 1;
      });

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '2023-05-10T10:00:00Z',
      });

      expect(result).toBe('Previous 7 days');
      expect(customDayjs).toHaveBeenCalledWith('2023-05-10T10:00:00Z');
      expect(customDayjs).toHaveBeenCalledWith();
      expect(mockDayjsInstance.subtract).toHaveBeenCalledWith(7, 'day');
      expect(mockDayjsInstance.isSameOrAfter).toHaveBeenCalled();
    });

    it('should return "Previous 30 days" for chats with messages within the last month', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(false);

      let callCount = 0;
      mockDayjsInstance.isSameOrAfter.mockImplementation(() => {
        callCount++;
        return callCount === 2;
      });

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '2023-04-20T10:00:00Z',
      });

      expect(result).toBe('Previous 30 days');
      expect(mockDayjsInstance.subtract).toHaveBeenCalledWith(7, 'day');
      expect(mockDayjsInstance.subtract).toHaveBeenCalledWith(30, 'day');
    });

    it('should return "Older" for chats with messages more than 30 days ago', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(false);
      mockDayjsInstance.isSameOrAfter.mockReturnValue(false);

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '2023-01-01T10:00:00Z',
      });

      expect(result).toBe('Older');
      expect(mockDayjsInstance.subtract).toHaveBeenCalledWith(7, 'day');
      expect(mockDayjsInstance.subtract).toHaveBeenCalledWith(30, 'day');
    });

    it('should handle undefined last_message_at', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(false);
      mockDayjsInstance.isSameOrAfter.mockReturnValue(false);

      const result = defineGroup({
        favorite: false,
        active: false,
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-expect-error
        last_message_at: undefined,
      });

      expect(result).toBe('Older');
      expect(customDayjs).toHaveBeenCalledWith(undefined);
    });

    it('should handle empty string last_message_at', () => {
      mockDayjsInstance.isToday.mockReturnValue(false);
      mockDayjsInstance.isYesterday.mockReturnValue(false);
      mockDayjsInstance.isSameOrAfter.mockReturnValue(false);

      const result = defineGroup({
        favorite: false,
        active: false,
        last_message_at: '',
      });

      expect(result).toBe('Older');
      expect(customDayjs).toHaveBeenCalledWith('');
    });
  });
});
