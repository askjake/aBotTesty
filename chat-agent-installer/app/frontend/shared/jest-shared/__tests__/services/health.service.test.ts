import MockAdapter from 'axios-mock-adapter';
import axiosLibs from '@shared/ui/libs/axios.libs';
import { getHealth } from '@shared/ui/services/health.services';
import { HealthType } from '@shared/ui/types/health.types';
import { HealthStatusEnum } from '@shared/ui/enums/health.enums';

// Create a mock for axios
const mock = new MockAdapter(axiosLibs);

describe('Health Services', () => {
  // Mock data based on the actual HealthType interface and enum
  const mockHealthData: HealthType = {
    status: HealthStatusEnum.HEALTHY,
    version: '1.0.0',
    timestamp: '2023-01-01T00:00:00Z',
  };

  beforeEach(() => {
    // Reset the mock before each test
    mock.reset();
  });

  describe('getHealth', () => {
    it('should fetch health status successfully', async () => {
      // Mock the response
      mock.onGet('/health').reply(200, mockHealthData);

      const result = await getHealth();

      // Check that the request was made correctly
      expect(mock.history.get.length).toBe(1);
      expect(mock.history?.get[0]?.url).toBe('/health');

      // Check the result
      expect(result).toEqual(mockHealthData);
      expect(result.status).toBe(HealthStatusEnum.HEALTHY);
      expect(result.version).toBe('1.0.0');
      expect(result.timestamp).toBe('2023-01-01T00:00:00Z');
    });

    it('should handle API errors', async () => {
      // Mock the response with an error
      mock.onGet('/health').reply(500, { message: 'Server error' });

      // Expect the function to throw an error
      await expect(getHealth()).rejects.toThrow();
    });

    it('should handle network errors', async () => {
      // Mock a network error
      mock.onGet('/health').networkError();

      // Expect the function to throw an error
      await expect(getHealth()).rejects.toThrow();
    });

    it('should handle timeout errors', async () => {
      // Mock a timeout error
      mock.onGet('/health').timeout();

      // Expect the function to throw an error
      await expect(getHealth()).rejects.toThrow();
    });

    it('should handle unhealthy status', async () => {
      // Mock a response with unhealthy status
      const unhealthyData: HealthType = {
        status: HealthStatusEnum.UNHEALTHY,
        version: '1.0.0',
        timestamp: '2023-01-01T00:00:00Z',
      };

      mock.onGet('/health').reply(200, unhealthyData);

      const result = await getHealth();

      // Check the result
      expect(result).toEqual(unhealthyData);
      expect(result.status).toBe(HealthStatusEnum.UNHEALTHY);
    });
  });
});
