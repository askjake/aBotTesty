import axiosLibs from '@shared/ui/libs/axios.libs';
import { UserType } from '@shared/ui/types/user.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';
import { pickKeys } from '@shared/ui/utils/common.utils';

export const getUser = async (
  incomingHeaders?: AxiosIncomingClientHeaders['incomingHeaders'],
): Promise<UserType> => {
  const { data } = await axiosLibs.get('/whoami', {
    ...(incomingHeaders && {
      headers: {
        ...pickKeys({
          obj: incomingHeaders,
          keysToPick: ['x-auth-request-email', 'cookie'],
        }),
      },
    }),
  });
  return data;
};
