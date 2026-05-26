import axiosLibs from '@shared/ui/libs/axios.libs';

import {
  AttachmentStatusResponseType,
  AttachmentType,
  FileType,
} from '@shared/ui/types/attachments.types';

import { IFileStream } from '@shared/ui/interfaces/stream.interfaces';
import { uploadAttachmentsValidator } from '@shared/ui/validators/attachments.validators';

export const uploadAttachments = async (
  fileList: FileType[],
): Promise<{ attachments: AttachmentType[] }> => {
  const dataTransfer = new DataTransfer();
  fileList.forEach((item) => {
    if (item.originFileObj instanceof File) {
      dataTransfer.items.add(item.originFileObj);
    }
  });
  await uploadAttachmentsValidator.parse({
    attachments: dataTransfer.files,
  });

  const formData = new FormData();
  fileList.forEach((file) => {
    formData.append('attachments', file.originFileObj as File);
  });

  const { data } = await axiosLibs.post(`/attachments`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
};

// export const getAttachments = async ({
//   page = 1,
//   limit = 50,
//   incomingHeaders,
// }: PaginationProps & AxiosIncomingClientHeaders): Promise<
//   PaginationType<AttachmentType>
// > => {
//   const { data } = await axiosLib.get(`/attachments`, {
//     params: {
//       page,
//       limit,
//     },
//     ...(incomingHeaders && {
//       headers: {
//         ...pickKeys({
//           obj: incomingHeaders,
//           keysToPick: ['x-auth-request-email', 'cookie'],
//         }),
//       },
//     }),
//   });
//   return data;
// };

export const getAttachmentStatuses = async (
  attachment_ids: string[] = [],
): Promise<AttachmentStatusResponseType | null> => {
  const { data } = await axiosLibs.post(`/attachments/status`, {
    attachment_ids,
  });
  return data;
};

export const getAttachment = async ({
  attachment_id,
}: {
  attachment_id: string;
}): Promise<IFileStream> => {
  const { data } = await axiosLibs.get(`/attachments/${attachment_id}`, {
    responseType: 'stream',
  });
  return data;
};

export const deleteAttachment = async (
  attachment_id: string,
): Promise<Pick<AttachmentType, 'attachment_id'> & { message: string }> => {
  const { data } = await axiosLibs.delete(`/attachments/${attachment_id}`);
  return data;
};
