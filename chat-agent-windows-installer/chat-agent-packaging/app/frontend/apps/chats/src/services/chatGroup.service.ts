import axiosLibs from '@shared/ui/libs/axios.libs';
import { pickKeys } from '@shared/ui/utils/common.utils';
import {
  UpdateOrCreateChatGroupSchema,
  updateOrCreateChatGroupValidator,
} from '@/validators/chatsGroups.validators';

import { ChatGroupType } from '@shared/ui/types/chatGroup.types';
import {
  PaginationProps,
  PaginationType,
} from '@shared/ui/types/pagination.types';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';

export const getChatsGroups = async ({
  page = 1,
  limit = 50,
  search = '',
  incomingHeaders,
}: PaginationProps & AxiosIncomingClientHeaders): Promise<
  PaginationType<ChatGroupType>
> => {
  const { data } = await axiosLibs.get('/chats-groups', {
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

export const createChatGroup = async ({
  title,
}: UpdateOrCreateChatGroupSchema): Promise<ChatGroupType> => {
  await updateOrCreateChatGroupValidator.parseAsync({ title });
  const { data } = await axiosLibs.post(`/chats-groups`, {
    title,
  });
  return data;
};

export const updateChatGroup = async ({
  id,
  title,
}: { id: string } & UpdateOrCreateChatGroupSchema): Promise<ChatGroupType> => {
  await updateOrCreateChatGroupValidator.parseAsync({
    title,
  });
  const { data } = await axiosLibs.put(`/chats-groups/${id}`, {
    title,
  });
  return data;
};

export const deleteChatGroup = async (
  id: string,
): Promise<Pick<ChatGroupType, 'group_id'>> => {
  const { data } = await axiosLibs.delete(`/chats-groups/${id}`);
  return data;
};
