'use client';

import { FC, useEffect } from 'react';
import { useRouter as useNextRouter } from 'next/navigation';
import { useRouter as usePagesRouter } from 'next/router';
import axios from 'axios';
import { Modal } from 'antd';
import { ExclamationCircleFilled } from '@ant-design/icons';
const { confirm } = Modal;

import { DeployNotifierProps } from '@shared/ui/components/molecules/Notifiers/DeployNotifier/DeployNotifier.props';

// Detect if we're in App Router or Pages Router context
const useRouterCompat = () => {
  try {
    // Try to use Pages Router first (has events API)
    const router = usePagesRouter();
    if (router && router.events) {
      return { router, isAppRouter: false };
    }
  } catch (e) {
    // Pages Router not available
  }
  
  try {
    // Fall back to App Router
    const router = useNextRouter();
    return { router, isAppRouter: true };
  } catch (e) {
    // Neither available
  }
  
  return { router: null, isAppRouter: false };
};

const DeployNotifier: FC<DeployNotifierProps> = ({ prefix = 'app' }) => {
  const { router, isAppRouter } = useRouterCompat();

  useEffect(() => {
    const checkForUpdates = async () => {
      try {
        const {
          data: { version },
        } = await axios.get('/api/version');
        const currentVersion = localStorage.getItem(`${prefix}_version`) || 0;

        if (+currentVersion !== +version) {
          confirm({
            title: 'The new version of the app is available',
            icon: <ExclamationCircleFilled />,
            content:
              'An update is available. Please click "OK" to reload this page or refresh the page manually.',
            okText: 'Ok',
            okType: 'danger',
            cancelText: 'Cancel',
            onOk() {
              window.location.reload();
            },
          });
        }
        localStorage.setItem(`${prefix}_version`, version);
      } catch (error) {
        console.error('Failed to check for updates:', error);
      }
    };

    // Set up route change listener for Pages Router
    if (!isAppRouter && router && router.events) {
      router.events.on('routeChangeComplete', checkForUpdates);
    }

    // Set up interval for both routers
    const interval = setInterval(checkForUpdates, 60 * 1000);

    return () => {
      if (!isAppRouter && router && router.events) {
        router.events.off('routeChangeComplete', checkForUpdates);
      }
      clearInterval(interval);
    };
  }, [router, isAppRouter, prefix]);
  
  return null;
};

export default DeployNotifier;
