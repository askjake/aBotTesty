import MockAdapter from 'axios-mock-adapter';
import axiosLibs from '@shared/ui/libs/axios.libs';
import {
  registerVaultService,
  updatePasswordVaultService,
  enableVaultService,
  disableVaultService,
  checkVaultRegisteredService,
  checkVaultStatusService,
  resetVaultModePasswordService,
} from '@/services/vault.services';
import { ZodError } from 'zod';
import { IncomingHttpHeaders } from 'node:http';

// Create a mock for axios
const mock = new MockAdapter(axiosLibs);

describe('Vault Services', () => {
  // Valid password for testing
  const validPassword = 'ValidP@ss123';
  const validNewPassword = 'NewV@lidPass456';

  // Mock headers
  const mockIncomingHeaders: IncomingHttpHeaders = {
    'x-auth-request-email': 'test.test@dish.com',
    cookie: 'session=abc123',
    'user-agent': 'Jest Test',
  };

  beforeEach(() => {
    // Reset the mock before each test
    mock.reset();

    // Clear all mocks
    jest.clearAllMocks();
  });

  describe('registerVaultService', () => {
    it('should register vault successfully with valid password', async () => {
      // Mock the response
      mock.onPost('/vault/setup').reply(200, { success: true });

      const result = await registerVaultService({
        password: validPassword,
      });

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0]?.url).toBe('/vault/setup');
      expect(JSON.parse(mock.history.post[0]?.data)).toEqual({
        password: validPassword,
      });

      // Check the result
      expect(result).toEqual({ success: true });
    });

    it('should throw validation error for password without lowercase', async () => {
      const invalidPassword = 'INVALID@123';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for password without uppercase', async () => {
      const invalidPassword = 'invalid@123';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for password without number', async () => {
      const invalidPassword = 'Invalid@abc';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for password without special character', async () => {
      const invalidPassword = 'Invalid123';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for password that is too short', async () => {
      const invalidPassword = 'Sh@rt1';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for password that is too long', async () => {
      const invalidPassword = 'ThisP@sswordIs1WayTooLongForTheValidator';

      // Expect the function to throw a ZodError
      await expect(
        registerVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onPost('/vault/setup').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        registerVaultService({
          password: validPassword,
        }),
      ).rejects.toThrow();
    });
  });

  describe('updatePasswordVaultService', () => {
    it('should update vault password successfully', async () => {
      // Mock the response
      mock.onPost('/vault/change-password').reply(200, { success: true });

      const result = await updatePasswordVaultService({
        oldPassword: validPassword,
        newPassword: validNewPassword,
      });

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0]?.url).toBe('/vault/change-password');
      expect(JSON.parse(mock.history.post[0]?.data)).toEqual({
        oldPassword: validPassword,
        newPassword: validNewPassword,
      });

      // Check the result
      expect(result).toEqual({ success: true });
    });

    it('should throw validation error when old and new passwords are the same', async () => {
      // Expect the function to throw a ZodError
      await expect(
        updatePasswordVaultService({
          oldPassword: validPassword,
          newPassword: validPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for invalid old password', async () => {
      const invalidPassword = 'invalid';

      // Expect the function to throw a ZodError
      await expect(
        updatePasswordVaultService({
          oldPassword: invalidPassword,
          newPassword: validNewPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should throw validation error for invalid new password', async () => {
      const invalidPassword = 'invalid';

      // Expect the function to throw a ZodError
      await expect(
        updatePasswordVaultService({
          oldPassword: validPassword,
          newPassword: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onPost('/vault/change-password')
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        updatePasswordVaultService({
          oldPassword: validPassword,
          newPassword: validNewPassword,
        }),
      ).rejects.toThrow();
    });
  });

  describe('enableVaultService', () => {
    it('should enable vault successfully with valid password', async () => {
      // Mock the response
      mock.onPost('/vault/verify').reply(200, { success: true });

      const result = await enableVaultService({
        password: validPassword,
      });

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0]?.url).toBe('/vault/verify');
      expect(JSON.parse(mock.history.post[0]?.data)).toEqual({
        password: validPassword,
      });

      // Check the result
      expect(result).toEqual({ success: true });
    });

    it('should throw validation error for invalid password', async () => {
      const invalidPassword = 'invalid';

      // Expect the function to throw a ZodError
      await expect(
        enableVaultService({
          password: invalidPassword,
        }),
      ).rejects.toThrow(ZodError);

      // Check that no request was made
      expect(mock.history.post.length).toBe(0);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onPost('/vault/verify').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(
        enableVaultService({
          password: validPassword,
        }),
      ).rejects.toThrow();
    });
  });

  describe('disableVaultService', () => {
    it('should disable vault successfully', async () => {
      // Mock the response
      mock.onPost('/vault/disable').reply(200, { success: true });

      const result = await disableVaultService();

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0]?.url).toBe('/vault/disable');
      expect(JSON.parse(mock.history.post[0]?.data)).toEqual({});

      // Check the result
      expect(result).toEqual({ success: true });
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onPost('/vault/disable').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(disableVaultService()).rejects.toThrow();
    });
  });

  describe('checkVaultRegisteredService', () => {
    it('should check if vault is registered successfully without headers', async () => {
      // Mock the response
      mock.onGet('/vault/exists').reply(200, { exists: true });

      const result = await checkVaultRegisteredService();

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/vault/exists');

      // Check that no headers were sent
      expect(mock.history.get[0]?.headers).toEqual(
        expect.not.objectContaining({
          'x-auth-request-email': expect.anything(),
          cookie: expect.anything(),
        }),
      );

      // Check the result
      expect(result).toBe(true);
    });

    it('should check if vault is registered successfully with headers', async () => {
      // Mock the response
      mock.onGet('/vault/exists').reply(200, { exists: false });

      const result = await checkVaultRegisteredService(mockIncomingHeaders);

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/vault/exists');

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
        }),
      );

      // Check the result
      expect(result).toBe(false);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onGet('/vault/exists').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(checkVaultRegisteredService()).rejects.toThrow();
    });
  });

  describe('checkVaultStatusService', () => {
    it('should check vault status successfully without headers', async () => {
      // Mock the response
      mock.onGet('/vault/status').reply(200, { enabled: true });

      const result = await checkVaultStatusService();

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/vault/status');

      // Check that no headers were sent
      expect(mock.history.get[0]?.headers).toEqual(
        expect.not.objectContaining({
          'x-auth-request-email': expect.anything(),
          cookie: expect.anything(),
        }),
      );

      // Check the result
      expect(result).toBe(true);
    });

    it('should check vault status successfully with headers', async () => {
      // Mock the response
      mock.onGet('/vault/status').reply(200, { enabled: false });

      const result = await checkVaultStatusService(mockIncomingHeaders);

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0]?.url).toBe('/vault/status');

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
        }),
      );

      // Check the result
      expect(result).toBe(false);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onGet('/vault/status').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(checkVaultStatusService()).rejects.toThrow();
    });
  });

  describe('resetVaultModePasswordService', () => {
    it('should reset vault password successfully', async () => {
      // Mock the response
      mock.onPost('/vault/reset-password').reply(200, { success: true });

      const result = await resetVaultModePasswordService();

      // Check that the request was made correctly
      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0]?.url).toBe('/vault/reset-password');

      // The data should be an empty object or not present
      // If it's an empty string, that's also acceptable
      if (mock.history.post[0]?.data) {
        expect(JSON.parse(mock.history.post[0]?.data)).toEqual({});
      }

      // Check the result
      expect(result).toBe(true);
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock
        .onPost('/vault/reset-password')
        .reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(resetVaultModePasswordService()).rejects.toThrow();
    });
  });
});
