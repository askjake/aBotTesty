import axiosLibs from '@shared/ui/libs/axios.libs';

import {
  UpdateLastReleaseDateSchema,
  updateLastReleaseDateValidator,
} from '@shared/ui/validators/releases.validators';
import { pickKeys } from '@shared/ui/utils/common.utils';
import {
  DEFAULT_DATE_FORMAT,
  DEFAULT_PAGE_SIZE,
} from '@shared/ui/constants/common.constants';
import customDayjs from '@shared/ui/libs/dayjs.libs';

import {
  PaginationProps,
  PaginationType,
} from '@shared/ui/types/pagination.types';
import { ReleasesType } from '@shared/ui/types/releases.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';

export const getReleases = async ({
  page = 1,
  limit = DEFAULT_PAGE_SIZE,
  search = '',
  incomingHeaders,
}: PaginationProps & AxiosIncomingClientHeaders): Promise<
  PaginationType<ReleasesType>
> => {
  const { data } = await axiosLibs.get('/releases', {
    params: {
      page,
      limit,
      search,
    },
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

export const updateLastReleaseDate = async ({
  date,
  incomingHeaders,
}: UpdateLastReleaseDateSchema & {
  incomingHeaders?: AxiosIncomingClientHeaders['incomingHeaders'];
}) => {
  await updateLastReleaseDateValidator.parseAsync({ date });
  const { data } = await axiosLibs.put(
    '/releases',
    { date: customDayjs(date).format(DEFAULT_DATE_FORMAT) },
    {
      ...(incomingHeaders && {
        headers: {
          ...pickKeys({
            obj: incomingHeaders,
            keysToPick: ['x-auth-request-email', 'cookie'],
          }),
        },
      }),
    },
  );
  return data;
};
