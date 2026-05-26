import { FileType } from '@shared/ui/types/attachments.types';

export const calcTotalAttachments = ({
  attachments = [],
  types,
}: {
  attachments: FileType[];
  types: { [key: string]: any };
}) =>
  attachments.filter((item) => Object.keys(types).includes(item.type as string))
    .length;
