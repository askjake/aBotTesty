import type { Config } from 'jest';

const config: Config = {
  rootDir: '../../',

  projects: [
    '<rootDir>/shared/jest-shared/jest.config.ts',
    '<rootDir>/shared/jest-chats/jest.config.ts',
    '<rootDir>/shared/jest-beta-reports/jest.config.ts',
  ],

  collectCoverageFrom: [
    'apps/**/*.{ts,tsx}',
    'shared/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/node_modules/**',
    '!**/__mocks__/**',
    '!**/jest-*/**',
  ],

  clearMocks: true,
  collectCoverage: true,
  coverageProvider: 'v8',
  testEnvironment: 'jsdom',
  coverageDirectory: '<rootDir>/coverage',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
};

export default config;
