import type { Config } from 'jest';

const config: Config = {
  displayName: 'beta-reports',
  rootDir: '../../',
  testEnvironment: 'jsdom',
  clearMocks: true,

  setupFilesAfterEnv: ['<rootDir>/shared/jest-config/jest.setup.ts'],

  testMatch: [
    '<rootDir>/apps/beta-reports/**/__tests__/**/*.{test,spec}.{ts,tsx}',
    '<rootDir>/apps/beta-reports/**/tests/**/*.{test,spec}.{ts,tsx}',
    '<rootDir>/shared/jest-beta-reports/__tests__/**/*.{test,spec}.{ts,tsx}',
  ],

  moduleNameMapper: {
    '^@beta-reports/(.*)$': '<rootDir>/apps/beta-reports/src/$1',
    '^@/(.*)$': '<rootDir>/apps/beta-reports/src/$1',
    '^@shared/ui/(.*)$': '<rootDir>/shared/ui/src/$1',
    '^@shared/jest-config/(.*)$': '<rootDir>/shared/jest-config/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
    '\\.(jpg|jpeg|png|gif|svg|webp)$':
      '<rootDir>/shared/jest-config/__mocks__/fileMock.js',
    // Mock next/dynamic
    '^next/dynamic$': '<rootDir>/shared/jest-config/__mocks__/next/dynamic.tsx',
  },

  collectCoverageFrom: [
    'apps/beta-reports/src/**/*.{ts,tsx}',
    'shared/ui/src/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/__mocks__/**',
    '!**/*.types.ts',
    '!**/*.enums.ts',
    '!**/*.constants.ts?(x)',
    '!**/*.styled.tsx',
    '!**/*.props.ts',
  ],

  transform: {
    '^.+\\.(ts|tsx)$': [
      'ts-jest',
      {
        tsconfig: {
          jsx: 'react-jsx',
          esModuleInterop: true,
          allowSyntheticDefaultImports: true,
        },
      },
    ],
  },

  transformIgnorePatterns: [
    '/node_modules/(?!nanoid|@ant-design|antd|@rc-component|rc-.*).+\\.(js|jsx|ts|tsx)$',
  ],

  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/.next/',
    '\\.config\\.ts$',
    '\\.types\\.ts$',
    '\\.enums\\.ts$',
    '\\.interfaces\\.ts$',
    '\\.libs\\.ts$',
    '\\.props\\.ts$',
    '\\.constants\\.tsx?$',
    '\\.styled\\.tsx$',
  ],

  moduleDirectories: ['node_modules', '<rootDir>/shared/jest-config/__mocks__'],
  coverageDirectory: '<rootDir>/coverage/chats',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
};

export default config;
