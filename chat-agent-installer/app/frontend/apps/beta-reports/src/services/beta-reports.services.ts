import axiosLibs from '@shared/ui/libs/axios.libs';
import { pickKeys } from '@shared/ui/utils/common.utils';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import {
  FeedbackIssueSchema,
  feedbackIssueValidator,
} from '@/validators/beta-reports.validator';
import { DEFAULT_DATE_FORMAT } from '@shared/ui/constants/common.constants';

import {
  BetaReportsPaginationProps,
  BetaReportType,
  IssueCandidatesPaginationProps,
  IssueCandidateType,
  ReportsReleasesPaginationProps,
  ReportsReleaseType,
} from '@/types/beta-reports.types';
import { PaginationType } from '@shared/ui/types/pagination.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';
import { SuccessResponseType } from '@shared/ui/types/common.types';

export const getBetaReports = async ({
  start_date,
  end_date,
  release,
  platform,
  device,
  page,
  limit,
  incomingHeaders,
}: BetaReportsPaginationProps & AxiosIncomingClientHeaders): Promise<
  PaginationType<BetaReportType>
> => {
  const { data } = await axiosLibs.get('/agents/betareport/reports', {
    params: {
      page,
      limit,
      ...(start_date && {
        start_date: customDayjs(start_date).format(DEFAULT_DATE_FORMAT),
      }),
      ...(end_date && {
        end_date: customDayjs(end_date).format(DEFAULT_DATE_FORMAT),
      }),
      platform,
      release,
      device,
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

export const getIssueCandidates = async ({
  start_date,
  end_date,
  release,
  platform,
  page,
  limit,
  min_priority,
  max_priority,
  incomingHeaders,
}: IssueCandidatesPaginationProps & AxiosIncomingClientHeaders): Promise<
  PaginationType<IssueCandidateType>
> => {
  const { data } = await axiosLibs.get('/agents/betareport/issues', {
    params: {
      page,
      limit,
      ...(start_date && {
        start_date: customDayjs(start_date).format(DEFAULT_DATE_FORMAT),
      }),
      ...(end_date && {
        end_date: customDayjs(end_date).format(DEFAULT_DATE_FORMAT),
      }),
      ...(min_priority !== undefined && {
        min_priority,
      }),
      ...(max_priority !== undefined && {
        max_priority,
      }),
      platform,
      release,
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

export const leaveFeedbackIssue = async ({
  accepted,
  id,
  comments,
}: FeedbackIssueSchema): Promise<SuccessResponseType> => {
  await feedbackIssueValidator.parseAsync({
    accepted,
    id,
    comments,
  });
  const { data } = await axiosLibs.post(`/agents/betareport/feedback`, {
    accept: accepted,
    issue_id: id,
    comments,
  });
  return data;
};

export const getReportsReleases = async ({
  start_date,
  end_date,
  platform,
  page,
  limit,
  incomingHeaders,
}: ReportsReleasesPaginationProps & AxiosIncomingClientHeaders): Promise<
  PaginationType<ReportsReleaseType>
> => {
  const { data } = await axiosLibs.get('/agents/betareport/releases', {
    params: {
      page,
      limit,
      ...(start_date && {
        start_date: customDayjs(start_date).format(DEFAULT_DATE_FORMAT),
      }),
      ...(end_date && {
        end_date: customDayjs(end_date).format(DEFAULT_DATE_FORMAT),
      }),
      platform,
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

export const getAvailablePlatforms = async ({
  incomingHeaders,
}: AxiosIncomingClientHeaders = {}): Promise<string[]> => {
  const { data } = await axiosLibs.get(
    '/agents/betareport/available-platforms',
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

export const getAvailableDevices = async ({
  incomingHeaders,
}: AxiosIncomingClientHeaders = {}): Promise<string[]> => {
  const { data } = await axiosLibs.get('/agents/betareport/available-devices', {
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
