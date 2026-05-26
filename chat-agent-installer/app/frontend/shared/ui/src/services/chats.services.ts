import axiosLibs from '@shared/ui/libs/axios.libs';
import { pickKeys } from '@shared/ui/utils/common.utils';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import {
  ChatsUsageByRangeValidator,
  UpdateChatSchema,
  updateChatValidator,
} from '../validators/chats.validators';
import { DEFAULT_DATE_FORMAT } from '@shared/ui/constants/common.constants';

import {
  PaginationProps,
  PaginationType,
} from '@shared/ui/types/pagination.types';
import { ChatType, ChatUsageType } from '@shared/ui/types/chats.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';

export const getChats = async ({
  page = 1,
  limit = 50,
  search = '',
  group_id = 'all',
  namespace = 'generic',
  incomingHeaders,
}: PaginationProps &
  AxiosIncomingClientHeaders & {
    group_id?: string | null;
    namespace?: string;
  }): Promise<PaginationType<ChatType> & { active_chat_id?: string }> => {
  const { data } = await axiosLibs.get('/chats', {
    params: {
      page,
      limit,
      search,
      group_id: group_id === null ? 'none' : group_id,
      namespace,
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

export const createChat = async ({
  namespace = 'generic',
  incomingHeaders,
}: {
  namespace?: string;
  incomingHeaders?: AxiosIncomingClientHeaders['incomingHeaders'];
}): Promise<ChatType> => {
  const { data } = await axiosLibs.post(
    '/chats',
    {},
    {
      params: {
        namespace,
      },
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

export const getChat = async ({
  id,
  incomingHeaders,
}: { id: string } & AxiosIncomingClientHeaders): Promise<ChatType> => {
  const { data } = await axiosLibs.get(`/chats/${id}`, {
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

export const updateChat = async ({
  id,
  title,
  favorite = false,
  active = false,
  group_id = null,
}: { id: string } & UpdateChatSchema): Promise<ChatType> => {
  await updateChatValidator.parseAsync({ title, favorite, group_id });
  const { data } = await axiosLibs.put(`/chats/${id}`, {
    title,
    favorite,
    active,
    group_id,
  });
  return data;
};

export const deleteChat = async (
  id: string,
): Promise<Pick<ChatType, 'chat_id'>> => {
  const { data } = await axiosLibs.delete(`/chats/${id}`);
  return data;
};

export const getChatUsage = async (id: string): Promise<ChatUsageType> => {
  const { data } = await axiosLibs.get(`/chats/${id}/token_usage`);
  return data;
};

export const getChatsUsageByRange = async ({
  start_date,
  end_date,
}: ChatsUsageByRangeValidator): Promise<ChatUsageType> => {
  const { data } = await axiosLibs.get(`/token_usage`, {
    params: {
      start_date: customDayjs(start_date).format(DEFAULT_DATE_FORMAT),
      end_date: customDayjs(end_date).format(DEFAULT_DATE_FORMAT),
    },
  });
  return data;
};

export const activateChat = async (chat_id: string): Promise<{ success: boolean; chat_id: string }> => {
  const { data } = await axiosLibs.post(`/chats/${chat_id}/activate`);
  return data;
};
