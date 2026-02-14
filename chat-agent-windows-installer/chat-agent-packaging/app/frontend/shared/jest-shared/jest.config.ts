import type { Config } from 'jest';

const config: Config = {
  displayName: 'shared',
  rootDir: '../../',
  testEnvironment: 'jsdom',
  clearMocks: true,

  setupFilesAfterEnv: ['<rootDir>/shared/jest-config/jest.setup.ts'],

  testMatch: [
    // Tests in jest-shared directory
    '<rootDir>/shared/jest-shared/__tests__/**/*.{test,spec}.{ts,tsx}',
    // Tests in UI components (co-located)
    '<rootDir>/shared/ui/**/__tests__/**/*.{test,spec}.{ts,tsx}',
    '<rootDir>/shared/ui/**/tests/**/*.{test,spec}.{ts,tsx}',
  ],

  moduleNameMapper: {
    '^@chats/(.*)$': '<rootDir>/apps/chats/src/$1',
    '^@/(.*)$': '<rootDir>/apps/chats/src/$1',
    '^@shared/ui/(.*)$': '<rootDir>/shared/ui/src/$1',
    '^@shared/jest-config/(.*)$': '<rootDir>/shared/jest-config/$1',
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },

  collectCoverageFrom: [
    'shared/ui/src/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/__mocks__/**',
    '!**/*.types.ts',
    '!**/*.enums.ts',
    '!**/*.constants.ts?(x)',
    '!**/*.styled.tsx',
    '!**/*.props.ts',
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
    'GlobalStyles.ts',
  ],

  transform: {
    '^.+\\.(ts|tsx)$': [
      'ts-jest',
      {
        tsconfig: '<rootDir>/shared/jest-shared/tsconfig.json',
      },
    ],
  },

  transformIgnorePatterns: [
    '/node_modules/(?!nanoid|@ant-design|antd|@rc-component|rc-.*).+\\.(js|jsx|ts|tsx)$',
  ],

  moduleDirectories: ['node_modules', '<rootDir>/shared/jest-config/__mocks__'],
  coverageDirectory: '<rootDir>/coverage/shared',
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
};

export default config;
