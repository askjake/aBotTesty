import MockAdapter from 'axios-mock-adapter';
import axiosLibs from '@shared/ui/libs/axios.libs';
import { getUser } from '@shared/ui/services/user.services';
import { UserType } from '@shared/ui/types/user.types';
import { IncomingHttpHeaders } from 'node:http';

// Create a mock for axios
const mock = new MockAdapter(axiosLibs);

describe('User Services', () => {
  // Mock data
  const mockUser: UserType = {
    email: 'test.test@dish.com',
    first_name: 'Test',
    last_name: 'User',
    last_release_date: null,
  };

  // Mock headers
  const mockIncomingHeaders: IncomingHttpHeaders = {
    'x-auth-request-email': 'test.test@dish.com',
    cookie: 'session=abc123',
    'user-agent': 'Jest Test',
    host: 'localhost',
    accept: 'application/json',
  };

  beforeEach(() => {
    // Reset the mock before each test
    mock.reset();

    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('getUser', () => {
    it('should fetch user data successfully without headers', async () => {
      // Mock the response
      mock.onGet('/whoami').reply(200, mockUser);

      const result = await getUser();

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/whoami');

      // Check that no headers were sent
      expect(mock.history.get[0]?.headers).toEqual(
        expect.not.objectContaining({
          'x-auth-request-email': expect.anything(),
          cookie: expect.anything(),
        }),
      );

      // Check the result
      expect(result).toEqual(mockUser);
    });

    it('should fetch user data successfully with headers', async () => {
      // Mock the response
      mock.onGet('/whoami').reply(200, mockUser);

      const result = await getUser(mockIncomingHeaders);

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/whoami');

      // Check that only the specified headers were sent
      expect(mock.history.get[0]?.headers).toEqual(
        expect.objectContaining({
          'x-auth-request-email': 'test.test@dish.com',
          cookie: 'session=abc123',
        }),
      );

      // Check that other headers were not sent
      expect(mock.history.get[0]?.headers).not.toEqual(
        expect.objectContaining({
          'user-agent': 'Jest Test',
          host: 'localhost',
          accept: 'application/json',
        }),
      );

      // Check the result
      expect(result).toEqual(mockUser);
    });

    it('should handle partial headers correctly', async () => {
      // Mock the response
      mock.onGet('/whoami').reply(200, mockUser);

      // Create partial headers
      const partialHeaders: IncomingHttpHeaders = {
        'x-auth-request-email': 'test.test@dish.com',
        // No cookie header
        'user-agent': 'Jest Test',
      };

      const result = await getUser(partialHeaders);

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/whoami');

      // Check that only the specified headers were sent
      expect(mock.history.get[0]?.headers).toEqual(
        expect.objectContaining({
          'x-auth-request-email': 'test.test@dish.com',
        }),
      );

      // Check that other headers were not sent
      expect(mock.history.get[0]?.headers).not.toEqual(
        expect.objectContaining({
          cookie: expect.anything(),
          'user-agent': 'Jest Test',
        }),
      );

      // Check the result
      expect(result).toEqual(mockUser);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onGet('/whoami').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(getUser()).rejects.toThrow();
    });

    it('should handle unauthorized errors', async () => {
      // Mock the response with an unauthorized error
      mock.onGet('/whoami').reply(401, { message: 'Unauthorized' });

      // Expect the function to throw an error
      await expect(getUser()).rejects.toThrow();
    });

    it('should handle network errors', async () => {
      // Mock a network error
      mock.onGet('/whoami').networkError();

      // Expect the function to throw an error
      await expect(getUser()).rejects.toThrow();
    });
  });
});
