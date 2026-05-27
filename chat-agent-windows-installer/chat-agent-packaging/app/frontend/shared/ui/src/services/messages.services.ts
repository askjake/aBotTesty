import axiosLibs from '@shared/ui/libs/axios.libs';
import {
  ChangeMessageVersionSchema,
  changeMessageVersionValidator,
  CreateMessageVersionSchema,
  createMessageVersionValidator,
  UpdateMessageSchema,
  updateMessageValidator,
} from '@shared/ui/validators/messages.validators';

import {
  MessageVersionsInfoType,
  MessageVersionsType,
  OriginalMessageType,
  RawMessageType,
} from '@shared/ui/types/messages.types';
import {
  PaginationProps,
  PaginationType,
} from '@shared/ui/types/pagination.types';
import { CHAT_MESSAGES_PAGE_SIZE } from '@shared/ui/constants/common.constants';
import { AxiosIncomingClientHeaders } from '@shared/ui/types/axios.types';
import { pickKeys } from '@shared/ui/utils/common.utils';

export const createMessage = async ({
  chat_id,
  content = '',
  message_config,
  attachments = [],
}: { chat_id: string } & UpdateMessageSchema): Promise<
  ReadableStream<Uint8Array<ArrayBufferLike>>
> => {
  await updateMessageValidator.parseAsync({
    content,
    attachments,
    message_config,
  });

  const { data } = await axiosLibs.post(
    `/chats/${chat_id}/messages`,
    {
      content,
      attachments,
      message_config,
    },
    {
      responseType: 'stream',
      adapter: 'fetch',
    },
  );
  return data;
};

export const getMessage = async ({
  chat_id,
  message_id,
}: {
  chat_id: string;
  message_id: string;
}): Promise<RawMessageType> => {
  const { data } = await axiosLibs.get(
    `/chats/${chat_id}/messages/${message_id}`,
  );
  return data;
};

export const getMessages = async ({
  chat_id,
  page = 1,
  limit = CHAT_MESSAGES_PAGE_SIZE,
  incomingHeaders,
}: {
  chat_id: string;
} & PaginationProps &
  AxiosIncomingClientHeaders): Promise<PaginationType<OriginalMessageType>> => {
  const { data } = await axiosLibs.get(`/chats/${chat_id}/messages`, {
    params: {
      page,
      limit,
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

export const getMessageVersion = async ({
  chat_id,
  message_id,
}: {
  chat_id: string;
  message_id: string;
}): Promise<MessageVersionsType> => {
  const { data } = await axiosLibs.get(
    `/chats/${chat_id}/messages/${message_id}/version`,
  );
  return data;
};

export const createMessageVersion = async ({
  chat_id,
  message_id,
  content = '',
}: {
  chat_id: string;
  message_id: string;
} & CreateMessageVersionSchema): Promise<
  ReadableStream<Uint8Array<ArrayBufferLike>>
> => {
  await createMessageVersionValidator.parseAsync({
    content,
  });

  const { data } = await axiosLibs.post(
    `/chats/${chat_id}/messages/${message_id}/versions`,
    {
      content,
    },
    {
      responseType: 'stream',
      adapter: 'fetch',
    },
  );
  return data;
};

export const changeMessageVersion = async ({
  chat_id,
  message_id,
  version_index,
}: {
  chat_id: string;
  message_id: string;
} & ChangeMessageVersionSchema): Promise<MessageVersionsInfoType> => {
  await changeMessageVersionValidator.parseAsync({
    version_index,
  });

  const { data } = await axiosLibs.put(
    `/chats/${chat_id}/messages/${message_id}/versions`,
    {
      version_index,
    },
  );
  return data;
};
