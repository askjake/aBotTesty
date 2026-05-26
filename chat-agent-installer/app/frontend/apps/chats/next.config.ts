import type { NextConfig } from 'next';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const APP_ENV = process.env.APP_ENV || 'local';
const BETA_REPORT_URL =
  process.env.NEXT_PUBLIC_BETA_REPORT_URL || 'http://localhost:3001';

const nextConfig: NextConfig = {
  devIndicators: false,
  env: {
    NEXT_PUBLIC_APP_VERSION: Date.now().toString(),
  },
  async rewrites() {
    return [
      // Proxy API requests to backend
      {
        source: '/rest/api/v1/:path*',
        destination: `${BACKEND_URL}/rest/api/v1/:path*`,
      },
      // Beta reports rewrites
      {
        source: '/beta-reports',
        destination: `${BETA_REPORT_URL}/beta-reports`,
      },
      {
        source: '/beta-reports/:path*',
        destination: `${BETA_REPORT_URL}/beta-reports/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        source: '/:all(svg|jpg|jpeg|png|gif|css|webp)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=2592000',
          },
        ],
      },
    ];
  },
  reactStrictMode: true,
  output: 'standalone',
  compress: APP_ENV !== 'local',
  experimental: {
    optimizePackageImports: ['antd'],
  },
  compiler: {
    styledComponents: true,
  },
  transpilePackages: [
    '@shared/ui',
    // antd & deps
    '@ant-design',
    '@ant-design/x',
    '@rc-component',
    'antd',
    'rc-cascader',
    'rc-checkbox',
    'rc-collapse',
    'rc-dialog',
    'rc-drawer',
    'rc-dropdown',
    'rc-field-form',
    'rc-image',
    'rc-input',
    'rc-input-number',
    'rc-mentions',
    'rc-menu',
    'rc-motion',
    'rc-notification',
    'rc-pagination',
    'rc-picker',
    'rc-progress',
    'rc-rate',
    'rc-resize-observer',
    'rc-segmented',
    'rc-select',
    'rc-slider',
    'rc-steps',
    'rc-switch',
    'rc-table',
    'rc-tabs',
    'rc-textarea',
    'rc-tooltip',
    'rc-tree',
    'rc-tree-select',
    'rc-upload',
    'rc-util',
  ],

  images: {
    contentDispositionType: 'attachment',
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox",
    remotePatterns: [
      APP_ENV === 'local'
        ? {
            protocol: 'http',
            hostname: 'localhost',
            port: '3000',
          }
        : {
            protocol: 'https',
            hostname: BACKEND_URL.replace('https://', ''),
          },
    ],
  },
};

export default nextConfig;
