import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';
import { getUser } from '@shared/ui/services/user.services';
import {
  checkVaultRegisteredService,
  checkVaultStatusService,
} from '@/services/vault.services';
import { getReleases } from '@shared/ui/services/releases.services';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';

export const fetchUserData = async (
  incomingHeaders: AxiosIncomingClientHeaders['incomingHeaders'],
) => {
  try {
    const [user, isVaultModeRegistered, isVaultModeEnabled, releases] =
      await Promise.all([
        getUser(incomingHeaders).catch((err) => {
          console.error('[fetchUserData] Error fetching user:', err.message);
          // Return a default user object if user fetch fails in no-auth mode
          const disableAuth = process.env.NEXT_PUBLIC_DISABLE_AUTH === 'true';
          if (disableAuth) {
            const email = incomingHeaders?.['X-Auth-Request-Email'] || 'test-user@dish.com';
            return {
              email: typeof email === 'string' ? email : email[0],
              first_name: 'Test',
              last_name: 'User',
              name: 'Test User',
              last_release_date: null,
            };
          }
          throw err;
        }),
        checkVaultRegisteredService(incomingHeaders).catch(() => false),
        checkVaultStatusService(incomingHeaders).catch(() => false),
        getReleases({
          incomingHeaders,
          page: 1,
          limit: DEFAULT_PAGE_SIZE,
        }).catch(() => ({ docs: [], hasNextPage: false })),
      ]);
    return {
      user,
      isVaultModeRegistered,
      isVaultModeEnabled,
      releases,
    };
  } catch (error) {
    console.error('[fetchUserData] Critical error:', error);
    throw error;
  }
};
